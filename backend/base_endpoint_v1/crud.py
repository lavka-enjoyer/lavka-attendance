import datetime
import logging

from starlette import status

from backend.attendance import TwoFactorRequiredError, get_us_info
from backend.database import DBModel
from backend.mirea_api.get_acs_events import (
    determine_university_status,
    get_acs_events_for_date,
)

from .schemas import (
    CheckUserError,
    CheckUserNeeds2FA,
    CheckUserNeedsLogin,
    CheckUserResult,
    CheckUserSuccess,
    OperationError,
    OperationResult,
    OperationSuccess,
)

logger = logging.getLogger(__name__)


async def _check_user(db: DBModel, tg_user_id: int) -> CheckUserResult:
    """
    Проверяет наличие пользователя в базе данных и возвращает его информацию.

    Args:
        db: Экземпляр модели базы данных
        tg_user_id: ID пользователя в Telegram

    Returns:
        CheckUserSuccess: При успешной проверке с данными пользователя
        CheckUserNeedsLogin: Если пользователю нужно ввести логин/пароль
        CheckUserError: При ошибке
    """
    try:
        info_from_db = await db.get_user_by_id(tg_user_id)
        if not info_from_db:
            # Автоматически создаём пользователя при первом входе
            await db.create_user_simple(tg_userid=tg_user_id, user_agent=None)
            info_from_db = await db.get_user_by_id(tg_user_id)

        if not info_from_db["login"] or not info_from_db["hashed_password"]:
            return CheckUserNeedsLogin()

        user_agent = await db.get_user_agent(tg_user_id)

        user_info: str = await get_us_info(db, tg_user_id, user_agent)

        return CheckUserSuccess(user_info=info_from_db, fio=user_info, is_valid=True)

    except TwoFactorRequiredError:
        logger.info(f"2FA required for user {tg_user_id}")
        return CheckUserNeeds2FA()

    except Exception as ex:
        logger.error(f"Error checking user {tg_user_id}: {ex}", exc_info=True)
        return CheckUserError(status_code=status.HTTP_404_NOT_FOUND, message=str(ex))


async def _edit_allow_confirm(
    db: DBModel, tg_user_id: int, allowconfirm: bool
) -> OperationResult:
    """
    Изменяет разрешение на автоматическую отметку посещаемости.

    Args:
        db: Экземпляр модели базы данных
        tg_user_id: ID пользователя в Telegram
        allowconfirm: Флаг разрешения автоматической отметки

    Returns:
        OperationSuccess: При успехе
        OperationError: При ошибке
    """
    try:
        edit_info = await db.update_user(tg_user_id, **{"allowConfirm": allowconfirm})
        if edit_info:
            return OperationSuccess()
        return OperationError(error="Не удалось обновить данные")
    except Exception as ex:
        logger.error(
            f"Error editing allow_confirm for user {tg_user_id}: {ex}", exc_info=True
        )
        return OperationError(error=str(ex))


async def _delete_user_by_id(db: DBModel, tg_user_id: int) -> OperationResult:
    """
    Удаляет пользователя из базы данных по его Telegram ID.

    Args:
        db: Экземпляр модели базы данных
        tg_user_id: ID пользователя в Telegram

    Returns:
        OperationSuccess: При успешном удалении
        OperationError: При ошибке
    """
    try:
        res = await db.delete_user(tg_user_id)
        if res:
            return OperationSuccess()
        return OperationError(error="Не удалось удалить пользователя")
    except Exception as ex:
        logger.error(f"Error deleting user {tg_user_id}: {ex}", exc_info=True)
        return OperationError(error=str(ex))


async def _get_university_status(db: DBModel, tg_user_id: int) -> dict:
    """
    Получает статус нахождения пользователя в университете на основе событий ACS

    Args:
        db: Экземпляр базы данных
        tg_user_id: ID пользователя в Telegram

    Returns:
        dict: Информация о статусе нахождения в университете
    """
    try:
        import json

        # Получаем куки из базы данных (так же, как в других методах)
        cookie_record = await db.get_cookie(tg_user_id)
        cookies = (
            json.loads(cookie_record["cookies"])
            if cookie_record and cookie_record.get("cookies")
            else None
        )

        if not cookies:
            return {
                "error": "Отсутствуют данные авторизации",
                "is_inside_university": False,
            }

        # Получаем user agent
        user_agent = await db.get_user_agent(tg_user_id)

        # Получаем события ACS за сегодня в московском времени (GMT+3)
        moscow_tz = datetime.timezone(datetime.timedelta(hours=3))
        today = datetime.datetime.now(tz=moscow_tz)
        events = await get_acs_events_for_date(
            cookies, tg_user_id, db, today, user_agent
        )

        # Определяем статус
        status = determine_university_status(events)

        return {
            "is_inside_university": status["is_inside_university"],
            "last_event_time": status["last_event_time"],
            "last_event_details": status["last_event_details"],
            "events_count": len(events),
            "events": events,
        }

    except Exception as ex:
        logger.error(
            f"Error getting university status for user {tg_user_id}: {ex}",
            exc_info=True,
        )
        return {"error": str(ex), "is_inside_university": False}


