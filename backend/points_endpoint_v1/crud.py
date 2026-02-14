from backend.attendance import get_user_points
from backend.database import DBModel


async def _getter_pr(db: DBModel, tg_userid: int):
    """
    Получает баллы пользователя с использованием его user agent.

    Args:
        db: Экземпляр модели базы данных
        tg_userid: Telegram ID пользователя

    Returns:
        Результат запроса баллов пользователя

    Raises:
        Exception: При ошибке получения данных
    """
    try:
        user_agent = await db.get_user_agent(tg_userid)

        res = await get_user_points(db, tg_userid, user_agent)

        return res

    except Exception as e:
        raise e
