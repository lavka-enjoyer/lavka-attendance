from typing import Tuple

from fastapi import Body, HTTPException, status

from backend.auth import verify_init_data
from backend.config import BOT_TOKEN

from .schemas import InitDataRequest


def init_data_post(request: InitDataRequest = Body(...)) -> Tuple[int, int]:
    """
    Проверяет и извлекает данные пользователя из initData.

    Args:
        request: Запрос с initData и количеством месяцев подписки

    Returns:
        Кортеж из ID пользователя и количества месяцев подписки

    Raises:
        HTTPException: При невалидном initData
    """
    try:
        tg_user_id = verify_init_data(request.initData, BOT_TOKEN)
        return tg_user_id, request.sub_month
    except ValueError as err:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=str(err))
