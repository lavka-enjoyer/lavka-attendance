import json
import logging
from dataclasses import dataclass
from typing import List, Union

import pyotp
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
from backend.mirea_api.get_cookies import TwoFactorRequired, submit_otp_code
from backend.tg_endpoint_v1.crud import send_telegram_message

logger = logging.getLogger(__name__)


async def try_auto_2fa(
    db: DBModel,
    tg_user_id: int,
    two_factor_result: TwoFactorRequired,
    user_agent: str = None,
) -> Union[dict, None]:
    """
    Пытается автоматически завершить 2FA, если у пользователя сохранён TOTP секрет.

    Args:
        db: Экземпляр базы данных
        tg_user_id: Telegram ID пользователя
        two_factor_result: Результат TwoFactorRequired с данными сессии
        user_agent: User agent для запросов

    Returns:
        dict с cookies при успехе, None если автоматическая 2FA невозможна
    """
    try:
        # Проверяем наличие сохранённого секрета
        totp_secret = await db.get_totp_secret(tg_user_id)
        if not totp_secret:
            logger.debug(f"No TOTP secret for user {tg_user_id}, auto-2FA not possible")
            return None

        # Проверяем, есть ли сохранённый credential_id для авто-TOTP
        saved_credential_id = await db.get_totp_credential_id(tg_user_id)
        credential_id = saved_credential_id or two_factor_result.credential_id

        if saved_credential_id:
            logger.info(f"Using saved credential_id for user {tg_user_id}: {saved_credential_id}")
        else:
            logger.info(f"Using default credential_id for user {tg_user_id}: {credential_id}")

        # Генерируем TOTP код
        totp = pyotp.TOTP(totp_secret)
        otp_code = totp.now()
        logger.info(f"Auto-generating TOTP code for user {tg_user_id}")

        # Отправляем код
        result = await submit_otp_code(
            otp_code=otp_code,
            otp_action_url=two_factor_result.otp_action_url,
            credential_id=credential_id,
            session_cookies=two_factor_result.session_cookies,
            user_agent=user_agent,
            tg_user_id=tg_user_id,
        )

        # Если снова требуется OTP - код неверный (возможно рассинхрон времени)
        if isinstance(result, TwoFactorRequired):
            logger.warning(
                f"Auto-2FA failed for user {tg_user_id} - code rejected, "
                "possibly time desync"
            )
            return None

        # Успешно!
        logger.info(f"Auto-2FA successful for user {tg_user_id}")
        return {"cookies": result[0]}

    except Exception as e:
        logger.error(f"Error during auto-2FA for user {tg_user_id}: {e}", exc_info=True)
        return None


async def send_2fa_notification(
    db: DBModel, tg_user_id: int, source: str = "refresh"
) -> bool:
    """
    Отправляет уведомление в Telegram о необходимости ввода TOTP кода.
    Уведомление отправляется максимум 1 раз в 24 часа для предотвращения спама.

    Args:
        db: Экземпляр базы данных
        tg_user_id: Telegram ID пользователя
        source: Источник запроса ('login' или 'refresh')

    Returns:
        True если уведомление было отправлено, False если пропущено из-за rate limit
    """
    try:
        # Проверяем, можно ли отправить уведомление (не чаще 1 раза в 24 часа)
        can_send = await db.can_send_2fa_notification(tg_user_id)
        if not can_send:
            logger.info(
                f"Skipping 2FA notification for user {tg_user_id} - "
                "already sent within 24 hours"
            )
            return False

        message = (
            "🔐 <b>Требуется двухфакторная аутентификация</b>\n\n"
            "Для продолжения работы сервиса отметок необходимо ввести TOTP код "
            "из приложения-аутентификатора для mirea.ru.\n\n"
            "📱 Откройте Mini App и введите 6-значный код.\n\n"
            "⚠️ Без ввода кода автоматическая отметка посещаемости не будет работать."
        )

        await send_telegram_message(tg_user_id, message)

        # Помечаем, что уведомление отправлено
        await db.mark_2fa_notification_sent(tg_user_id)

        logger.info(f"Sent 2FA notification to user {tg_user_id}")
        return True
    except Exception as e:
        logger.error(f"Failed to send 2FA notification to {tg_user_id}: {e}")
        return False


