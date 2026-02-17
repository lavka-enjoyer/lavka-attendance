import json
import logging
from dataclasses import dataclass
from typing import List, Union

from fastapi import HTTPException

from backend.database import DBModel
from backend.mirea_api import (
    get_cookies,
    get_groups,
    get_lesson_attendance,
    get_me_info,
    get_schedule,
)
from backend.mirea_api import get_user_points as get_points
from backend.mirea_api import (
    self_approve_attendance,
)
from backend.mirea_api.get_cookies import (
    EmailCodeRequired,
    submit_email_code,
)
from backend.tg_endpoint_v1.crud import send_telegram_message

logger = logging.getLogger(__name__)


@dataclass
class EmailCodeRequiredError(Exception):
    """Исключение, когда требуется ввод кода из email."""

    tg_user_id: int
    source: str = "login"
    message: str = "Код подтверждения отправлен на вашу почту"


async def _handle_email_code_result(
    db: DBModel,
    tg_user_id: int,
    result: EmailCodeRequired,
    user_agent: str,
    source: str = "login",
) -> None:
    """
    Сохраняет данные email code сессии в БД.

    Args:
        db: Экземпляр базы данных
        tg_user_id: Telegram ID пользователя
        result: Результат EmailCodeRequired
        user_agent: User agent для запросов
        source: Источник запроса ('login' или 'refresh')
    """
    await db.create_email_code_session(
        tg_userid=tg_user_id,
        session_cookies=json.dumps(result.session_cookies),
        email_code_action_url=result.email_code_action_url,
        user_agent=user_agent,
        source=source,
    )


async def send_email_code_notification(
    db: DBModel, tg_user_id: int, source: str = "login"
) -> bool:
    """
    Отправляет уведомление в Telegram о необходимости ввода email кода.
    Уведомление отправляется максимум 1 раз в 24 часа.

    Args:
        db: Экземпляр базы данных
        tg_user_id: Telegram ID пользователя
        source: Источник запроса

    Returns:
        True если уведомление было отправлено
    """
    try:
        can_send = await db.can_send_email_code_notification(tg_user_id)
        if not can_send:
            logger.info(
                f"Skipping email code notification for user {tg_user_id} - "
                "already sent within 24 hours"
            )
            return False

        message = (
            "📧 <b>Требуется подтверждение по email</b>\n\n"
            "На вашу почту МИРЭА отправлен код подтверждения. "
            "Проверьте почту и введите код в Mini App.\n\n"
            "📱 Откройте Mini App и введите код из письма.\n\n"
            "⚠️ Без ввода кода автоматическая отметка посещаемости не будет работать."
        )

        await send_telegram_message(tg_user_id, message)
        await db.mark_email_code_notification_sent(tg_user_id)

        logger.info(f"Sent email code notification to user {tg_user_id}")
        return True
    except Exception as e:
        logger.error(f"Failed to send email code notification to {tg_user_id}: {e}")
        return False


async def complete_email_code_login(
    db: DBModel,
    tg_user_id: int,
    email_code: str,
) -> Union[List[str], EmailCodeRequired]:
    """
    Завершает проверку email кода.

    Args:
        db: Экземпляр базы данных
        tg_user_id: Telegram ID пользователя
        email_code: Код из email

    Returns:
        Список групп пользователя при полном успехе
        EmailCodeRequired если код неверный

    Raises:
        Exception: Если сессия email кода не найдена или истекла
    """
    email_session = await db.get_email_code_session(tg_user_id)
    if not email_session:
        raise Exception(
            "Сессия email кода не найдена или истекла. Начните авторизацию заново."
        )

    session_cookies = json.loads(email_session["session_cookies"])
    user_agent = email_session.get("user_agent")
    source = email_session.get("source", "login")

    result = await submit_email_code(
        email_code=email_code,
        email_code_action_url=email_session["email_code_action_url"],
        session_cookies=session_cookies,
        user_agent=user_agent,
        tg_user_id=tg_user_id,
    )

    # Если снова требуется email код (неверный код)
    if isinstance(result, EmailCodeRequired):
        await db.update_email_code_session(
            tg_userid=tg_user_id,
            session_cookies=json.dumps(result.session_cookies),
            email_code_action_url=result.email_code_action_url,
        )
        return result

    # Удаляем email code сессию - она больше не нужна
    await db.delete_email_code_session(tg_user_id)

    # Успех — cookies получены
    cookies = result[0]
    await db.create_cookie(tg_user_id, json.dumps(cookies))

    # Получаем FIO пользователя и сохраняем в БД
    try:
        me_info = await get_me_info.get_me_info_full(
            cookies, tg_user_id, db, user_agent=user_agent
        )
        fio = me_info.get("fio", "")
        if fio:
            await db.update_fio(tg_user_id, fio)
            logger.info(f"Saved FIO for user {tg_user_id}: {fio}")
    except Exception as e:
        logger.error(f"Error getting FIO after email code for {tg_user_id}: {e}")

    if source == "login":
        # Получаем группы
        try:
            groups = await get_groups.get_group(
                cookies, tg_user_id, db, user_agent=user_agent
            )
            if groups and groups[0]:
                # Сохраняем группу в БД
                group_name = groups[0][-1]  # последняя = актуальная
                await db.update_user(tg_user_id, group_name=group_name)
                logger.info(f"Saved group for user {tg_user_id}: {group_name}")
            return groups[0]
        except Exception as e:
            logger.error(f"Error getting groups after email code for {tg_user_id}: {e}")
            return []

    return []


