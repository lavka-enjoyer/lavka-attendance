from typing import Optional

from pydantic import BaseModel


class TokenRegisterRequest(BaseModel):
    """Запрос от стороннего сервиса на регистрацию токена"""

    token: str
    service_name: Optional[str] = None
    expires_in_minutes: int = 10  # время жизни токена в минутах


class TokenRegisterResponse(BaseModel):
    """Ответ на регистрацию токена"""

    status: str
    token: str
    expires_at: str
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


class SubmitTotpRequest(BaseModel):
    """Запрос на отправку TOTP кода"""

    totp_code: str


class SubmitTotpResponse(BaseModel):
    """Ответ на отправку TOTP кода"""

    status: str  # success, invalid_code, error
    message: str
    cookies: Optional[list] = None


class CredentialsResponse(BaseModel):
    """Ответ с логином и паролем MIREA для внешнего сервиса"""

    status: str
    login: Optional[str] = None
    password: Optional[str] = None  # расшифрованный пароль
    group_name: Optional[str] = None
    message: str
