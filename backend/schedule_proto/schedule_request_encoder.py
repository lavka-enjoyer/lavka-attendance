import base64

from backend.pb2 import schedulerequest_pb2 as request_pb2


def date_to_base64(year: int, month: int, day: int) -> str:
    """
    Преобразует дату в base64-строку для запроса расписания через gRPC-Web.

    Args:
        year: Год
        month: Месяц
        day: День

    Returns:
        Base64-encoded строка с protobuf сообщением в gRPC-Web формате
    """
    # Собираем protobuf-пейлоад
    request = request_pb2.Request()
    request.date.year = year
    request.date.month = month
    request.date.day = day

    payload = (
        request.SerializeToString()
    )  # b'\x12\x07\x08\xe9\x0f\x10\x0a\x18\x14' для 2025,10,20

    # gRPC(-Web) фрейм: 1 байт флагов + 4 байта длины (big-endian) + payload
    flags = bytes([0])  # 0 = без компрессии
    length = len(payload).to_bytes(4, byteorder="big")  # big-endian
    framed = flags + length + payload

    return base64.b64encode(framed).decode("utf-8")