async def _check_existing_email_session(db: DBModel, tg_user_id: int, source: str = "refresh", notify: bool = False):
    """
    Проверяет, есть ли уже активная email code сессия.
    Если есть — сразу кидает EmailCodeRequiredError без повторного логина.
    """
    existing_session = await db.get_email_code_session(tg_user_id)
    if existing_session:
        logger.info(
            f"Active email code session already exists for user {tg_user_id}, "
            "skipping re-auth to prevent email spam"
        )
        if notify:
            await send_email_code_notification(db, tg_user_id, source=source)
        raise EmailCodeRequiredError(tg_user_id=tg_user_id, source=source)


async def get_us_info(db, tgID, user_agent=None, notify_on_2fa=False):
    """
    Получает данные пользователя с использованием куки.
    Если куки отсутствуют или неверны, получает их из логина/пароля из БД.
    Если требуется 2FA, сохраняет сессию.

    Args:
        db: Экземпляр базы данных
        tgID: Telegram ID пользователя
        user_agent: User-Agent для запросов
        notify_on_2fa: Отправлять ли уведомление в Telegram при 2FA
            (False для интерактивных сессий Mini App, True для фоновых операций)

    Raises:
        EmailCodeRequiredError: Если требуется ввод кода из email
        Exception: При других ошибках
    """
    try:
        # Пытаемся получить куки из БД
        cookie_record = await db.get_cookie(tgID)
        cookies = (
            json.loads(cookie_record["cookies"])
            if cookie_record and cookie_record.get("cookies")
            else None
        )

        # Сначала пытаемся получить информацию с существующими куки
        if cookies:
            try:
                info = await get_me_info.get_me_info_data(
                    cookies, tgID, db, user_agent=user_agent
                )
                if info[0].strip():
                    return info[0]
            except Exception as e:
                # Если не удалось, продолжаем обновление куки
                logger.debug(
                    f"Failed to get info with existing cookies for {tgID}: {e}"
                )

        # Если дошли сюда — куки отсутствуют или не работают
        # Проверяем, есть ли уже активная email code сессия (предотвращаем спам)
        await _check_existing_email_session(db, tgID, source="refresh", notify=notify_on_2fa)

        # Получаем учётные данные пользователя и обновляем куки
        user = await db.get_user(tgID)
        if not user:
            raise Exception("Пользователь не найден")

        try:
            # Получаем новые куки
            cookies_result = await get_cookies.get_cookies(
                user["login"],
                user["hashed_password"],
                user_agent,
                tgID,
                db,
            )

            # Проверяем, не требуется ли ввод email кода
            if isinstance(cookies_result, EmailCodeRequired):
                logger.info(f"Email code required for user {tgID} during get_us_info")

                # Если у пользователя уже были куки, значит он авторизован,
                # но get_me_info вернул неожиданный ответ. Пробуем FIO из БД,
                # чтобы не зацикливать на повторный ввод email кода.
                if cookies:
                    user_by_id = await db.get_user_by_id(tgID)
                    saved_fio = user_by_id.get("fio") if user_by_id else None
                    if saved_fio:
                        logger.info(
                            f"Using saved FIO for {tgID} instead of requiring email code"
                        )
                        return saved_fio

                await _handle_email_code_result(
                    db, tgID, cookies_result, user_agent, source="refresh"
                )
                if notify_on_2fa:
                    await send_email_code_notification(db, tgID, source="refresh")
                raise EmailCodeRequiredError(tg_user_id=tgID, source="refresh")

            await db.create_cookie(tgID, json.dumps(cookies_result[0]))

            # Пробуем снова с новыми куки
            info = await get_me_info.get_me_info_data(
                cookies_result[0], tgID, db, user_agent=user_agent
            )
            if info[0].strip():
                return info[0]
            else:
                raise Exception("Неправильный логин или пароль")
        except EmailCodeRequiredError:
            raise
        except Exception as e:
            raise Exception(f"Ошибка обновления cookies: {str(e)}")

    except EmailCodeRequiredError:
        raise
    except Exception as e:
        raise Exception(f"Ошибка в get_us_info: {str(e)}")


