from typing import Optional

from pydantic import BaseModel


class TokenRegisterRequest(BaseModel):
    """Запрос от стороннего сервиса на регистрацию токена"""

    token: str
    service_name: Optional[str] = None
    expires_in_minutes: int = 0  # 0 = бессрочный токен


class TokenRegisterResponse(BaseModel):
    """Ответ на регистрацию токена"""

    status: str
    token: str
    expires_at: Optional[str] = None
    message: str


class TokenStatusResponse(BaseModel):
    """Ответ на проверку статуса токена (для polling)"""

    status: str  # pending, approved, rejected, expired
    tg_userid: Optional[int] = None
    message: str


class TokenApproveRequest(BaseModel):
    """Запрос на подтверждение токена от Telegram бота"""

    token: str
    tg_userid: int


class TokenApproveResponse(BaseModel):
    """Ответ на подтверждение токена"""

    status: str
    message: str


class MireaTokenRequest(BaseModel):
    """Запрос на получение токена MIREA"""

    pass  # Авторизация через заголовок Authorization или initData


class MireaTokenResponse(BaseModel):
    """Ответ с токеном/cookies MIREA"""

    status: str
    cookies: list
    message: str


class CredentialsResponse(BaseModel):
    """Ответ с зашифрованными credentials MIREA для внешнего сервиса"""

    status: str
    encrypted_data: Optional[str] = None  # Fernet-encrypted JSON {"l": login, "p": password}
    group_name: Optional[str] = None
    message: str
