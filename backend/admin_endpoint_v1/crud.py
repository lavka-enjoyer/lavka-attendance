import logging
from typing import Any, Dict, List, Optional, Union

from backend.attendance import (
    TwoFactorRequiredError,
    add_data_for_login,
    check_login_and_pass,
    complete_2fa_login,
)
from backend.database import DBModel
from backend.mirea_api.get_cookies import TwoFactorRequired

logger = logging.getLogger(__name__)


async def _update_user(
    db: DBModel, tg_user_id: int, data: Any
) -> Union[str, Any, dict]:
    """
    Обновляет данные пользователя в базе данных.

    Args:
        db: Экземпляр модели базы данных
        tg_user_id: ID пользователя в Telegram
        data: Данные для обновления (схема UpdateUser)

    Returns:
        Результат обновления, строку с ошибкой, или dict с requires_2fa=True
    """
    try:
        dict_for_update = {
            k: v
            for k, v in data.model_dump(exclude_none=True).items()
            if k != "initData"
        }
        res = None
        if "login" in dict_for_update and "password" in dict_for_update:
            # Используем user_agent из запроса (если передан), иначе из БД
            user_agent_data = dict_for_update.get("user_agent") or await db.get_user_agent(tg_user_id)
            res = await check_login_and_pass(
                db,
                tg_user_id,
                dict_for_update["login"],
                dict_for_update["password"],
                user_agent=user_agent_data,
            )
        if res is not None:
            dict_for_update["group_name"] = res[-1]
        elif "login" in dict_for_update or "password" in dict_for_update:
            return "Логин без пароля не живет и на оборот"
        return await db.update_user(tg_user_id, **dict_for_update)
    except TwoFactorRequiredError:
        logger.info(f"2FA required for user {tg_user_id} during update")
        # Сохраняем логин и пароль в БД до возврата 2FA
        # (credentials валидны, т.к. Keycloak принял их и запросил OTP)
        save_fields = {}
        if "login" in dict_for_update:
            save_fields["login"] = dict_for_update["login"]
        if "password" in dict_for_update:
            save_fields["password"] = dict_for_update["password"]
        if "user_agent" in dict_for_update:
            save_fields["user_agent"] = dict_for_update["user_agent"]
        if save_fields:
            try:
                await db.update_user(tg_user_id, **save_fields)
                logger.info(f"Saved credentials for user {tg_user_id} before 2FA")
            except Exception as save_err:
                logger.error(f"Failed to save credentials for {tg_user_id}: {save_err}")
        return {"requires_2fa": True, "message": "Требуется ввод TOTP кода"}
    except Exception as e:
        logger.error(f"Error updating user {tg_user_id}: {e}", exc_info=True)
        return str(e)


async def _create_user_part_1_new(
    db: DBModel,
    tg_user_id: int,
    login: Optional[str] = None,
    password: Optional[str] = None,
    user_agent: Optional[str] = None,
) -> Union[str, Dict[str, str]]:
    """
    Создает нового пользователя с возможностью указания логина и пароля.

    Args:
        db: Экземпляр модели базы данных
        tg_user_id: ID пользователя в Telegram
        login: Логин от ЛКС (необязательный)
        password: Пароль от ЛКС (необязательный)
        user_agent: User-Agent браузера (необязательный)

    Returns:
        Результат создания пользователя, словарь с ошибкой, или dict с requires_2fa=True
    """
    try:
        res1 = await db.get_user_by_id(tg_user_id)
        if res1:
            return {"result": "user already exists"}

        logger.info(
            f"Пользователь {tg_user_id} зарегистрировался. Логин и пароль: {all([login, password])}"
        )

        if not login or not password:
            res = await db.create_user_simple(
                tg_userid=tg_user_id, user_agent=user_agent
            )
        else:
            res = await add_data_for_login(
                db,
                tgID=tg_user_id,
                login=login,
                password=password,
                user_agent=user_agent,
            )
        return res

    except TwoFactorRequiredError:
        logger.info(f"2FA required for new user {tg_user_id}")
        return {"requires_2fa": True, "message": "Требуется ввод TOTP кода"}
    except Exception as e:
        logger.error(f"Error creating user {tg_user_id}: {e}", exc_info=True)
        return {"Exception": str(e)}