async def self_approve(db, tgID, token, user_agent=None):
    """
    Подтверждает посещение, используя куки.
    Если куки отсутствуют или запрос возвращает 401, обновляет куки и повторяет попытку.
    Если требуется 2FA, сохраняет сессию и отправляет уведомление в Telegram.

    Raises:
        EmailCodeRequiredError: Если требуется ввод кода из email
        Exception: При других ошибках
    """
    try:
        cookie_record = await db.get_cookie(tgID)
        cookies = (
            json.loads(cookie_record["cookies"])
            if cookie_record and cookie_record.get("cookies")
            else None
        )

        if cookies:
            try:
                result = await self_approve_attendance.send_self_approve_attendance(
                    token, cookies, tgID, db, user_agent=user_agent
                )
                return result[0]
            except Exception as e:
                if "401" not in str(e):
                    raise e

        # Проверяем, есть ли уже активная email code сессия (предотвращаем спам)
        await _check_existing_email_session(db, tgID, source="refresh", notify=True)

        user = await db.get_user(tgID)
        if not user:
            raise Exception("Пользователь не найден")

        cookies_result = await get_cookies.get_cookies(
            user["login"],
            user["hashed_password"],
            user_agent,
            tgID,
            db,
        )

        # Проверяем, не требуется ли ввод email кода
        if isinstance(cookies_result, EmailCodeRequired):
            logger.info(f"Email code required for user {tgID} during self_approve")
            await _handle_email_code_result(
                db, tgID, cookies_result, user_agent, source="refresh"
            )
            await send_email_code_notification(db, tgID, source="refresh")
            raise EmailCodeRequiredError(tg_user_id=tgID, source="refresh")

        await db.create_cookie(tgID, json.dumps(cookies_result[0]))
        result = await self_approve_attendance.send_self_approve_attendance(
            token,
            cookies_result[0],
            tgID,
            db,
            user_agent=user_agent,
        )
        return result[0]

    except EmailCodeRequiredError:
        raise
    except Exception as e:
        raise Exception(f"Неправильный логин или пароль: {str(e)}")


async def add_data_for_login(
    db,
    tgID,
    login,
    password,
    user_agent=None,
):
    """
    Добавляет или обновляет логин и пароль в БД.
    Перед сохранением проверяет корректность данных с помощью get_us_info.
    В случае успеха сохраняет данные и возвращает список групп.

    Returns:
        Список групп пользователя

    Raises:
        EmailCodeRequiredError: Если требуется ввод кода из email
        Exception: При ошибке авторизации
    """
    try:
        # Пробуем получить куки по введённым данным
        result = await get_cookies.get_cookies(login, password, user_agent, tgID, db)

        # Проверяем, не требуется ли ввод email кода
        if isinstance(result, EmailCodeRequired):
            logger.info(f"Email code required for user {tgID} during login")
            # Сохраняем данные пользователя и email code сессию
            await db.create_user_simple(
                tg_userid=tgID,
                login=login,
                password=password,
                user_agent=user_agent,
            )
            await _handle_email_code_result(db, tgID, result, user_agent, source="login")
            raise EmailCodeRequiredError(tg_user_id=tgID, source="login")

        cookies = result
        logger.debug("add_data_for_login: cookies obtained")

        try:
            info = await get_me_info.get_me_info_data(
                cookies[0], tgID, db, user_agent=user_agent
            )
            if not info[0].strip():
                raise Exception("Пустой ответ от GetMeInfo")
        except Exception:
            raise Exception("Неправильный логин или пароль")

        # Возвращаем список групп
        groups = await get_groups.get_group(cookies[0], tgID, db, user_agent=user_agent)

        # Если проверка успешна, сохраняем данные пользователя и куки
        await db.create_user_simple(
            tg_userid=tgID,
            login=login,
            password=password,
            group=groups[0][-1],
            user_agent=user_agent,
        )
        await db.create_cookie(tgID, json.dumps(cookies[0]))

        return groups[0]
    except EmailCodeRequiredError:
        raise
    except Exception as e:
        raise Exception(f"Ошибка в add_data_for_login: {str(e)}")