@dataclass
class TwoFactorRequiredError(Exception):
    """Исключение, когда требуется двухфакторная аутентификация."""

    tg_user_id: int
    source: str = "login"
    message: str = "Требуется ввод TOTP кода"


async def _handle_2fa_result(
    db: DBModel,
    tg_user_id: int,
    result: TwoFactorRequired,
    user_agent: str,
    source: str = "login",
) -> None:
    """
    Сохраняет данные 2FA сессии в БД.

    Args:
        db: Экземпляр базы данных
        tg_user_id: Telegram ID пользователя
        result: Результат TwoFactorRequired
        user_agent: User agent для запросов
        source: Источник запроса ('login' или 'refresh')
    """
    await db.create_totp_session(
        tg_userid=tg_user_id,
        session_cookies=json.dumps(result.session_cookies),
        otp_action_url=result.otp_action_url,
        credential_id=result.credential_id,
        user_agent=user_agent,
        source=source,
        otp_credentials=json.dumps(result.otp_credentials) if result.otp_credentials else None,
    )


async def complete_2fa_login(
    db: DBModel,
    tg_user_id: int,
    otp_code: str,
) -> Union[List[str], TwoFactorRequired]:
    """
    Завершает 2FA авторизацию, отправляя OTP код.

    Args:
        db: Экземпляр базы данных
        tg_user_id: Telegram ID пользователя
        otp_code: 6-значный TOTP код

    Returns:
        Список групп пользователя при успехе
        TwoFactorRequired если код неверный

    Raises:
        Exception: Если сессия 2FA не найдена или истекла
    """
    # Получаем сохраненную сессию 2FA
    totp_session = await db.get_totp_session(tg_user_id)
    if not totp_session:
        raise Exception(
            "Сессия 2FA не найдена или истекла. Начните авторизацию заново."
        )

    session_cookies = json.loads(totp_session["session_cookies"])
    user_agent = totp_session.get("user_agent")
    source = totp_session.get("source", "login")

    # Отправляем OTP код
    result = await submit_otp_code(
        otp_code=otp_code,
        otp_action_url=totp_session["otp_action_url"],
        credential_id=totp_session["credential_id"],
        session_cookies=session_cookies,
        user_agent=user_agent,
        tg_user_id=tg_user_id,
    )

    # Если снова требуется OTP (неверный код)
    if isinstance(result, TwoFactorRequired):
        # Обновляем сессию с новыми данными, но сохраняем выбранный пользователем credential_id
        # (Keycloak возвращает дефолтный credential, а не тот что выбрал пользователь)
        await db.update_totp_session(
            tg_userid=tg_user_id,
            session_cookies=json.dumps(result.session_cookies),
            otp_action_url=result.otp_action_url,
            credential_id=totp_session["credential_id"],  # Сохраняем выбор пользователя
        )
        return result

    # Успешная авторизация - сохраняем cookies
    cookies = result[0]
    await db.create_cookie(tg_user_id, json.dumps(cookies))

    # Сохраняем credential_id для авто-TOTP (если у пользователя есть totp_secret)
    if await db.has_totp_secret(tg_user_id):
        await db.set_totp_credential_id(tg_user_id, totp_session["credential_id"])
        logger.info(f"Saved credential_id for auto-TOTP: {totp_session['credential_id']}")

    # Удаляем 2FA сессию
    await db.delete_totp_session(tg_user_id)

    # Если это был login, получаем группы
    if source == "login":
        try:
            groups = await get_groups.get_group(
                cookies, tg_user_id, db, user_agent=user_agent
            )
            return groups[0]
        except Exception as e:
            logger.error(f"Error getting groups after 2FA for {tg_user_id}: {e}")
            return []

    return []


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
        TwoFactorRequiredError: Если требуется ввод TOTP кода
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

            # Проверяем, не требуется ли 2FA
            if isinstance(cookies_result, TwoFactorRequired):
                logger.info(f"2FA required for user {tgID} during get_us_info")

                # Пробуем автоматическую 2FA
                auto_result = await try_auto_2fa(db, tgID, cookies_result, user_agent)
                if auto_result:
                    await db.create_cookie(tgID, json.dumps(auto_result["cookies"]))
                    # Пробуем снова с новыми куки
                    info = await get_me_info.get_me_info_data(
                        auto_result["cookies"], tgID, db, user_agent=user_agent
                    )
                    if info[0].strip():
                        return info[0]

                # Автоматическая 2FA не удалась - сохраняем сессию
                await _handle_2fa_result(
                    db, tgID, cookies_result, user_agent, source="refresh"
                )
                if notify_on_2fa:
                    await send_2fa_notification(db, tgID, source="refresh")
                raise TwoFactorRequiredError(tg_user_id=tgID, source="refresh")

            await db.create_cookie(tgID, json.dumps(cookies_result[0]))

            # Пробуем снова с новыми куки
            info = await get_me_info.get_me_info_data(
                cookies_result[0], tgID, db, user_agent=user_agent
            )
            if info[0].strip():
                return info[0]
            else:
                raise Exception("Неправильный логин или пароль")
        except TwoFactorRequiredError:
            raise
        except Exception as e:
            raise Exception(f"Ошибка обновления cookies: {str(e)}")

    except TwoFactorRequiredError:
        raise
    except Exception as e:
        raise Exception(f"Ошибка в get_us_info: {str(e)}")