async def _get_group_university_status(db: DBModel, tg_user_id: int) -> dict:
    """
    Получает статус нахождения всех активированных студентов группы в университете

    Args:
        db: Экземпляр базы данных
        tg_user_id: ID пользователя в Telegram (для определения группы)

    Returns:
        dict: Словарь со списком студентов и их статусами
    """
    try:
        import json

        # Получаем информацию о текущем пользователе для определения группы
        current_user = await db.get_user_by_id(tg_user_id)
        if not current_user:
            return {"error": "Пользователь не найден"}

        group_name = current_user.get("group_name", "")
        if not group_name:
            return {"error": "У пользователя не указана группа"}

        # Получаем всех пользователей группы с полной информацией
        group_users = await db.get_all_users_from_group(group_name)

        if not group_users:
            return {"error": "Нет студентов в группе"}

        result = []
        moscow_tz = datetime.timezone(datetime.timedelta(hours=3))
        today = datetime.datetime.now(tz=moscow_tz)

        # Проходим по каждому студенту группы
        for user in group_users:
            user_tg_id = user.get("tg_userid")

            # Получаем FIO из API МИРЭА (это также обновляет куки если нужно)
            fio = "Неизвестный студент"
            needs_2fa = False
            try:
                # Получаем user_agent и FIO через get_us_info
                user_agent_for_fio = await db.get_user_agent(user_tg_id)
                fio = await get_us_info(db, user_tg_id, user_agent_for_fio)
            except TwoFactorRequiredError:
                # Требуется 2FA - проверим позже
                needs_2fa = True
                # Пробуем получить FIO из БД
                saved_fio = await db.get_fio(user_tg_id)
                fio = saved_fio if saved_fio else f"Студент #{user_tg_id}"
            except Exception as fio_error:
                logger.warning(f"Error getting FIO for user {user_tg_id}: {fio_error}")
                # Пробуем получить FIO из БД
                saved_fio = await db.get_fio(user_tg_id)
                fio = saved_fio if saved_fio else f"Студент #{user_tg_id}"

            # Проверяем наличие cookies (активирован ли студент)
            cookie_record = await db.get_cookie(user_tg_id)
            cookies = (
                json.loads(cookie_record["cookies"])
                if cookie_record and cookie_record.get("cookies")
                else None
            )

            # Если нет кук, проверяем есть ли pending 2FA сессия или требуется 2FA
            if not cookies:
                # Проверяем есть ли активная 2FA сессия
                totp_session = await db.get_totp_session(user_tg_id)
                if needs_2fa or totp_session:
                    result.append(
                        {
                            "fio": fio,
                            "tg_id": user_tg_id,
                            "is_inside_university": False,
                            "needs_2fa": True,
                            "last_event_time": None,
                            "time_in_university": "Требуется 2FA",
                            "time_out_university": "Требуется 2FA",
                            "events_count": 0,
                        }
                    )
                else:
                    # Студент не активирован
                    result.append(
                        {
                            "fio": fio,
                            "tg_id": user_tg_id,
                            "is_inside_university": False,
                            "not_activated": True,
                            "last_event_time": None,
                            "time_in_university": "Не активирован",
                            "time_out_university": "Не активирован",
                            "events_count": 0,
                        }
                    )
                continue

            try:
                # Получаем user agent
                user_agent = await db.get_user_agent(user_tg_id)

                # Получаем события ACS за сегодня
                events = await get_acs_events_for_date(
                    cookies, user_tg_id, db, today, user_agent
                )

                # Определяем статус
                status = determine_university_status(events)

                # Расчет времени в/вне университета
                time_in_university = "Нет данных"
                time_out_university = "Нет данных"
                relevant_event_time = status[
                    "last_event_time"
                ]  # По умолчанию - последнее событие

                if events and len(events) > 0:
                    is_inside = status["is_inside_university"]

                    if is_inside:
                        # Студент сейчас в университете - считаем сколько времени он там
                        last_entry_time = None
                        for event in reversed(events):
                            to_name = event.get("access_point_to", {}).get(
                                "access_point_name", ""
                            )
                            if to_name == "Неконтролируемая территория":
                                # Это вход в университет
                                last_entry_time = event.get("time")
                                break

                        if last_entry_time:
                            # Используем время входа как релевантное событие
                            relevant_event_time = last_entry_time
                            try:
                                # Парсим время входа
                                entry_time = datetime.datetime.strptime(
                                    last_entry_time, "%H:%M:%S"
                                )
                                # Используем московское время для корректного расчета
                                now = datetime.datetime.now(tz=moscow_tz)
                                entry_time = entry_time.replace(
                                    year=now.year,
                                    month=now.month,
                                    day=now.day,
                                    tzinfo=moscow_tz,
                                )

                                # Вычисляем разницу
                                time_diff = now - entry_time
                                hours = int(time_diff.total_seconds() // 3600)
                                minutes = int((time_diff.total_seconds() % 3600) // 60)

                                time_in_university = f"{hours}ч {minutes}м"
                            except Exception as time_ex:
                                logger.warning(
                                    f"Error calculating entry time for user {user_tg_id}: {time_ex}"
                                )
                                time_in_university = f"С {last_entry_time}"
                    else:
                        # Студент не в университете - считаем сколько времени он вне университета
                        last_exit_time = None
                        for event in reversed(events):
                            from_name = event.get("access_point_from", {}).get(
                                "access_point_name", ""
                            )
                            if from_name == "Неконтролируемая территория":
                                # Это выход из университета
                                last_exit_time = event.get("time")
                                break

                        if last_exit_time:
                            # Используем время выхода как релевантное событие
                            relevant_event_time = last_exit_time
                            try:
                                # Парсим время выхода
                                exit_time = datetime.datetime.strptime(
                                    last_exit_time, "%H:%M:%S"
                                )
                                # Используем московское время для корректного расчета
                                now = datetime.datetime.now(tz=moscow_tz)
                                exit_time = exit_time.replace(
                                    year=now.year,
                                    month=now.month,
                                    day=now.day,
                                    tzinfo=moscow_tz,
                                )

                                # Вычисляем разницу
                                time_diff = now - exit_time
                                hours = int(time_diff.total_seconds() // 3600)
                                minutes = int((time_diff.total_seconds() % 3600) // 60)

                                time_out_university = f"{hours}ч {minutes}м"
                            except Exception as time_ex:
                                logger.warning(
                                    f"Error calculating time for user {user_tg_id}: {time_ex}"
                                )
                                time_out_university = f"С {last_exit_time}"
                        else:
                            time_out_university = "Не заходил сегодня"
                else:
                    # Нет событий сегодня
                    time_out_university = "Не заходил сегодня"

                result.append(
                    {
                        "fio": fio,
                        "tg_id": user_tg_id,
                        "is_inside_university": status["is_inside_university"],
                        "last_event_time": relevant_event_time,
                        "time_in_university": time_in_university,
                        "time_out_university": time_out_university,
                        "events_count": len(events),
                    }
                )

            except Exception as user_ex:
                logger.error(
                    f"Error processing user {user_tg_id} in group status: {user_ex}",
                    exc_info=True,
                )
                # Если ошибка для конкретного студента - добавляем с ошибкой
                result.append(
                    {
                        "fio": fio,
                        "tg_id": user_tg_id,
                        "is_inside_university": False,
                        "error": str(user_ex),
                        "time_in_university": "Ошибка",
                        "time_out_university": "Ошибка",
                        "events_count": 0,
                    }
                )

        # Сортируем: сначала кто в университете, потом кто вне,
        # затем требующие 2FA, в конце неактивированные
        result.sort(
            key=lambda x: (
                x.get("not_activated", False),  # Неактивированные в самом конце
                x.get("needs_2fa", False),  # Требующие 2FA перед ними
                not x.get("is_inside_university", False),  # Затем по статусу в унике
                x.get("fio", ""),  # Затем по алфавиту
            )
        )

        return {"students": result}

    except Exception as ex:
        logger.error(
            f"Error getting group university status for user {tg_user_id}: {ex}",
            exc_info=True,
        )
        return {"error": str(ex)}
