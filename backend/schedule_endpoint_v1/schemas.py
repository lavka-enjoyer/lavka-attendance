from typing import List, Optional

from pydantic import BaseModel


class ScheduleRequest(BaseModel):
    year: int
    month: int
    day: int


class MonthScheduleRequest(BaseModel):
    """Запрос расписания на месяц (для кэширования)"""

    year: int
    month: int


class LessonResponse(BaseModel):
    """Информация об одном занятии"""

    uuid: str
    time: str  # Формат: "10:40 - 12:10"
    date: str  # Формат: "2025-11-14"
    room: Optional[str] = ""
    building: Optional[str] = ""  # Здание: С-20, В-78, СДО
    subject: Optional[str] = ""
    teacher: Optional[str] = ""
    type: Optional[str] = ""  # ЛК, ПР, ЛАБ и т.д.
    status: Optional[str] = ""  # "Н" - не был, "+" - был, "У" - уважительная причина


class ScheduleResponse(BaseModel):
    """Список занятий на день"""

    lessons: List[LessonResponse]


class MonthScheduleResponse(BaseModel):
    """Расписание на месяц (словарь дата -> список занятий)"""

    schedule: dict  # {"2025-11-15": [...], "2025-11-16": [...]}


class AttendanceRequest(BaseModel):
    """Запрос статистики посещаемости по занятию"""

    lesson_date: str  # Формат: "YYYY-MM-DD"
    lesson_time: str  # Формат: "HH:MM"
    lesson_type: str  # "ЛК", "ПР", "ЛАБ"
    lesson_subject: str  # Название предмета
    lesson_index_in_day: int = (
        0  # Индекс пары в дне (0, 1, 2...) - для случая когда несколько пар одного типа
    )


class StudentAttendance(BaseModel):
    """Информация о посещаемости студента"""

    fio: str
    status: str  # "+", "Н", "У"
    status_code: int  # 3 - был, 0/1 - не был, 2 - уважительная


class AttendanceResponse(BaseModel):
    """Ответ со статистикой посещаемости"""

    lesson: dict  # Информация о занятии
    students: List[StudentAttendance]  # Список студентов с их статусами
    total_lessons: int  # Общее количество пар по этому предмету в семестре


class LessonsCalendarResponse(BaseModel):
    """Календарь занятий с количеством пар по дням"""

    calendar: dict  # {"2025": {"11": {1: 4, 2: 3, ...}}}


class LessonsCostResponse(BaseModel):
    """Стоимость посещения пар по предметам для группы"""

    lessons_cost: (
        dict  # {"Предмет 1": 32, "Предмет 2": 28, ...} (количество пар в семестре)
    )
    cached: bool  # Из кеша или получено от API
