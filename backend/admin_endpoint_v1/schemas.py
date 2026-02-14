from typing import Optional

from pydantic import BaseModel


class InitDataRequest(BaseModel):
    initData: str
    sub_month: int = 0


class UpdateUser(BaseModel):
    initData: str
    login: Optional[str] = None
    password: Optional[str] = None
    allowConfirm: Optional[bool] = None
    user_agent: Optional[str] = None


class CreateUserNew(BaseModel):
    initData: str
    url: str
    login: Optional[str] = None
    password: Optional[str] = None
    user_agent: Optional[str] = None


class UpdateSub(BaseModel):
    initData: str
    tg_user_id: int
    subscribe_id: int
    month: int


class GetAllUsers(BaseModel):
    initData: str
    offset: int
    group_name: Optional[str] = None


class DeleteUserByAdmin(BaseModel):
    initData: str
    target_tg_userid: int


class SetAdminLevel(BaseModel):
    initData: str
    target_tg_userid: int
    admin_level: int


class SearchUsers(BaseModel):
    initData: str
    query: str
    offset: int = 0


class SubmitOtpCode(BaseModel):
    """Схема для отправки OTP кода."""

    initData: str
    otp_code: str


class CheckTotpSession(BaseModel):
    """Схема для проверки наличия 2FA сессии."""

    initData: str


class SelectOtpCredential(BaseModel):
    """Схема для выбора OTP credential."""

    initData: str
    credential_id: str


# Bulk operations schemas


class BulkDeleteRequest(BaseModel):
    """Схема для массового удаления пользователей."""

    initData: str
    target_tg_userids: list[int]


class BulkEditRequest(BaseModel):
    """Схема для массового редактирования пользователей."""

    initData: str
    target_tg_userids: list[int]
    allowConfirm: Optional[bool] = None
    admin_lvl: Optional[int] = None
    group_name: Optional[str] = None


class BulkImportUser(BaseModel):
    """Схема для одного пользователя при массовом импорте."""

    tg_userid: int
    login: Optional[str] = None
    password: Optional[str] = None
    group_name: Optional[str] = None
    fio: Optional[str] = None
    allowConfirm: bool = True
    admin_lvl: int = 0


class BulkImportRequest(BaseModel):
    """Схема для массового импорта пользователей."""

    initData: str
    users: list[BulkImportUser]


# Audit logs schemas


class AuditLogsRequest(BaseModel):
    """Схема для запроса аудит-логов."""

    initData: str
    admin_tg_userid: Optional[int] = None
    action_type: Optional[str] = None
    target_type: Optional[str] = None
    date_from: Optional[str] = None  # ISO format
    date_to: Optional[str] = None  # ISO format
    offset: int = 0
    limit: int = 50


class UserActionLogsRequest(BaseModel):
    """Схема для запроса логов действий пользователей."""

    initData: str
    actor_tg_userid: Optional[int] = None
    target_tg_userid: Optional[int] = None
    action_type: Optional[str] = None
    status: Optional[str] = None
    date_from: Optional[str] = None  # ISO format
    date_to: Optional[str] = None  # ISO format
    offset: int = 0
    limit: int = 50
