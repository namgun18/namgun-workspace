"""Meetings (LiveKit) API router — 호스트 승인 + 공유링크 참여."""

import logging
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, status

from app.auth.deps import get_current_user
from app.config import get_settings
from app.db.models import User
from app.meetings import livekit, store
from app.meetings.invite import (
    create_calendar_event,
    generate_ics,
    send_invite_email,
)
from app.meetings.schemas import (
    JoinRequestCreate,
    JoinRequestResponse,
    JoinRequestStatus,
    JoinRoomInfo,
    ParticipantInfo,
    PendingRequest,
    RoomCreate,
    RoomInfo,
    RoomListResponse,
    TokenRequest,
    TokenResponse,
)

logger = logging.getLogger(__name__)
settings = get_settings()

router = APIRouter(prefix="/api/meetings", tags=["meetings"])


def _check_configured():
    if not livekit.is_configured():
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="LiveKit is not configured",
        )


# ════════════════════════════════════════════
# 인증 사용자 엔드포인트
# ════════════════════════════════════════════

@router.get("/rooms", response_model=RoomListResponse)
async def get_rooms(user: User = Depends(get_current_user)):
    """회의실 목록 (인증 사용자)."""
    _check_configured()
    lk_rooms = await livekit.list_rooms()
    result = []
    for r in lk_rooms:
        meta = store.get_room_meta(r["name"])
        result.append(RoomInfo(
            **r,
            share_token=meta.share_token if meta else "",
            is_host=meta.host_user_id == str(user.id) if meta else False,
            pending_count=len(store.get_pending_requests(r["name"])) if meta else 0,
        ))
    return RoomListResponse(rooms=result)


@router.post("/rooms", response_model=RoomInfo, status_code=201)
async def create_room(body: RoomCreate, user: User = Depends(get_current_user)):
    """회의실 생성 → 호스트가 됨 + 참가자 초대."""
    _check_configured()
    room = await livekit.create_room(
        name=body.name,
        max_participants=body.max_participants,
    )
    meta = store.create_room_meta(
        name=room["name"],
        host_user_id=str(user.id),
        host_username=user.username,
        host_display_name=user.display_name or user.username,
    )

    # ── 참가자 초대 (best-effort) ──
    if body.invitees:
        join_url = f"{settings.app_url}/meetings/join/{meta.share_token}"
        host_name = user.display_name or user.username
        host_email = user.email or f"{user.username}@{settings.domain}"

        if body.scheduled_at:
            try:
                scheduled = datetime.fromisoformat(body.scheduled_at)
                if scheduled.tzinfo is None:
                    scheduled = scheduled.replace(tzinfo=timezone.utc)
            except ValueError:
                scheduled = datetime.now(timezone.utc)
        else:
            scheduled = datetime.now(timezone.utc)

        duration = body.duration_minutes

        ics = generate_ics(
            summary=body.name,
            description=f"회의 참여: {join_url}",
            location=join_url,
            start=scheduled,
            end=scheduled + timedelta(minutes=duration),
            organizer_name=host_name,
            organizer_email=host_email,
        )

        for inv in body.invitees:
            # Determine recipient email
            if inv.type == "internal":
                to_email = f"{inv.username}@{settings.domain}" if inv.username else inv.email
            else:
                to_email = inv.email

            if not to_email:
                continue

            # a. Send invite email (ICS attached)
            try:
                await send_invite_email(
                    to_email=to_email,
                    meeting_name=body.name,
                    host_name=host_name,
                    join_url=join_url,
                    scheduled_at=scheduled,
                    duration_minutes=duration,
                    ics_content=ics,
                )
            except Exception:
                logger.warning("Failed to send invite email to %s", to_email, exc_info=True)

            # b. Internal user → create calendar event
            if inv.type == "internal" and inv.username:
                try:
                    await create_calendar_event(
                        username=inv.username,
                        meeting_name=body.name,
                        join_url=join_url,
                        scheduled_at=scheduled,
                        duration_minutes=duration,
                    )
                except Exception:
                    logger.warning("Failed to create calendar event for %s", inv.username, exc_info=True)

    return RoomInfo(
        **room,
        share_token=meta.share_token,
        is_host=True,
        pending_count=0,
    )


@router.delete("/rooms/{name}", status_code=204)
async def delete_room(name: str, user: User = Depends(get_current_user)):
    """회의실 삭제."""
    _check_configured()
    await livekit.delete_room(name)
    store.delete_room_meta(name)


@router.post("/token", response_model=TokenResponse)
async def create_token(body: TokenRequest, user: User = Depends(get_current_user)):
    """인증 사용자용 토큰 발급 (직접 참여)."""
    _check_configured()
    token = livekit.generate_token(
        room=body.room,
        identity=user.username,
        name=user.display_name or user.username,
    )
    return TokenResponse(token=token, livekit_url=livekit.get_ws_url())


