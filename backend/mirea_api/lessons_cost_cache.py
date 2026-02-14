"""
Модуль для кеширования стоимости посещения пар по группам

Кеш хранит:
- Группа
- Предмет
- Количество пар в семестре (total_lessons)
- Дата последнего обновления

Кеш обновляется раз в месяц или по запросу
"""

import json
import logging
from datetime import datetime, timedelta, timezone
from typing import Dict, Optional

from backend.mirea_api.get_lesson_attendance import get_lesson_attendance_data

logger = logging.getLogger(__name__)


class LessonsCostCache:
    """Класс для работы с кешем стоимости посещений"""

    @staticmethod
    async def get_cache_from_db(db, group_name: str) -> Optional[Dict[str, int]]:
        """
        Получить кеш из БД для группы.

        Args:
            db: Объект подключения к базе данных
            group_name: Название группы

        Returns:
            Словарь {название_предмета: количество_пар} или None если кеша нет или он устарел
        """
        try:
            # Получаем кеш из БД
            result = await db.pool.fetchrow(
                """
                SELECT subjects_data, last_updated
                FROM lessons_cost_cache
                WHERE group_name = $1
                """,
                group_name,
            )

            if not result:
                logger.info(f"Кеш для группы {group_name} не найден")
                return None

            # Проверяем возраст кеша (обновляем раз в месяц)
            last_updated = result["last_updated"]
            now = datetime.now(timezone.utc)
            age = now - last_updated

            if age > timedelta(days=30):
                logger.info(
                    f"Кеш для группы {group_name} устарел (возраст: {age.days} дней)"
                )
                return None

            # Парсим JSON с данными о предметах
            subjects_data = json.loads(result["subjects_data"])
            logger.info(
                f"Найден кеш для группы {group_name} ({len(subjects_data)} предметов)"
            )
            return subjects_data

        except Exception as e:
            logger.error(f"Ошибка при получении кеша: {e}")
            return None

    @staticmethod
    async def update_cache_in_db(db, group_name: str, subjects_data: Dict[str, int]):
        """
        Обновить кеш в БД для группы.

        Args:
            db: Объект подключения к базе данных
            group_name: Название группы
            subjects_data: Словарь {название_предмета: количество_пар}

        Raises:
            Exception: При ошибках обновления кеша
        """
        try:
            now = datetime.now(timezone.utc)
            subjects_json = json.dumps(subjects_data, ensure_ascii=False)

            # Используем UPSERT (INSERT ... ON CONFLICT)
            await db.pool.execute(
                """
                INSERT INTO lessons_cost_cache (group_name, subjects_data, last_updated)
                VALUES ($1, $2, $3)
                ON CONFLICT (group_name)
                DO UPDATE SET
                    subjects_data = EXCLUDED.subjects_data,
                    last_updated = EXCLUDED.last_updated
                """,
                group_name,
                subjects_json,
                now,
            )

            logger.info(
                f"Кеш обновлён для группы {group_name} ({len(subjects_data)} предметов)"
            )

        except Exception as e:
            logger.error(f"Ошибка при обновлении кеша: {e}")
            raise

    @staticmethod
    async def get_or_fetch_lessons_count(
        db,
        group_name: str,
        subject_name: str,
        cookies: list,
        lesson_date: str,
        lesson_time: str,
        lesson_type: str,
        lesson_index_in_day: int = 0,
        user_agent: Optional[str] = None,
        tg_user_id: Optional[int] = None,
    ) -> Optional[int]:
        """
        Получить количество пар для предмета из кеша или запросить у API.

        Args:
            db: Объект подключения к базе данных
            group_name: Название группы
            subject_name: Название предмета
            cookies: Список куки пользователя
            lesson_date: Дата занятия
            lesson_time: Время занятия
            lesson_type: Тип занятия
            lesson_index_in_day: Индекс пары в дне
            user_agent: User-Agent для запроса
            tg_user_id: ID пользователя в Telegram

        Returns:
            Количество пар в семестре или None
        """
        try:
            # Получаем кеш для группы
            cache = await LessonsCostCache.get_cache_from_db(db, group_name)

            # Если кеш есть и предмет в нём - возвращаем
            if cache and subject_name in cache:
                total_lessons = cache[subject_name]
                logger.info(
                    f"Используем кеш для {group_name}/{subject_name}: {total_lessons} пар"
                )
                return total_lessons

            # Кеша нет или предмета нет в кеше - запрашиваем у API
            logger.info(f"Запрашиваем данные для {group_name}/{subject_name} у API...")

            result = await get_lesson_attendance_data(
                cookies=cookies,
                lesson_date=lesson_date,
                lesson_time=lesson_time,
                lesson_type=lesson_type,
                lesson_subject=subject_name,
                lesson_index_in_day=lesson_index_in_day,
                db=db,
                user_agent=user_agent,
                tg_user_id=tg_user_id,
            )

            if result and result[0] and "total_lessons" in result[0]:
                total_lessons = result[0]["total_lessons"]
                logger.info(f"Получено от API: {total_lessons} пар")

                # Обновляем кеш
                if cache is None:
                    cache = {}

                cache[subject_name] = total_lessons
                await LessonsCostCache.update_cache_in_db(db, group_name, cache)

                return total_lessons

            return None

        except Exception as e:
            logger.error(f"Ошибка при получении количества пар: {e}")
            return None

    @staticmethod
    async def prefetch_group_subjects(
        db,
        group_name: str,
        cookies: list,
        user_agent: Optional[str] = None,
        tg_user_id: Optional[int] = None,
    ) -> None:
        """
        Предзагрузка данных для всех предметов группы.

        Эта функция может быть вызвана периодически (например, раз в неделю)
        для обновления кеша для всех предметов группы.

        Args:
            db: Объект подключения к базе данных
            group_name: Название группы
            cookies: Список куки пользователя из группы
            user_agent: User-Agent для запроса
            tg_user_id: ID пользователя в Telegram
        """
        try:
            logger.info(f"Начинаем предзагрузку для группы {group_name}")

            # Здесь можно реализовать логику получения списка всех предметов группы
            # и загрузки данных для каждого предмета
            # Но для начала просто обновим существующий кеш при первом запросе

            logger.info(f"Предзагрузка завершена для группы {group_name}")

        except Exception as e:
            logger.error(f"Ошибка при предзагрузке: {e}")