async def self_approve(db, tgID, token, user_agent=None):
    """
    Подтверждает посещение, используя куки.
    Если куки отсутствуют или запрос возвращает 401, обновляет куки и повторяет попытку.
    Если требуется 2FA, сохраняет сессию и отправляет уведомление в Telegram.

    Raises:
        TwoFactorRequiredError: Если требуется ввод TOTP кода
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

        # Проверяем, не требуется ли 2FA
        if isinstance(cookies_result, TwoFactorRequired):
            logger.info(f"2FA required for user {tgID} during self_approve")

            # Пробуем автоматическую 2FA
            auto_result = await try_auto_2fa(db, tgID, cookies_result, user_agent)
            if auto_result:
                await db.create_cookie(tgID, json.dumps(auto_result["cookies"]))
                result = await self_approve_attendance.send_self_approve_attendance(
                    token,
                    auto_result["cookies"],
                    tgID,
                    db,
                    user_agent=user_agent,
                )
                return result[0]

            # Автоматическая 2FA не удалась
            await _handle_2fa_result(
                db, tgID, cookies_result, user_agent, source="refresh"
            )
            await send_2fa_notification(db, tgID, source="refresh")
            raise TwoFactorRequiredError(tg_user_id=tgID, source="refresh")

        await db.create_cookie(tgID, json.dumps(cookies_result[0]))
        result = await self_approve_attendance.send_self_approve_attendance(
            token,
            cookies_result[0],
            tgID,
            db,
            user_agent=user_agent,
        )
        return result[0]

    except TwoFactorRequiredError:
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

    Если требуется 2FA, сохраняет сессию в БД и выбрасывает TwoFactorRequiredError.

    Returns:
        Список групп пользователя

    Raises:
        TwoFactorRequiredError: Если требуется ввод TOTP кода
        Exception: При ошибке авторизации
    """
    try:
        # Пробуем получить куки по введённым данным
        result = await get_cookies.get_cookies(login, password, user_agent, tgID, db)

        # Проверяем, не требуется ли 2FA
        if isinstance(result, TwoFactorRequired):
            logger.info(f"2FA required for user {tgID} during login")

            # Пробуем автоматическую 2FA
            auto_result = await try_auto_2fa(db, tgID, result, user_agent)
            if auto_result:
                # Автоматическая 2FA успешна
                result = (auto_result["cookies"],)
            else:
                # Автоматическая 2FA не удалась - сохраняем данные и сессию
                await db.create_user_simple(
                    tg_userid=tgID,
                    login=login,
                    password=password,
                    user_agent=user_agent,
                )
                await _handle_2fa_result(db, tgID, result, user_agent, source="login")
                raise TwoFactorRequiredError(tg_user_id=tgID, source="login")

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
    except TwoFactorRequiredError:
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
        TwoFactorRequiredError: Если требуется ввод TOTP кода
        Exception: При ошибке проверки или неверных данных
    """
    try:
        # Пробуем получить куки по введённым данным
        result = await get_cookies.get_cookies(
            login, password, user_agent, tg_userid, db
        )

        # Проверяем, не требуется ли 2FA
        if isinstance(result, TwoFactorRequired):
            logger.info(
                f"2FA required for user {tg_userid} during check_login_and_pass"
            )

            # Пробуем автоматическую 2FA
            auto_result = await try_auto_2fa(db, tg_userid, result, user_agent)
            if auto_result:
                result = (auto_result["cookies"],)
            else:
                await _handle_2fa_result(db, tg_userid, result, user_agent, source="login")
                raise TwoFactorRequiredError(tg_user_id=tg_userid, source="login")

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
    except TwoFactorRequiredError:
        raise
    except Exception as e:
        raise Exception(f"Ошибка в check_login_and_pass: {str(e)}")


async def get_user_points(db, tgID, user_agent=None):
    """
    Получает баллы.

    Raises:
        TwoFactorRequiredError: Если требуется ввод TOTP кода
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

        # Проверяем, не требуется ли 2FA
        if isinstance(cookies_result, TwoFactorRequired):
            logger.info(f"2FA required for user {tgID} during get_user_points")

            # Пробуем автоматическую 2FA
            auto_result = await try_auto_2fa(db, tgID, cookies_result, user_agent)
            if auto_result:
                await db.create_cookie(tgID, json.dumps(auto_result["cookies"]))
                res_from_att = await get_points._get_points_data(
                    auto_result["cookies"],
                    db=db,
                    user_agent=user_agent,
                    tg_user_id=tgID,
                )
                return res_from_att[0]

            await _handle_2fa_result(
                db, tgID, cookies_result, user_agent, source="refresh"
            )
            # Не отправляем уведомление - пользователь в Mini App и может ввести код
            raise TwoFactorRequiredError(tg_user_id=tgID, source="refresh")

        await db.create_cookie(tgID, json.dumps(cookies_result[0]))
        res_from_att = await get_points._get_points_data(
            cookies_result[0],
            db=db,
            user_agent=user_agent,
            tg_user_id=tgID,
        )
        return res_from_att[0]

    except TwoFactorRequiredError:
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
        TwoFactorRequiredError: Если требуется ввод TOTP кода
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

        # Проверяем, не требуется ли 2FA
        if isinstance(cookies_result, TwoFactorRequired):
            logger.info(f"2FA required for user {user_id} during _get_user_schedule")

            # Пробуем автоматическую 2FA
            auto_result = await try_auto_2fa(db, user_id, cookies_result, user_agent)
            if auto_result:
                await db.create_cookie(user_id, json.dumps(auto_result["cookies"]))
                res_from_att = await get_schedule.get_user_schedule(
                    cookies=auto_result["cookies"],
                    db=db,
                    user_agent=user_agent,
                    tg_user_id=user_id,
                    b64_data=b64_data,
                )
                return res_from_att[0]

            await _handle_2fa_result(
                db, user_id, cookies_result, user_agent, source="refresh"
            )
            # Не отправляем уведомление - пользователь в Mini App и может ввести код
            raise TwoFactorRequiredError(tg_user_id=user_id, source="refresh")

        await db.create_cookie(user_id, json.dumps(cookies_result[0]))
        res_from_att = await get_schedule.get_user_schedule(
            cookies=cookies_result[0],
            db=db,
            user_agent=user_agent,
            tg_user_id=user_id,
            b64_data=b64_data,
        )
        return res_from_att[0]

    except TwoFactorRequiredError:
        raise
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


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
        TwoFactorRequiredError: Если требуется ввод TOTP кода
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

        # Проверяем, не требуется ли 2FA
        if isinstance(cookies_result, TwoFactorRequired):
            logger.info(
                f"2FA required for user {user_id} during get_lesson_attendance_info"
            )

            # Пробуем автоматическую 2FA
            auto_result = await try_auto_2fa(db, user_id, cookies_result, user_agent)
            if auto_result:
                await db.create_cookie(user_id, json.dumps(auto_result["cookies"]))
                res_from_att = await get_lesson_attendance.get_lesson_attendance_data(
                    cookies=auto_result["cookies"],
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

            await _handle_2fa_result(
                db, user_id, cookies_result, user_agent, source="refresh"
            )
            # Не отправляем уведомление - пользователь в Mini App и может ввести код
            raise TwoFactorRequiredError(tg_user_id=user_id, source="refresh")

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

    except TwoFactorRequiredError:
        raise
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Ошибка получения данных о посещаемости: {str(e)}"
        )
