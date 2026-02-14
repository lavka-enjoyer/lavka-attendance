#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
MIREA Attendance API - Protobuf Schemas
========================================

Схемы (typedef) для декодирования gRPC-Web protobuf ответов от MIREA API
с использованием библиотеки blackboxprotobuf.

Этот файл можно использовать как основу для создания собственных проектов,
работающих с внешним API системы посещаемости MIREA.

Установка зависимостей:
    pip install blackboxprotobuf aiohttp

Базовый пример использования:
    import base64
    import blackboxprotobuf
    from protobuf_schemas import SCHEDULE_TYPEDEF, ME_INFO_TYPEDEF

    # Декодирование ответа
    raw_bytes = base64.b64decode(response_b64)
    protobuf_data = raw_bytes[5:]  # Пропускаем 5-байтовый gRPC заголовок
    message, _ = blackboxprotobuf.decode_message(protobuf_data, SCHEDULE_TYPEDEF)

API Endpoints:
    Base URL: https://attendance.mirea.ru/
    Content-Type: application/grpc-web+proto или application/grpc-web-text
    Headers: x-grpc-web: 1, x-requested-with: XMLHttpRequest

Авторизация:
    Используются cookies после OAuth авторизации через https://login.mirea.ru/
"""

from typing import Any, Dict

# =============================================================================
# gRPC-Web формат
# =============================================================================
#
# Все ответы от MIREA API имеют 5-байтовый заголовок:
#   [1 byte flags][4 bytes big-endian length][protobuf payload]
#
# Flags:
#   0x00 = data frame (содержит данные)
#   0x80 = trailer frame (пустой ответ, только grpc-status)
#
# Пример: 00 00 00 05 CC = flags=0, length=1484, затем 1484 байта protobuf
#
# =============================================================================


# =============================================================================
# GetMeInfo - Информация о текущем пользователе
# =============================================================================
# Endpoint: rtu_tc.rtu_attend.app.UserService/GetMeInfo
# Method: POST
# Request body: пустой (base64: AAAAAAA=)
#
# Возвращает: UUID, ФИО, email, claims пользователя
# =============================================================================

ME_INFO_TYPEDEF: Dict[str, Any] = {
    "1": {
        "type": "message",
        "message_typedef": {
            "1": {
                "type": "message",
                "message_typedef": {
                    "1": {"type": "string"},  # UUID пользователя
                    "2": {"type": "string"},  # Имя
                    "3": {"type": "string"},  # Фамилия
                    "4": {
                        "type": "message",
                        "message_typedef": {"1": {"type": "string"}}  # Отчество
                    },
                    "5": {"type": "message"},  # claims (repeated) - роли пользователя
                    "6": {"type": "string"},  # email
                    "7": {"type": "message"},  # preferences (JSON string)
                }
            },
            "2": {"type": "string"},  # logout URL
        }
    }
}


# =============================================================================
# GetAvailableDisciplines - Список дисциплин
# =============================================================================
# Endpoint: rtu_tc.attendance.api.DisciplineService/GetAvailableDisciplines
# Method: POST
# Request body: visiting_log_uuid
#
# Возвращает: список дисциплин с UUID и названиями
# =============================================================================

DISCIPLINES_TYPEDEF: Dict[str, Any] = {
    "1": {
        "type": "message",
        "seen_repeated": True,
        "message_typedef": {
            "1": {"type": "string"},  # UUID дисциплины
            "2": {"type": "string"},  # Название дисциплины
        }
    }
}


# =============================================================================
# GetHumanAcsEvents - События системы контроля доступа (турникеты)
# =============================================================================
# Endpoint: rtu_tc.rtu_attend.humanpass.HumanPassService/GetHumanAcsEvents
# Method: POST
# Request body: {user_uuid, time_range{from, to}, page, page_size}
#
# Возвращает: список проходов через турникеты с временем и точками доступа
# =============================================================================

ACS_EVENTS_TYPEDEF: Dict[str, Any] = {
    "1": {
        "type": "message",
        "seen_repeated": True,
        "message_typedef": {
            "1": {"type": "string"},  # event UUID
            "2": {
                "type": "message",
                "message_typedef": {"1": {"type": "int"}}  # Unix timestamp
            },
            "3": {  # access_point_from - откуда
                "type": "message",
                "message_typedef": {
                    "1": {"type": "string"},  # access_point UUID
                    "2": {"type": "string"},  # access_point name
                }
            },
            "4": {  # access_point_to - куда
                "type": "message",
                "message_typedef": {
                    "1": {"type": "string"},
                    "2": {"type": "string"},
                }
            },
        }
    }
}


# =============================================================================
# GetAvailableVisitingLogsOfStudent - Семестры и журналы посещаемости
# =============================================================================
# Endpoint: rtu_tc.attendance.api.VisitingLogService/GetAvailableVisitingLogsOfStudent
# Method: POST
# Request body: пустой
#
# Возвращает: список логов посещаемости (группа + семестр)
# =============================================================================

VISITING_LOGS_TYPEDEF: Dict[str, Any] = {
    "1": {
        "type": "message",
        "seen_repeated": True,
        "message_typedef": {
            "1": {
                "type": "message",
                "message_typedef": {
                    "1": {"type": "string"},  # log UUID
                    "2": {"type": "string"},  # group name (ИКБО-01-23)
                    "4": {"type": "string"},  # semester UUID
                    "6": {
                        "type": "message",
                        "message_typedef": {
                            "1": {"type": "string"},  # semester UUID
                            "2": {"type": "string"},  # semester name (Осень 25-26)
                            "3": {"type": "message", "message_typedef": {"1": {"type": "int"}}},  # start date
                            "4": {"type": "message", "message_typedef": {"1": {"type": "int"}}},  # end date
                        }
                    }
                }
            },
            "2": {"type": "int"},
            "3": {"type": "int"},
            "4": {"type": "string"},  # human UUID
        }
    },
    "2": {
        "type": "message",
        "seen_repeated": True,
    }
}


# =============================================================================
# GetLearnRatingScoreReportForStudentInVisitingLogV2 - Баллы БРС
# =============================================================================
# Endpoint: rtu_tc.attendance.api.LearnRatingScoreService/GetLearnRatingScoreReportForStudentInVisitingLogV2
# Method: POST
# Request body: {visiting_log_uuid}
#
# Возвращает: баллы по дисциплинам (текущий контроль, посещения, достижения и т.д.)
#
# ВАЖНО: Баллы хранятся как fixed64, нужно конвертировать в double:
#   import struct
#   double_value = struct.unpack('<d', struct.pack('<Q', fixed64_value))[0]
# =============================================================================

BRS_TYPEDEF: Dict[str, Any] = {
    "1": {
        "type": "message",
        "message_typedef": {
            "1": {  # Дисциплины (repeated)
                "type": "message",
                "seen_repeated": True,
                "message_typedef": {
                    "1": {  # Информация о дисциплине
                        "type": "message",
                        "message_typedef": {
                            "1": {"type": "string"},  # Название
                            "2": {"type": "string"},  # UUID
                        }
                    },
                    "2": {  # Баллы по категориям (repeated)
                        "type": "message",
                        "seen_repeated": True,
                        "message_typedef": {
                            "1": {"type": "string"},  # UUID категории
                            "2": {"type": "fixed64"},  # Балл (double как fixed64!)
                        }
                    },
                    "3": {"type": "fixed64"},  # Общий балл (double как fixed64!)
                }
            },
            "2": {  # Определения категорий (repeated)
                "type": "message",
                "seen_repeated": True,
                "message_typedef": {
                    "1": {"type": "int"},  # Тип категории
                    "2": {  # Колонки (repeated)
                        "type": "message",
                        "seen_repeated": True,
                        "message_typedef": {
                            "1": {"type": "string"},  # UUID
                            "2": {"type": "string"},  # Название (Текущий контроль, Посещения, ...)
                            "3": {"type": "string"},  # Описание
                            "4": {"type": "int"},     # Максимальный балл
                        }
                    }
                }
            },
            "3": {"type": "int"},  # Общий максимум (обычно 100)
        }
    }
}


# =============================================================================
# GetAttendanceVisitingLogReportForDiscipline - Отчёт посещаемости по дисциплине
# =============================================================================
# Endpoint: rtu_tc.attendance.api.VisitingLogService/GetAttendanceVisitingLogReportForDiscipline
# Method: POST
# Request body: {visiting_log_uuid, discipline_uuid}
#
# Возвращает: занятия с отметками посещаемости для всех студентов группы
#
# Статусы посещаемости:
#   1 = "Н" (не был / отсутствовал)
#   2 = "У" (уважительная причина)
#   3 = "+" (присутствовал)
# =============================================================================

ATTENDANCE_REPORT_TYPEDEF: Dict[str, Any] = {
    "1": {  # Занятия (repeated)
        "type": "message",
        "seen_repeated": True,
        "message_typedef": {
            "1": {  # Информация о занятии
                "type": "message",
                "message_typedef": {
                    "1": {  # Время занятия
                        "type": "message",
                        "message_typedef": {
                            "1": {"type": "message", "message_typedef": {"1": {"type": "int"}}},  # start timestamp
                            "2": {"type": "message", "message_typedef": {"1": {"type": "int"}}},  # end timestamp
                        }
                    },
                    "2": {"type": "string"},  # Тип занятия (ЛК, ПР, ЗАЧ, КП, Э, Конс)
                    "3": {"type": "string"},  # UUID занятия
                }
            },
            "2": {  # Записи посещаемости (repeated)
                "type": "message",
                "seen_repeated": True,
                "message_typedef": {
                    "1": {"type": "string"},  # student UUID
                    "3": {  # Статус посещаемости (если есть)
                        "type": "message",
                        "message_typedef": {
                            "1": {"type": "string"},  # attendance record ID
                            "2": {"type": "int"},     # status: 1=Н, 2=У, 3=+
                        }
                    },
                    "4": {"type": "message"},  # empty = not marked yet
                }
            }
        }
    },
    "2": {  # Студенты (repeated)
        "type": "message",
        "seen_repeated": True,
        "message_typedef": {
            "1": {"type": "string"},  # UUID
            "2": {"type": "string"},  # Имя
            "3": {"type": "string"},  # Фамилия
            "4": {"type": "message", "message_typedef": {"1": {"type": "string"}}},  # Отчество
            "5": {"type": "int"},
            "6": {"type": "int"},
            "7": {"type": "string"},  # student ID (24Б1037)
            "8": {"type": "string"},  # some UUID
        }
    },
    "3": {  # Информация о логе
        "type": "message",
        "message_typedef": {
            "1": {"type": "string"},  # log UUID
            "2": {"type": "string"},  # group name
            "6": {
                "type": "message",
                "message_typedef": {
                    "2": {"type": "string"},  # semester name
                }
            }
        }
    }
}


# =============================================================================
# GetScheduleForStudent - Расписание студента
# =============================================================================
# Endpoint: rtu_tc.attendance.api.ScheduleService/GetScheduleForStudent
# Method: POST
# Request body: {time_range{from, to}}
#
# Возвращает: расписание занятий с информацией о посещаемости
#
# Логика определения статуса посещения:
#   1. Проверить field 8.1.1 - timestamp подтверждения
#      - Если < 1000000000 (или -62135596800) → занятие не подтверждено, статус пустой
#   2. Если подтверждено, смотреть wrapper["2"]:
#      - 1 → "Н" (не был)
#      - 3 → "+" (был)
# =============================================================================

SCHEDULE_TYPEDEF: Dict[str, Any] = {
    "2": {  # Wrapper (repeated)
        "type": "message",
        "message_typedef": {
            "2": {"type": "int"},  # СТАТУС: 1=Н (не был), 3=+ (был)
            "3": {  # Lesson
                "type": "message",
                "message_typedef": {
                    "1": {"type": "string"},  # UUID занятия
                    "2": {  # Время начала
                        "type": "message",
                        "message_typedef": {"1": {"type": "int"}},  # Unix timestamp
                    },
                    "3": {  # Время конца
                        "type": "message",
                        "message_typedef": {"1": {"type": "int"}},
                    },
                    "4": {  # Предмет
                        "type": "message",
                        "message_typedef": {
                            "1": {"type": "bytes"},   # UUID дисциплины
                            "2": {"type": "string"},  # Название
                        },
                    },
                    "5": {  # Тип занятия
                        "type": "message",
                        "message_typedef": {
                            "1": {"type": "bytes"},
                            "2": {"type": "string"},  # ЛК, ПР, ЗАЧ, КП, Э, Конс
                        },
                    },
                    "6": {  # Аудитория
                        "type": "message",
                        "message_typedef": {
                            "1": {"type": "string"},  # UUID аудитории
                            "2": {"type": "string"},  # Номер (326, 145б, Дистанционно)
                            "3": {"type": "string"},  # Здание (С-20, В-78, СДО)
                        },
                    },
                    "7": {  # Преподаватель
                        "type": "message",
                        "message_typedef": {
                            "1": {"type": "string"},  # UUID
                            "2": {"type": "string"},  # Имя
                            "3": {"type": "string"},  # Фамилия
                            "4": {  # Отчество
                                "type": "message",
                                "message_typedef": {"1": {"type": "string"}},
                            },
                        },
                    },
                    "8": {  # Подтверждение посещения
                        "type": "message",
                        "message_typedef": {
                            "1": {
                                "type": "message",
                                "message_typedef": {"1": {"type": "int"}}  # timestamp
                                # -62135596800 = не подтверждено (default protobuf value)
                            }
                        },
                    },
                    "9": {"type": "int"},  # Дополнительный статус
                },
            },
        },
    }
}


# =============================================================================
# SelfApproveAttendance - Самоподтверждение посещения
# =============================================================================
# Endpoint: rtu_tc.attendance.api.StudentService/SelfApproveAttendance
# Method: POST
# Request body: {lesson_uuid}
#
# Формат запроса:
#   protobuf = bytes([0x0A, len(uuid)]) + uuid.encode()
#   grpc_body = b"\x00\x00\x00\x00" + bytes([len(protobuf)]) + protobuf
#   request = base64.b64encode(grpc_body)
#
# Возвращает: пустой ответ при успехе или сообщение об ошибке
# =============================================================================


# =============================================================================
# Экспорт всех схем
# =============================================================================

__all__ = [
    "ME_INFO_TYPEDEF",
    "DISCIPLINES_TYPEDEF",
    "ACS_EVENTS_TYPEDEF",
    "VISITING_LOGS_TYPEDEF",
    "BRS_TYPEDEF",
    "ATTENDANCE_REPORT_TYPEDEF",
    "SCHEDULE_TYPEDEF",
]
