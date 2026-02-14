import json
import logging
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, status

from backend.attendance import get_lesson_attendance_info
from backend.dependencies import init_data
from backend.mirea_api.get_lessons_calendar import get_daily_lessons_count
from backend.mirea_api.lessons_cost_cache import LessonsCostCache
from backend.utils_helper import db

from .crud import get_schedules
from .schedule_cache import MIREAScheduleCache
from .schemas import (
    AttendanceRequest,
    AttendanceResponse,
    LessonsCalendarResponse,
    LessonsCostResponse,
    MonthScheduleRequest,
    MonthScheduleResponse,
    ScheduleRequest,
    ScheduleResponse,
    StudentAttendance,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/schedule", tags=["schedule"])


@router.post("/", response_model=ScheduleResponse)
async def get_schedule(
    data: ScheduleRequest,
    user_id: int = Depends(init_data),
) -> ScheduleResponse:
    """
    Получить расписание занятий на указанную дату

    Args:
        data: Запрос с датой (год, месяц, день)
        user_id: ID пользователя (из токена)

    Returns:
        ScheduleResponse: Список занятий на указанную дату с полной информацией
    """
    try:
        await db.connect()

        return await get_schedules(
            db=db,
            user_id=user_id,
            year=data.year,
            month=data.month,
            day=data.day,
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e)
        )
    finally:
        await db.disconnect()


@router.post("/attendance", response_model=AttendanceResponse)
async def get_lesson_attendance(
    data: AttendanceRequest,
    user_id: int = Depends(init_data),
) -> AttendanceResponse:
    """
    Получить статистику посещаемости для конкретного занятия

    Args:
        data: Запрос с данными о занятии (дата, время, тип, предмет)
        user_id: ID пользователя (из токена)

    Returns:
        AttendanceResponse: Информация о занятии и список студентов с их статусами
    """
    try:
        await db.connect()

        # Получаем группу пользователя
        user: Optional[Dict[str, Any]] = await db.get_user(user_id)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Пользователь не найден"
            )

        group_name: str = user.get("group_name", "")

        # Получаем user_agent
        user_agent: Optional[str] = await db.get_user_agent(user_id)

        # Получаем cookies
        cookie_record: Optional[Dict[str, Any]] = await db.get_cookie(user_id)
        cookies: Optional[List[Dict[str, Any]]] = (
            json.loads(cookie_record["cookies"])
            if cookie_record and cookie_record.get("cookies")
            else None
        )

        if not cookies:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED, detail="Cookies не найдены"
            )

        # Сначала пытаемся получить количество пар из кеша
        total_lessons: Optional[int] = (
            await LessonsCostCache.get_or_fetch_lessons_count(
                db=db,
                group_name=group_name,
                subject_name=data.lesson_subject,
                cookies=cookies,
                lesson_date=data.lesson_date,
                lesson_time=data.lesson_time,
                lesson_type=data.lesson_type,
                lesson_index_in_day=data.lesson_index_in_day,
                user_agent=user_agent,
                tg_user_id=user_id,
            )
        )

        # Получаем данные о посещаемости
        attendance_data: Optional[Dict[str, Any]] = await get_lesson_attendance_info(
            db=db,
            tg_user_id=user_id,
            lesson_date=data.lesson_date,
            lesson_time=data.lesson_time,
            lesson_type=data.lesson_type,
            lesson_subject=data.lesson_subject,
            lesson_index_in_day=data.lesson_index_in_day,
            user_agent=user_agent,
        )

        if not attendance_data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Данные о посещаемости не найдены",
            )

        # Преобразуем в формат ответа API
        students: List[StudentAttendance] = [
            StudentAttendance(
                fio=student["fio"],
                status=student["status"],
                status_code=student["status_code"],
            )
            for student in attendance_data["students"]
        ]

        # Используем закешированное значение, если оно есть, иначе из данных
        if total_lessons is None:
            total_lessons = attendance_data.get("total_lessons", 0)

        return AttendanceResponse(
            lesson=attendance_data["lesson"],
            students=students,
            total_lessons=total_lessons,
        )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e)
        )
    finally:
        await db.disconnect()


