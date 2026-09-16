"""Pydantic request/response schemas."""

from datetime import date, datetime
from typing import Any, Self

from pydantic import BaseModel, ConfigDict, EmailStr, Field, model_validator

from einsatzbereit.models import CertificationKind, UserRole, ValidityMode
from einsatzbereit.services.status import CellStatus


class ORMModel(BaseModel):
    model_config = ConfigDict(from_attributes=True)


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class MfaLoginRequest(BaseModel):
    mfa_token: str
    code: str = Field(min_length=6, max_length=8)


class TokenResponse(BaseModel):
    access_token: str | None = None
    token_type: str = "bearer"  # noqa: S105
    mfa_required: bool = False
    mfa_token: str | None = None


class PasswordResetRequest(BaseModel):
    email: EmailStr


class PasswordResetConfirm(BaseModel):
    token: str
    new_password: str = Field(min_length=10, max_length=256)


class PasswordChange(BaseModel):
    current_password: str
    new_password: str = Field(min_length=10, max_length=256)


class TotpSetupResponse(BaseModel):
    secret: str
    otpauth_uri: str


class TotpCode(BaseModel):
    code: str = Field(min_length=6, max_length=8)


class TotpDisable(BaseModel):
    password: str
    code: str = Field(min_length=6, max_length=8)


class UserOut(ORMModel):
    id: int
    email: str
    display_name: str
    role: UserRole
    is_active: bool
    totp_enabled: bool


class UserCreate(BaseModel):
    email: EmailStr
    display_name: str = Field(min_length=1, max_length=120)
    role: UserRole = UserRole.USER
    password: str = Field(min_length=10, max_length=256)


class UserUpdate(BaseModel):
    display_name: str | None = Field(default=None, min_length=1, max_length=120)
    role: UserRole | None = None
    is_active: bool | None = None


class CertificationRef(ORMModel):
    id: int
    name: str


class CertificationBase(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    short_name: str = Field(default="", max_length=12)
    kind: CertificationKind
    description: str = ""
    validity_mode: ValidityMode
    validity_months: int | None = Field(default=None, ge=1, le=240)
    warn_days: int = Field(default=60, ge=0, le=730)
    sort_order: int = 0
    is_active: bool = True

    @model_validator(mode="after")
    def _check_months(self) -> Self:
        needs_months = self.validity_mode in (ValidityMode.FIXED_DURATION, ValidityMode.END_OF_YEAR)
        if needs_months and self.validity_months is None:
            raise ValueError("validity_months is required for this validity_mode")
        if not needs_months:
            self.validity_months = None
        return self


class CertificationIn(CertificationBase):
    pass


class CertificationOut(CertificationBase, ORMModel):
    id: int


class PositionIn(BaseModel):
    name: str = Field(min_length=1, max_length=80)
    description: str = ""
    certification_ids: list[int] = []


class PositionOut(ORMModel):
    id: int
    name: str
    description: str
    certifications: list[CertificationRef]


class PositionRef(ORMModel):
    id: int
    name: str


class MemberIn(BaseModel):
    number: str = Field(min_length=1, max_length=32)
    last_name: str = Field(min_length=1, max_length=80)
    first_name: str = Field(min_length=1, max_length=80)
    is_active: bool = True
    position_ids: list[int] = []


class MemberOut(ORMModel):
    id: int
    number: str
    last_name: str
    first_name: str
    is_active: bool
    positions: list[PositionRef]


class CompletionIn(BaseModel):
    member_id: int
    certification_id: int
    completed_on: date
    manual_expires_on: date | None = None
    note: str = Field(default="", max_length=2000)

    @model_validator(mode="after")
    def _check_dates(self) -> Self:
        if self.manual_expires_on is not None and self.manual_expires_on < self.completed_on:
            raise ValueError("manual_expires_on must not be before completed_on")
        return self


class BulkCompletionIn(BaseModel):
    """Same completion for many members at once, e.g. after a joint exercise."""

    certification_id: int
    member_ids: list[int] = Field(min_length=1, max_length=500)
    completed_on: date
    manual_expires_on: date | None = None
    note: str = Field(default="", max_length=2000)

    @model_validator(mode="after")
    def _check(self) -> Self:
        if self.manual_expires_on is not None and self.manual_expires_on < self.completed_on:
            raise ValueError("manual_expires_on must not be before completed_on")
        self.member_ids = list(dict.fromkeys(self.member_ids))
        return self


class BulkCompletionOut(BaseModel):
    created: int


class CompletionOut(BaseModel):
    id: int
    member_id: int
    certification_id: int
    certification_name: str
    completed_on: date
    expires_on: date | None
    note: str
    recorded_by: str | None
    recorded_by_id: int | None
    recorded_at: datetime


class CellOut(BaseModel):
    certification_id: int
    required: bool
    status: CellStatus
    completed_on: date | None
    expires_on: date | None


class MatrixRowOut(BaseModel):
    member: MemberOut
    worst_status: CellStatus
    open_count: int
    cells: list[CellOut]


class OverviewOut(BaseModel):
    today: date
    certifications: list[CertificationOut]
    rows: list[MatrixRowOut]
    counts: dict[CellStatus, int]


class MemberDetailOut(BaseModel):
    member: MemberOut
    cells: list[CellOut]
    history: list[CompletionOut]


class AuditEntryOut(ORMModel):
    id: int
    at: datetime
    user_name: str
    entity_type: str
    entity_id: int
    entity_label: str
    member_id: int | None
    action: str
    changes: dict[str, Any]


class AuditPage(BaseModel):
    entries: list[AuditEntryOut]
    next_before_id: int | None
    """Pass as ``before_id`` to load the next (older) page."""
