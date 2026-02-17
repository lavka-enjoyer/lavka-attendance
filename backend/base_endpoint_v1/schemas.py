from dataclasses import dataclass
from typing import Any, Optional

from pydantic import BaseModel, EmailStr


@dataclass
class CheckUserSuccess:
    """Успешный результат проверки пользователя."""

    user_info: dict
    fio: str
    is_valid: bool
    extra: Any = None


@dataclass
class CheckUserError:
    """Ошибка при проверке пользователя."""

    status_code: int
    message: str


@dataclass
class CheckUserNeedsLogin:
    """Пользователю нужно ввести логин/пароль."""

    message: str = "Введите Логин и Пароль"


@dataclass
class CheckUserNeedsEmailCode:
    """Пользователю нужно ввести код из email."""

    message: str = "Требуется ввод кода из email"


# Type alias для результата _check_user
CheckUserResult = (
    CheckUserSuccess | CheckUserError | CheckUserNeedsLogin | CheckUserNeedsEmailCode
)


@dataclass
class OperationSuccess:
    """Успешная операция."""

    success: bool = True


@dataclass
class OperationError:
    """Ошибка операции."""

    error: str


# Type alias для результата операций
OperationResult = OperationSuccess | OperationError


class ErrorResponse(BaseModel):
    """Стандартная схема ответа об ошибке."""

    detail: str
    error_code: Optional[str] = None

    class Config:
        json_schema_extra = {
            "example": {"detail": "Описание ошибки", "error_code": "AUTH_ERROR"}
        }


class SuccessResponse(BaseModel):
    """Стандартная схема успешного ответа."""

    status: str = "success"
    message: Optional[str] = None

    class Config:
        json_schema_extra = {
            "example": {"status": "success", "message": "Операция выполнена успешно"}
        }


class EditAllowConfirm(BaseModel):
    """Схема для изменения разрешения на автоматическую отметку."""

    initData: str
    allowConfirm: bool


class CreateUserPart1(BaseModel):
    """Схема для первой части регистрации пользователя."""

    initData: str
    login: EmailStr
    password: str


class CreateUserPart2(BaseModel):
    """Схема для второй части регистрации пользователя."""

    initData: str
    group: str


class GetFlowUsersRequest(BaseModel):
    """Схема запроса списка пользователей группы."""

    initData: str
    groupName: str


class WebSocketResponse(BaseModel):
    """Схема ответа для WebSocket соединения."""

    status: str
    message: Optional[str] = None


class DeleteUser(BaseModel):
    """Схема для удаления пользователя."""

    initData: str