async def check_login_and_pass(db, tg_userid, login, password, user_agent=None):
    """
    Проверяет корректность логина и пароля без сохранения в базу.

    Args:
        db: Экземпляр DBModel для работы с базой данных
        tg_userid: Telegram ID пользователя
        login: Логин для проверки
        password: Пароль для проверки
        user_agent: User agent для HTTP запросов

    Returns:
        Список групп пользователя

    Raises:
        EmailCodeRequiredError: Если требуется ввод кода из email
        Exception: При ошибке проверки или неверных данных
    """
    try:
        # Пробуем получить куки по введённым данным
        result = await get_cookies.get_cookies(
            login, password, user_agent, tg_userid, db
        )

        # Проверяем, не требуется ли ввод email кода
        if isinstance(result, EmailCodeRequired):
            logger.info(
                f"Email code required for user {tg_userid} during check_login_and_pass"
            )
            await _handle_email_code_result(
                db, tg_userid, result, user_agent, source="login"
            )
            raise EmailCodeRequiredError(tg_user_id=tg_userid, source="login")

        cookies = result
        try:
            info = await get_me_info.get_me_info_data(
                cookies[0], tg_userid, db, user_agent=user_agent
            )
            if not info[0].strip():
                raise Exception("Пустой ответ от GetMeInfo")
        except Exception:
            raise Exception("Неправильный логин или пароль")
        groups = await get_groups.get_group(
            cookies[0], tg_userid, db, user_agent=user_agent
        )
        return groups[0]
    except EmailCodeRequiredError:
        raise
    except Exception as e:
        raise Exception(f"Ошибка в check_login_and_pass: {str(e)}")


async def get_user_points(db, tgID, user_agent=None):
    """
    Получает баллы.

    Raises:
        EmailCodeRequiredError: Если требуется ввод кода из email
        Exception: При других ошибках
    """
    try:
        # Получаем куки из базы
        cookie_record = await db.get_cookie(tgID)
        cookies = (
            json.loads(cookie_record["cookies"])
            if cookie_record and cookie_record.get("cookies")
            else None
        )
        if cookies:
            try:
                res_from_att = await get_points._get_points_data(
                    cookies=cookies,
                    db=db,
                    user_agent=user_agent,
                    tg_user_id=tgID,
                )
                return res_from_att[0]
            except Exception as e:
                if "401" not in str(e):
                    raise e
                # Если ошибка 401, продолжаем для обновления кук

        # Проверяем, есть ли уже активная email code сессия (предотвращаем спам)
        await _check_existing_email_session(db, tgID, source="refresh")

        # Получаем или обновляем куки
        user = await db.get_user(tgID)
        if not user:
            raise Exception("Пользователь не найден")
        cookies_result = await get_cookies.get_cookies(
            user["login"],
            user["hashed_password"],
            user_agent,
            tgID,
            db,
        )

        # Проверяем, не требуется ли ввод email кода
        if isinstance(cookies_result, EmailCodeRequired):
            logger.info(f"Email code required for user {tgID} during get_user_points")
            await _handle_email_code_result(
                db, tgID, cookies_result, user_agent, source="refresh"
            )
            raise EmailCodeRequiredError(tg_user_id=tgID, source="refresh")

        await db.create_cookie(tgID, json.dumps(cookies_result[0]))
        res_from_att = await get_points._get_points_data(
            cookies_result[0],
            db=db,
            user_agent=user_agent,
            tg_user_id=tgID,
        )
        return res_from_att[0]

    except EmailCodeRequiredError:
        raise
    except Exception as e:
        raise Exception(f"Что то пошло не так ;( Ошибка - {str(e)}")