async def _submit_otp_code(
    db: DBModel, tg_user_id: int, otp_code: str
) -> Dict[str, Any]:
    """
    Отправляет OTP код для завершения 2FA.

    Args:
        db: Экземпляр модели базы данных
        tg_user_id: ID пользователя в Telegram
        otp_code: 6-значный TOTP код

    Returns:
        Словарь с результатом: success=True и groups при успехе,
        или requires_2fa=True если код неверный
    """
    try:
        result = await complete_2fa_login(db, tg_user_id, otp_code)

        if isinstance(result, TwoFactorRequired):
            return {
                "success": False,
                "requires_2fa": True,
                "message": result.message or "Неверный код. Попробуйте снова.",
                "otp_credentials": result.otp_credentials or [],
            }

        # Успешная авторизация - обновляем группу в БД
        if result and len(result) > 0:
            await db.update_user(tg_user_id, group_name=result[-1])

        return {"success": True, "groups": result}

    except Exception as e:
        logger.error(f"Error submitting OTP for user {tg_user_id}: {e}", exc_info=True)
        return {"success": False, "error": str(e)}


async def _check_totp_session(db: DBModel, tg_user_id: int) -> Dict[str, Any]:
    """
    Проверяет наличие активной 2FA сессии для пользователя.

    Args:
        db: Экземпляр модели базы данных
        tg_user_id: ID пользователя в Telegram

    Returns:
        Словарь с has_session=True если есть активная сессия
    """
    session = await db.get_totp_session(tg_user_id)
    if session:
        otp_credentials = []
        if session.get("otp_credentials"):
            import json
            try:
                otp_credentials = json.loads(session["otp_credentials"])
            except (json.JSONDecodeError, TypeError):
                pass
        return {
            "has_session": True,
            "source": session.get("source"),
            "otp_credentials": otp_credentials,
        }
    return {
        "has_session": False,
        "source": None,
        "otp_credentials": [],
    }


async def _get_count(db: DBModel) -> Union[int, Dict[str, Exception]]:
    """
    Получает общее количество пользователей в системе.

    Args:
        db: Экземпляр модели базы данных

    Returns:
        Количество пользователей или словарь с ошибкой
    """
    try:
        return await db.get_count_us()
    except Exception as e:
        logger.error(f"Error getting user count: {e}", exc_info=True)
        return {"EXC": e}


async def _get_all(
    db: DBModel, tg_user_id: int, offset: int, group_name: Optional[str] = None
) -> List[Dict[str, Any]]:
    """
    Получает список всех пользователей с пагинацией и фильтрацией по группе.

    Args:
        db: Экземпляр модели базы данных
        tg_user_id: ID пользователя, выполняющего запрос
        offset: Смещение для пагинации
        group_name: Название группы для фильтрации (необязательный)

    Returns:
        Список словарей с информацией о пользователях
    """
    try:
        res1 = await db.getter_us(tg_user_id, offset, group_name)
        res = [dict(row) for row in res1]
        return res

    except Exception as e:
        logger.error(f"Error getting all users for {tg_user_id}: {e}", exc_info=True)
        raise e


async def _get_all_admin(db: DBModel, tg_user_id: int) -> List[Dict[str, Any]]:
    """
    Получает список всех администраторов системы.

    Args:
        db: Экземпляр модели базы данных
        tg_user_id: ID пользователя, выполняющего запрос

    Returns:
        Список словарей с информацией об администраторах
    """
    try:
        res1 = await db.get_admin(tg_user_id)
        res = [dict(row) for row in res1]
        return res

    except Exception as e:
        logger.error(f"Error getting all admins for {tg_user_id}: {e}", exc_info=True)
        raise e
