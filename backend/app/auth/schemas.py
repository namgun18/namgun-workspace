import re
from datetime import datetime

from pydantic import BaseModel, field_validator


class UserResponse(BaseModel):
    id: str
    username: str
    display_name: str | None
    email: str | None
    avatar_url: str | None
    recovery_email: str | None
    is_admin: bool
    has_2fa: bool = False
    last_login_at: datetime | None

    model_config = {"from_attributes": True}

    @classmethod
    def from_user(cls, user) -> "UserResponse":
        return cls(
            id=user.id,
            username=user.username,
            display_name=user.display_name,
            email=user.email,
            avatar_url=user.avatar_url,
            recovery_email=user.recovery_email,
            is_admin=user.is_admin,
            has_2fa=bool(user.totp_secret),
            last_login_at=user.last_login_at,
        )


class LoginRequest(BaseModel):
    username: str
    password: str
    remember_me: bool = False


class RegisterRequest(BaseModel):
    username: str
    password: str
    display_name: str
    recovery_email: str

    @field_validator("username")
    @classmethod
    def validate_username(cls, v: str) -> str:
        v = v.strip().lower()
        if not re.match(r"^[a-z0-9][a-z0-9.\-]{1,28}[a-z0-9]$", v):
            raise ValueError(
                "사용자명은 영문 소문자, 숫자, 점(.), 하이픈(-)만 사용 가능하며 3~30자여야 합니다"
            )
        if ".." in v or "--" in v:
            raise ValueError("연속된 점이나 하이픈은 사용할 수 없습니다")
        return v

    @field_validator("password")
    @classmethod
    def validate_password(cls, v: str) -> str:
        if len(v) < 8:
            raise ValueError("비밀번호는 최소 8자 이상이어야 합니다")
        if not re.search(r"[A-Z]", v):
            raise ValueError("비밀번호에 대문자를 1개 이상 포함해야 합니다")
        if not re.search(r"[a-z]", v):
            raise ValueError("비밀번호에 소문자를 1개 이상 포함해야 합니다")
        if not re.search(r"[0-9]", v):
            raise ValueError("비밀번호에 숫자를 1개 이상 포함해야 합니다")
        if not re.search(r"[^A-Za-z0-9]", v):
            raise ValueError("비밀번호에 특수문자를 1개 이상 포함해야 합니다")
        return v

    @field_validator("recovery_email")
    @classmethod
    def validate_recovery_email(cls, v: str) -> str:
        v = v.strip().lower()
        # Domain-specific recovery email validation is handled by frontend
        if "@" not in v or "." not in v.split("@")[-1]:
            raise ValueError("올바른 이메일 주소를 입력해주세요")
        return v

    @field_validator("display_name")
    @classmethod
    def validate_display_name(cls, v: str) -> str:
        v = v.strip()
        if not v or len(v) > 100:
            raise ValueError("표시 이름은 1~100자여야 합니다")
        return v


class ProfileUpdateRequest(BaseModel):
    display_name: str | None = None
    recovery_email: str | None = None

    @field_validator("recovery_email")
    @classmethod
    def validate_recovery_email(cls, v: str | None) -> str | None:
        if v is None:
            return v
        v = v.strip().lower()
        # Domain-specific recovery email validation is handled by frontend
        if "@" not in v or "." not in v.split("@")[-1]:
            raise ValueError("올바른 이메일 주소를 입력해주세요")
        return v


class ChangePasswordRequest(BaseModel):
    current_password: str
    new_password: str

    @field_validator("new_password")
    @classmethod
    def validate_new_password(cls, v: str) -> str:
        if len(v) < 8:
            raise ValueError("비밀번호는 최소 8자 이상이어야 합니다")
        if not re.search(r"[A-Z]", v):
            raise ValueError("비밀번호에 대문자를 1개 이상 포함해야 합니다")
        if not re.search(r"[a-z]", v):
            raise ValueError("비밀번호에 소문자를 1개 이상 포함해야 합니다")
        if not re.search(r"[0-9]", v):
            raise ValueError("비밀번호에 숫자를 1개 이상 포함해야 합니다")
        if not re.search(r"[^A-Za-z0-9]", v):
            raise ValueError("비밀번호에 특수문자를 1개 이상 포함해야 합니다")
        return v


class ForgotPasswordRequest(BaseModel):
    username: str


class ResetPasswordRequest(BaseModel):
    token: str
    new_password: str

    @field_validator("new_password")
    @classmethod
    def validate_new_password(cls, v: str) -> str:
        if len(v) < 8:
            raise ValueError("비밀번호는 최소 8자 이상이어야 합니다")
        if not re.search(r"[A-Z]", v):
            raise ValueError("비밀번호에 대문자를 1개 이상 포함해야 합니다")
        if not re.search(r"[a-z]", v):
            raise ValueError("비밀번호에 소문자를 1개 이상 포함해야 합니다")
        if not re.search(r"[0-9]", v):
            raise ValueError("비밀번호에 숫자를 1개 이상 포함해야 합니다")
        if not re.search(r"[^A-Za-z0-9]", v):
            raise ValueError("비밀번호에 특수문자를 1개 이상 포함해야 합니다")
        return v


# ── 2FA (TOTP) schemas ──────────────────────────────────────


class TwoFactorEnableRequest(BaseModel):
    secret: str
    code: str


class TwoFactorDisableRequest(BaseModel):
    code: str


class TwoFactorVerifyRequest(BaseModel):
    temp_token: str
    code: str