@router.get("/rooms/{name}/participants", response_model=list[ParticipantInfo])
async def get_participants(name: str, user: User = Depends(get_current_user)):
    """참여자 목록."""
    _check_configured()
    participants = await livekit.list_participants(name)
    return [ParticipantInfo(**p) for p in participants]


# ════════════════════════════════════════════
# 호스트 — 참가 신청 관리
# ════════════════════════════════════════════

@router.get("/rooms/{name}/requests", response_model=list[PendingRequest])
async def get_pending_requests(name: str, user: User = Depends(get_current_user)):
    """대기 중인 참가 신청 목록 (호스트 전용)."""
    meta = store.get_room_meta(name)
    if not meta or meta.host_user_id != str(user.id):
        raise HTTPException(status_code=403, detail="호스트만 확인할 수 있습니다")
    pending = store.get_pending_requests(name)
    return [PendingRequest(id=r.id, nickname=r.nickname, created_at=r.created_at) for r in pending]


@router.post("/rooms/{name}/requests/{req_id}/approve", status_code=200)
async def approve_request(name: str, req_id: str, user: User = Depends(get_current_user)):
    """참가 신청 승인 → LiveKit 토큰 생성."""
    meta = store.get_room_meta(name)
    if not meta or meta.host_user_id != str(user.id):
        raise HTTPException(status_code=403, detail="호스트만 승인할 수 있습니다")
    req = store.get_join_request(name, req_id)
    if not req:
        raise HTTPException(status_code=404, detail="신청을 찾을 수 없습니다")
    if req.status != "pending":
        raise HTTPException(status_code=400, detail="이미 처리된 신청입니다")

    token = livekit.generate_token(
        room=name,
        identity=f"guest-{req.id}",
        name=req.nickname,
    )
    req.status = "approved"
    req.livekit_token = token
    return {"status": "approved"}


@router.post("/rooms/{name}/requests/{req_id}/deny", status_code=200)
async def deny_request(name: str, req_id: str, user: User = Depends(get_current_user)):
    """참가 신청 거절."""
    meta = store.get_room_meta(name)
    if not meta or meta.host_user_id != str(user.id):
        raise HTTPException(status_code=403, detail="호스트만 거절할 수 있습니다")
    req = store.get_join_request(name, req_id)
    if not req:
        raise HTTPException(status_code=404, detail="신청을 찾을 수 없습니다")
    if req.status != "pending":
        raise HTTPException(status_code=400, detail="이미 처리된 신청입니다")
    req.status = "denied"
    return {"status": "denied"}


# ════════════════════════════════════════════
# 공유링크 (인증 불요)
# ════════════════════════════════════════════

@router.get("/join/{token}", response_model=JoinRoomInfo)
async def get_join_info(token: str):
    """공유링크 → 회의실 정보 조회 (인증 불요)."""
    _check_configured()
    meta = store.get_room_by_token(token)
    if not meta:
        raise HTTPException(status_code=404, detail="유효하지 않은 초대 링크입니다")

    # LiveKit에서 실시간 참여자 수 조회
    try:
        lk_rooms = await livekit.list_rooms()
        lk_info = next((r for r in lk_rooms if r["name"] == meta.name), None)
    except Exception:
        lk_info = None

    return JoinRoomInfo(
        name=meta.name,
        host_name=meta.host_display_name,
        num_participants=lk_info["num_participants"] if lk_info else 0,
        max_participants=lk_info["max_participants"] if lk_info else 10,
    )


@router.post("/join/{token}/request", response_model=JoinRequestResponse)
async def submit_join_request(token: str, body: JoinRequestCreate):
    """공유링크 → 참가 신청 (인증 불요)."""
    _check_configured()
    meta = store.get_room_by_token(token)
    if not meta:
        raise HTTPException(status_code=404, detail="유효하지 않은 초대 링크입니다")

    nickname = body.nickname.strip()
    if not nickname or len(nickname) > 30:
        raise HTTPException(status_code=400, detail="닉네임은 1~30자여야 합니다")

    req = store.create_join_request(meta.name, nickname)
    if not req:
        raise HTTPException(status_code=404, detail="회의실을 찾을 수 없습니다")

    return JoinRequestResponse(request_id=req.id)


@router.get("/join/{token}/request/{req_id}/status", response_model=JoinRequestStatus)
async def get_request_status(token: str, req_id: str):
    """참가 신청 상태 폴링 (인증 불요)."""
    meta = store.get_room_by_token(token)
    if not meta:
        raise HTTPException(status_code=404, detail="유효하지 않은 초대 링크입니다")

    req = store.get_join_request(meta.name, req_id)
    if not req:
        raise HTTPException(status_code=404, detail="신청을 찾을 수 없습니다")

    if req.status == "approved" and req.livekit_token:
        return JoinRequestStatus(
            status="approved",
            token=req.livekit_token,
            livekit_url=livekit.get_ws_url(),
        )

    return JoinRequestStatus(status=req.status)
