from pydantic import BaseModel


# ─── 참가자 초대 ───

class InviteeItem(BaseModel):
    type: str  # "internal" | "external"
    user_id: str | None = None
    username: str | None = None
    display_name: str | None = None
    email: str | None = None  # external일 때


# ─── 인증 사용자 (로비) ───

class RoomCreate(BaseModel):
    name: str
    max_participants: int = 10
    invitees: list[InviteeItem] = []
    scheduled_at: str | None = None  # ISO 8601 (없으면 즉시)
    duration_minutes: int = 60


class RoomInfo(BaseModel):
    name: str
    num_participants: int
    max_participants: int
    creation_time: int
    share_token: str = ""
    is_host: bool = False
    pending_count: int = 0


class RoomListResponse(BaseModel):
    rooms: list[RoomInfo]


class TokenRequest(BaseModel):
    room: str


class TokenResponse(BaseModel):
    token: str
    livekit_url: str


class ParticipantInfo(BaseModel):
    identity: str
    name: str
    joined_at: int


# ─── 공유링크 (외부인) ───

class JoinRoomInfo(BaseModel):
    name: str
    host_name: str
    num_participants: int
    max_participants: int


class JoinRequestCreate(BaseModel):
    nickname: str


class JoinRequestResponse(BaseModel):
    request_id: str


class JoinRequestStatus(BaseModel):
    status: str  # pending | approved | denied
    token: str | None = None
    livekit_url: str | None = None


# ─── 호스트 — 참가 신청 관리 ───

class PendingRequest(BaseModel):
    id: str
    nickname: str
    created_at: float
