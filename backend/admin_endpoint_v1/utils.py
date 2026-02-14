from datetime import datetime

from dateutil.relativedelta import relativedelta


async def get_timestamp_future(months_to_add: int) -> datetime:
    """
    Вычисляет будущую дату, добавляя указанное количество месяцев к текущей дате.

    Args:
        months_to_add: Количество месяцев для добавления

    Returns:
        Дата в будущем
    """
    today = datetime.now()
    future = today + relativedelta(months=months_to_add)
    future_date = future.strftime("%Y-%m-%d %H:%M:%S")
    return datetime.strptime(future_date, "%Y-%m-%d %H:%M:%S")