async def _get_user_schedule(
    db: DBModel,
    tgID: int = None,
    tg_user_id: int = None,
    b64_data: str = None,
    user_agent=None,
):
    """
    Получает расписание пользователя.

    Args:
        db: Экземпляр DBModel для работы с базой данных
        tgID: Telegram ID пользователя (deprecated, используйте tg_user_id)
        tg_user_id: Telegram ID пользователя
        b64_data: Base64 закодированные данные для получения расписания
        user_agent: User agent для HTTP запросов (опционально)

    Returns:
        Данные расписания пользователя

    Raises:
        EmailCodeRequiredError: Если требуется ввод кода из email
        HTTPException: При ошибке получения данных
    """
    # Поддержка обоих вариантов именования
    user_id = tg_user_id if tg_user_id is not None else tgID

    try:
        cookie_record = await db.get_cookie(user_id)
        cookies = (
            json.loads(cookie_record["cookies"])
            if cookie_record and cookie_record.get("cookies")
            else None
        )

        if cookies:
            try:
                res_from_att = await get_schedule.get_user_schedule(
                    cookies=cookies,
                    db=db,
                    user_agent=user_agent,
                    tg_user_id=tgID,
                    b64_data=b64_data,
                )
                return res_from_att[0]
            except Exception as e:
                if "401" not in str(e):
                    raise e
                # Если ошибка 401, продолжаем для обновления кук

        # Проверяем, есть ли уже активная email code сессия (предотвращаем спам)
        await _check_existing_email_session(db, user_id, source="refresh")

        # Получаем или обновляем куки
        user = await db.get_user(user_id)
        if not user:
            raise Exception("Пользователь не найден")
        cookies_result = await get_cookies.get_cookies(
            user["login"],
            user["hashed_password"],
            user_agent,
            user_id,
            db,
        )

        # Проверяем, не требуется ли ввод email кода
        if isinstance(cookies_result, EmailCodeRequired):
            logger.info(f"Email code required for user {user_id} during _get_user_schedule")
            await _handle_email_code_result(
                db, user_id, cookies_result, user_agent, source="refresh"
            )
            raise EmailCodeRequiredError(tg_user_id=user_id, source="refresh")

        await db.create_cookie(user_id, json.dumps(cookies_result[0]))
        res_from_att = await get_schedule.get_user_schedule(
            cookies=cookies_result[0],
            db=db,
            user_agent=user_agent,
            tg_user_id=user_id,
            b64_data=b64_data,
        )
        return res_from_att[0]

    except EmailCodeRequiredError:
        raise
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail="Internal server error")


async def get_lesson_attendance_info(
    db: DBModel,
    tgID: int = None,
    tg_user_id: int = None,
    lesson_date: str = None,
    lesson_time: str = None,
    lesson_type: str = None,
    lesson_subject: str = None,
    lesson_index_in_day: int = 0,
    user_agent=None,
):
    """
    Получает информацию о посещаемости для конкретного занятия.

    Raises:
        EmailCodeRequiredError: Если требуется ввод кода из email
        HTTPException: При ошибке получения данных
    """
    # Поддержка обоих вариантов именования
    user_id = tg_user_id if tg_user_id is not None else tgID

    try:
        # Получаем куки из базы
        cookie_record = await db.get_cookie(user_id)
        cookies = (
            json.loads(cookie_record["cookies"])
            if cookie_record and cookie_record.get("cookies")
            else None
        )

        if cookies:
            try:
                res_from_att = await get_lesson_attendance.get_lesson_attendance_data(
                    cookies=cookies,
                    lesson_date=lesson_date,
                    lesson_time=lesson_time,
                    lesson_type=lesson_type,
                    lesson_subject=lesson_subject,
                    lesson_index_in_day=lesson_index_in_day,
                    db=db,
                    user_agent=user_agent,
                    tg_user_id=user_id,
                )
                if res_from_att[0] is not None:
                    return res_from_att[0]
            except Exception as e:
                if "401" not in str(e):
                    raise e
                # Если ошибка 401, продолжаем для обновления кук

        # Проверяем, есть ли уже активная email code сессия (предотвращаем спам)
        await _check_existing_email_session(db, user_id, source="refresh")

        # Получаем или обновляем куки
        user = await db.get_user(user_id)
        if not user:
            raise Exception("Пользователь не найден")

        cookies_result = await get_cookies.get_cookies(
            user["login"],
            user["hashed_password"],
            user_agent,
            user_id,
            db,
        )

        # Проверяем, не требуется ли ввод email кода
        if isinstance(cookies_result, EmailCodeRequired):
            logger.info(
                f"Email code required for user {user_id} during get_lesson_attendance_info"
            )
            await _handle_email_code_result(
                db, user_id, cookies_result, user_agent, source="refresh"
            )
            raise EmailCodeRequiredError(tg_user_id=user_id, source="refresh")

        await db.create_cookie(user_id, json.dumps(cookies_result[0]))
        res_from_att = await get_lesson_attendance.get_lesson_attendance_data(
            cookies=cookies_result[0],
            lesson_date=lesson_date,
            lesson_time=lesson_time,
            lesson_type=lesson_type,
            lesson_subject=lesson_subject,
            lesson_index_in_day=lesson_index_in_day,
            db=db,
            user_agent=user_agent,
            tg_user_id=user_id,
        )
        return res_from_att[0]

    except EmailCodeRequiredError:
        raise
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500, detail="Ошибка получения данных о посещаемости"
        )
