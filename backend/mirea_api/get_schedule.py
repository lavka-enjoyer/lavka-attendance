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
        b64_data: Base64-кодированные данные запроса
        user_agent: User-Agent для запроса
        tg_user_id: ID пользователя в Telegram

    Returns:
        Список [данные_ответа]

    Raises:
        HTTPException: При ошибке запроса
    """
    cookies_dict = {cookie["name"]: cookie["value"] for cookie in cookies}
    url = "https://attendance.mirea.ru/rtu_tc.attendance.api.LessonService/GetAvailableLessonsOfVisitingLogs"
    headers = {
        "Accept": "application/grpc-web-text",
        "Accept-Encoding": "gzip, deflate, br, zstd",
        "Accept-Language": "ru-RU,ru;q=0.8,en-US;q=0.5,en;q=0.3",
        "attendance-app-type": "student-app",
        "attendance-app-version": "1.0.0+1273",
        "baggage": (
            "sentry-environment=production,sentry-release=1.0.0%2B1273,"
            "sentry-public_key=37febb3f2d7ebcb778a7f43e0d6aed71,"
            "sentry-trace_id=0529f1e6ed924da5a6f4a1833ec7c72c,"
            "sentry-sample_rate=0.001,sentry-transaction=%2Fsettings,"
            "sentry-sampled=false"
        ),
        "Content-Type": "application/grpc-web-text",
        "Origin": "https://attendance-app.mirea.ru",
        "Referer": "https://attendance-app.mirea.ru/",
        "Sec-Fetch-Dest": "empty",
        "Sec-Fetch-Mode": "cors",
        "Sec-Fetch-Site": "same-site",
        "sentry-trace": "0529f1e6ed924da5a6f4a1833ec7c72c-a6ff3f0039d3494e-0",
        "User-Agent": (
            user_agent
            if user_agent is not None
            else generate_random_mobile_user_agent()
        ),
        "X-Grpc-Web": "1",
        "x-requested-with": "XMLHttpRequest",
        "X-User-Agent": "grpc-web-javascript/0.1",
    }

    request_body = b64_data
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
                        status_code=response.status, detail=response.text
                    )

                response_data = await response.text()

        logger.debug(f"b64_data: {b64_data}")
        return [response_data]

    except Exception as e:
        logger.error(f"Ошибка при получении расписания: {e}")
        raise
