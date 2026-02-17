import base64
import logging
from typing import Optional

import aiohttp
from fastapi import HTTPException

from backend.database import DBModel
from backend.mirea_api.get_cookies import generate_random_mobile_user_agent

logger = logging.getLogger(__name__)


async def get_user_schedule(
    cookies: list,
    db: DBModel,
    b64_data: str,
    user_agent: Optional[str] = None,
    tg_user_id: Optional[int] = None,
) -> list:
    """
    Получает расписание пользователя через API посещаемости.

    Args:
        cookies: Список куки для авторизации
        db: Объект базы данных
        b64_data: Base64-кодированные данные запроса (gRPC-Web фрейм)
        user_agent: User-Agent для запроса
        tg_user_id: ID пользователя в Telegram

    Returns:
        Список [base64_данные_ответа]

    Raises:
        HTTPException: При ошибке запроса
    """
    cookies_dict = {cookie["name"]: cookie["value"] for cookie in cookies}
    url = "https://attendance.mirea.ru/rtu_tc.attendance.api.LessonService/GetAvailableLessonsOfVisitingLogs"
    headers = {
        "Accept": "*/*",
        "Accept-Encoding": "gzip, deflate, br, zstd",
        "Accept-Language": "ru-RU,ru;q=0.8,en-US;q=0.5,en;q=0.3",
        "Content-Type": "application/grpc-web+proto",
        "pulse-app-type": "pulse-app",
        "pulse-app-version": "1.6.0+5256",
        "Origin": "https://attendance-app.mirea.ru",
        "Referer": "https://attendance-app.mirea.ru/",
        "Sec-Fetch-Dest": "empty",
        "Sec-Fetch-Mode": "cors",
        "Sec-Fetch-Site": "same-site",
        "User-Agent": (
            user_agent
            if user_agent is not None
            else generate_random_mobile_user_agent()
        ),
        "x-grpc-web": "1",
        "x-requested-with": "XMLHttpRequest",
    }

    # Декодируем base64 в бинарные данные для отправки как grpc-web+proto
    request_body = base64.b64decode(b64_data)
    try:
        async with aiohttp.ClientSession() as session:
            session.cookie_jar.update_cookies(cookies_dict)
            async with session.post(
                url,
                headers=headers,
                data=request_body,
                timeout=4,
            ) as response:
                if response.status != 200:
                    raise HTTPException(
                        status_code=response.status, detail=str(response.status)
                    )

                # Читаем бинарный ответ и кодируем обратно в base64
                response_bytes = await response.read()

        response_b64 = base64.b64encode(response_bytes).decode("utf-8")
        logger.debug(f"Schedule response: {len(response_bytes)} bytes")
        return [response_b64]

    except Exception as e:
        logger.error(f"Ошибка при получении расписания: {e}")
        raise