@router.post("/month-cache", response_model=MonthScheduleResponse)
async def get_month_schedule_cache(
    data: MonthScheduleRequest,
    user_id: int = Depends(init_data),
) -> MonthScheduleResponse:
    """
    Получить расписание группы на месяц (для кэширования точек в календаре)

    Получает расписание через авторизованное API для каждого дня месяца.

    Args:
        data: Запрос с годом и месяцем
        user_id: ID пользователя

    Returns:
        MonthScheduleResponse: Словарь {дата: [список занятий]}
    """
    try:
        await db.connect()

        logger.debug(f"Запрос на {data.year}-{data.month:02d}")

        # Получаем группу пользователя
        user: Optional[Dict[str, Any]] = await db.get_user(user_id)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Пользователь не найден"
            )

        group_name: str = user.get("group_name", "")
        if not group_name:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="У пользователя не указана группа",
            )

        # Получаем расписание через публичное API с поддержкой RRULE и EXDATE
        schedule_dict: Dict[str, List[Dict[str, Any]]] = (
            await MIREAScheduleCache.get_month_schedule(
                group_name, data.year, data.month
            )
        )

        logger.debug(f"Получено {len(schedule_dict)} дней с занятиями")

        return MonthScheduleResponse(schedule=schedule_dict)

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e)
        )
    finally:
        await db.disconnect()


@router.get("/lessons-cost", response_model=LessonsCostResponse)
async def get_lessons_cost_endpoint(
    user_id: int = Depends(init_data),
) -> LessonsCostResponse:
    """
    Получить стоимость посещения пар (количество пар в семестре) для всех предметов группы

    Возвращает кешированные данные или пустой словарь, если кеш пуст.
    Кеш обновляется автоматически при запросах к эндпоинту /attendance

    Returns:
        LessonsCostResponse: Словарь {предмет: количество_пар}
    """
    try:
        await db.connect()

        logger.debug("Запрос стоимости пар для группы")

        # Получаем группу пользователя
        user: Optional[Dict[str, Any]] = await db.get_user(user_id)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Пользователь не найден"
            )

        group_name: str = user.get("group_name", "")
        if not group_name:
            logger.debug("У пользователя не указана группа")
            return LessonsCostResponse(lessons_cost={}, cached=False)

        logger.debug(f"Группа: {group_name}")

        # Получаем кеш для группы
        cache: Optional[Dict[str, int]] = await LessonsCostCache.get_cache_from_db(
            db, group_name
        )

        if cache:
            logger.debug(f"Возвращаем кеш ({len(cache)} предметов)")
            return LessonsCostResponse(lessons_cost=cache, cached=True)
        else:
            logger.debug("Кеш пуст")
            return LessonsCostResponse(lessons_cost={}, cached=False)

    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"Ошибка: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e)
        )
    finally:
        await db.disconnect()


@router.get("/lessons-calendar", response_model=LessonsCalendarResponse)
async def get_lessons_calendar_endpoint(
    user_id: int = Depends(init_data),
    start_ts: Optional[int] = None,
    end_ts: Optional[int] = None,
) -> LessonsCalendarResponse:
    """
    Получить календарь занятий (количество пар по дням) используя приватное API

    Args:
        start_ts: Unix timestamp начала периода (опционально)
        end_ts: Unix timestamp конца периода (опционально)

    Возвращает календарь в формате:
    {
        "2025": {
            "11": {1: 4, 2: 3, ...},
            "09": {1: 2, 4: 3, ...}
        }
    }
    """
    try:
        await db.connect()

        logger.debug(f"Получение календаря: start_ts={start_ts}, end_ts={end_ts}")

        # Получаем данные пользователя
        user: Optional[Dict[str, Any]] = await db.get_user(user_id)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Пользователь не найден"
            )

        # Получаем user_agent
        user_agent: Optional[str] = await db.get_user_agent(user_id)

        # Получаем cookies
        cookie_record: Optional[Dict[str, Any]] = await db.get_cookie(user_id)
        cookies: Optional[List[Dict[str, Any]]] = (
            json.loads(cookie_record["cookies"])
            if cookie_record and cookie_record.get("cookies")
            else None
        )

        if not cookies:
            logger.warning("Cookies не найдены, возвращаем пустой календарь")
            return LessonsCalendarResponse(calendar={})

        logger.debug(f"Получаем календарь для user_id={user_id}")

        # Используем приватное API для получения календаря
        calendar: Optional[Dict[str, Dict[str, Dict[int, int]]]] = (
            await get_daily_lessons_count(
                cookies=cookies,
                user_agent=user_agent,
                start_ts=start_ts,
                end_ts=end_ts,
            )
        )

        if calendar:
            total_days = sum(
                len(days) for months in calendar.values() for days in months.values()
            )
            logger.debug(f"Получено {total_days} дней с занятиями")
            logger.debug(f"Годы в календаре: {list(calendar.keys())}")
            return LessonsCalendarResponse(calendar=calendar)
        else:
            logger.debug("Календарь пуст")
            return LessonsCalendarResponse(calendar={})

    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"Ошибка: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e)
        )
    finally:
        await db.disconnect()
