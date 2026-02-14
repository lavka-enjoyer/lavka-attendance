from backend.attendance import get_us_info
from backend.database import DBModel


async def _get_group_users(db: DBModel, tg_userid):
    """Получает всех пользователей из той же группы, что и указанный пользователь."""
    # Получаем группу пользователя
    user = await db.get_user(tg_userid)
    if not user or not user.get("group_name"):
        raise Exception("Пользователь или группа не найдены")

    group_name = user["group_name"]

    # Получаем всех пользователей в той же группе
    rows = await db.get_users_from_group(group_name)
    return rows


async def _get_user_info_safe(db: DBModel, tg_userid, allow_confirm):
    """Безопасно получает информацию о пользователе, возвращая None при ошибке."""
    try:
        # Сначала проверяем, есть ли уже ФИО в БД
        existing_fio = await db.get_fio(tg_userid)
        if existing_fio:
            return {
                "tg_id": tg_userid,
                "fio": existing_fio,
                "allowConfirm": allow_confirm,
            }

        # Получаем информацию о пользователе из системы
        user_agent = await db.get_user_agent(tg_userid)
        info = await get_us_info(db, tg_userid, user_agent)

        # Сохраняем ФИО в БД для последующего использования
        if info and isinstance(info, str) and len(info) > 0:
            await db.update_fio(tg_userid, info)

        # Возвращаем информацию о пользователе
        return {
            "tg_id": tg_userid,
            "fio": info,  # Предполагается, что info содержит имя пользователя
            "allowConfirm": allow_confirm,
        }
    except Exception as e:
        return str(e)


async def _get_other_group_users(db: DBModel, group_name):
    """Получает всех пользователей из указанной группы."""
    return await db.get_other_group_users(group_name=group_name)


async def _get_unique_group(db: DBModel):
    """
    Получает список всех уникальных групп из базы данных.

    Args:
        db: Экземпляр модели базы данных

    Returns:
        Список уникальных групп

    Raises:
        Exception: При ошибке получения данных из БД
    """
    try:
        rows = await db.get_unique_group_db()
        return rows
    except Exception as exc:
        raise Exception from exc
