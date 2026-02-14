import json
import logging
from typing import Any, Dict, List, Optional

from fastapi import HTTPException

from backend.attendance import _get_user_schedule
from backend.database import DBModel
from backend.mirea_api import get_cookies
from backend.mirea_api.get_lesson_attendance import get_disciplines, get_visiting_logs
from backend.schedule_proto import date_to_base64
from backend.schedule_proto.improved_schedule_decoder import parse_schedule

from .schemas import LessonResponse, ScheduleResponse

logger = logging.getLogger(__name__)


async def get_schedules(
    user_id: int, db: DBModel, year: int, month: int, day: int
) -> ScheduleResponse:
    """
    Получает расписание занятий для пользователя на указанную дату.

    Args:
        user_id: ID пользователя
        db: Экземпляр модели базы данных
        year: Год
        month: Месяц
        day: День

    Returns:
        Объект ScheduleResponse со списком занятий
    """
    try:
        b64_data = date_to_base64(
            year=year,
            month=month,
            day=day,
        )

        user_agent: Optional[str] = await db.get_user_agent(user_id)
        response: str = await _get_user_schedule(
            db=db,
            tg_user_id=user_id,
            b64_data=b64_data,
            user_agent=user_agent,
        )

        # Получаем список дисциплин для точного сопоставления
        disciplines_list: List[str] = []
        try:
            logger.debug(f"Попытка получить список дисциплин для user_id={user_id}")
            user: Optional[Dict[str, Any]] = await db.get_user(user_id)
            logger.debug(f"User получен: {bool(user)}, type: {type(user)}")
            if user and isinstance(user, dict):
                # Получаем cookies
                cookie_record: Optional[Dict[str, Any]] = await db.get_cookie(user_id)
                logger.debug(f"Cookie data получен: {bool(cookie_record)}")
                if cookie_record and cookie_record.get("cookies"):
                    cookie_data: Any = cookie_record["cookies"]
                    # Проверяем тип: если уже dict, не парсим JSON
                    if isinstance(cookie_data, str):
                        cookies: List[Dict[str, Any]] = json.loads(cookie_data)
                    else:
                        cookies = cookie_data
                else:
                    # Получаем новые cookies
                    logger.debug("Получаем новые cookies")
                    cookies_result = await get_cookies.get_cookies(
                        user["login"],
                        user["hashed_password"],
                        user_agent,
                        user_id,
                        db,
                    )
                    cookies = cookies_result[0] if cookies_result else []

                logger.debug(f"Cookies: {bool(cookies)}, type: {type(cookies)}")
                if cookies:
                    logger.debug(f"Cookies sample: {str(cookies)[:200]}")
                # Получаем список журналов (семестров)
                logs: List[Dict[str, Any]] = await get_visiting_logs(
                    cookies, user_agent
                )
                logger.debug(f"Logs получены: {len(logs) if logs else 0}")
                if logs:
                    # Берем текущий семестр
                    current_log: Dict[str, Any] = logs[0]
                    logger.debug(f"Current log ID: {current_log['id']}")
                    # Получаем список дисциплин
                    disciplines: List[Dict[str, Any]] = await get_disciplines(
                        current_log["id"],
                        cookies,
                        user_agent,
                    )
                    logger.debug(f"Disciplines получены: {len(disciplines)}")
                    disciplines_list = [d["name"] for d in disciplines]
                    logger.debug(f"Список дисциплин: {disciplines_list}")
        except Exception as e:
            # Если не удалось получить список дисциплин, продолжаем без него
            logger.exception(f"Не удалось получить список дисциплин: {e}")

        # Парсим расписание с помощью улучшенного декодера
        lessons: List[Dict[str, Any]] = parse_schedule(
            response, disciplines_list=disciplines_list
        )

        # Преобразуем в формат ответа API
        lesson_responses: List[LessonResponse] = [
            LessonResponse(
                uuid=lesson.get("uuid", ""),
                time=lesson.get("time", ""),
                date=lesson.get("date", ""),
                room=lesson.get("room", ""),
                building=lesson.get("building", ""),
                subject=lesson.get("subject", ""),
                teacher=lesson.get("teacher", ""),
                type=lesson.get("type", ""),
                status=lesson.get("status", ""),
            )
            for lesson in lessons
        ]

        return ScheduleResponse(lessons=lesson_responses)

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
