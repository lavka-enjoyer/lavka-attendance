from datetime import datetime
from typing import Optional

from pydantic import BaseModel


class NfcCardAddRequest(BaseModel):
    """Запрос на добавление NFC карты"""

    card_id: int
    tg_userid: Optional[int] = None  # Если карта привязана к пользователю бота
    name: Optional[str] = (
        None  # Имя владельца (опционально, если есть tg_userid - берётся из БД)
    )


class NfcCardResponse(BaseModel):
    """Ответ с информацией о NFC карте"""

    id: int
    card_id: int
    tg_userid: Optional[int] = None
    name: str
    owner_group: str
    added_by: int
    created_at: datetime
    is_in_university: Optional[bool] = (
        None  # Статус присутствия в вузе (если есть tg_userid)
    )
    last_event_time: Optional[str] = None


class NfcCardsListResponse(BaseModel):
    """Ответ со списком NFC карт"""

    status: str
    cards: list[NfcCardResponse]


class NfcCardAddResponse(BaseModel):
    """Ответ на добавление NFC карты"""

    status: str
    message: str
    card: Optional[NfcCardResponse] = None


class NfcCardDeleteResponse(BaseModel):
    """Ответ на удаление NFC карты"""

    status: str
    message: str


class GroupUserForNfc(BaseModel):
    """Пользователь группы для выбора при добавлении NFC карты"""

    tg_userid: int
    name: str  # fio или login
    needs_totp: bool = False  # Требуется ли 2FA для этого пользователя


class GroupUsersListResponse(BaseModel):
    """Список пользователей группы для выбора"""

    status: str
    users: list[GroupUserForNfc]


class MireaCookiesResponse(BaseModel):
    """Ответ с cookies MIREA для пользователя"""

    status: str
    tg_userid: int
    name: str
    cookies: dict
    message: str
