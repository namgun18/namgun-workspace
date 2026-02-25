from pydantic import BaseModel


# ─── 인증 사용자 (로비) ───

class RoomCreate(BaseModel):
    name: str
    max_participants: int = 10


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
