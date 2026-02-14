# Примеры использования API

Этот документ содержит примеры запросов к API MireApprove.

## Содержание

- [Аутентификация](#аутентификация)
- [Информация о пользователе](#информация-о-пользователе)
- [Расписание](#расписание)
- [Баллы БРС](#баллы-брс)
- [Отметка посещаемости](#отметка-посещаемости)
- [Администрирование](#администрирование)

---

## Аутентификация

### Telegram Mini App

Для запросов из Telegram Mini App используется параметр `initData`:

```bash
curl "http://localhost:8001/api/v1/user/info?initData=<telegram_init_data>"
```

### Внешняя авторизация (Bearer Token)

Для сторонних сервисов используется Bearer токен:

```bash
curl -H "Authorization: Bearer <your_token>" \
     http://localhost:8001/api/v1/user/info
```

#### Получение токена

1. Запросите создание токена:

```bash
curl -X POST http://localhost:8001/api/v1/external/create-token \
     -H "Content-Type: application/json" \
     -d '{"service_name": "my_service"}'
```

Ответ:
```json
{
  "token": "abc123...",
  "auth_url": "https://t.me/YourBot?start=auth_abc123...",
  "expires_at": null
}
```

2. Пользователь переходит по `auth_url` и подтверждает авторизацию в Telegram

3. Проверяйте статус токена:

```bash
curl http://localhost:8001/api/v1/external/token-status/abc123...
```

Ответ после подтверждения:
```json
{
  "status": "approved",
  "tg_userid": 123456789
}
```

---

## Информация о пользователе

### Получить информацию о текущем пользователе

```bash
curl -H "Authorization: Bearer <token>" \
     http://localhost:8001/api/v1/user/info
```

Ответ:
```json
{
  "tg_userid": 123456789,
  "group_name": "ИКБО-01-23",
  "login": "ivanov_ii",
  "allowConfirm": true,
  "admin_lvl": 0,
  "fio": "Иванов Иван Иванович"
}
```

### Проверить права пользователя

```bash
curl -H "Authorization: Bearer <token>" \
     http://localhost:8001/api/v1/user/permissions
```

Ответ:
```json
{
  "can_mark_self": true,
  "can_mark_others": false,
  "can_view_group": true,
  "admin_level": 0
}
```

---

## Расписание

### Получить расписание на неделю

```bash
curl -H "Authorization: Bearer <token>" \
     http://localhost:8001/api/v1/schedule/week
```

Ответ:
```json
{
  "week_number": 15,
  "days": [
    {
      "date": "2026-01-06",
      "day_name": "Понедельник",
      "lessons": [
        {
          "time": "09:00-10:30",
          "subject": "Математический анализ",
          "type": "Лекция",
          "room": "А-101",
          "teacher": "Петров П.П.",
          "can_mark": true
        }
      ]
    }
  ]
}
```

### Получить расписание на конкретную дату

```bash
curl -H "Authorization: Bearer <token>" \
     "http://localhost:8001/api/v1/schedule/day?date=2026-01-06"
```

---

## Баллы БРС

### Получить баллы по всем предметам

```bash
curl -H "Authorization: Bearer <token>" \
     http://localhost:8001/api/v1/points/all
```

Ответ:
```json
{
  "subjects": [
    {
      "name": "Математический анализ",
      "total_points": 75.5,
      "max_points": 100,
      "categories": [
        {
          "name": "Лабораторные работы",
          "points": 25.0,
          "max_points": 30
        },
        {
          "name": "Контрольные работы",
          "points": 50.5,
          "max_points": 70
        }
      ]
    }
  ]
}
```

---

## Отметка посещаемости

### Отметить себя на занятии

```bash
curl -X POST -H "Authorization: Bearer <token>" \
     -H "Content-Type: application/json" \
     -d '{"lesson_token": "<lesson_token>"}' \
     http://localhost:8001/api/v1/attendance/mark-self
```

Ответ:
```json
{
  "success": true,
  "message": "Посещение подтверждено"
}
```

### Получить информацию о посещаемости занятия

```bash
curl -H "Authorization: Bearer <token>" \
     "http://localhost:8001/api/v1/attendance/lesson?date=2026-01-06&time=09:00"
```

---

## Администрирование

> Требуется уровень администратора >= 1

### Получить статистику

```bash
curl -H "Authorization: Bearer <token>" \
     http://localhost:8001/api/v1/admin/stats
```

Ответ:
```json
{
  "total_users": 150,
  "total_groups": 12,
  "total_admins": 5,
  "users_with_login": 145,
  "users_with_proxy": 20
}
```

### Поиск пользователей

```bash
curl -H "Authorization: Bearer <token>" \
     "http://localhost:8001/api/v1/admin/search?query=иванов"
```

### Изменить уровень администратора

> Требуется уровень администратора >= 3

```bash
curl -X POST -H "Authorization: Bearer <token>" \
     -H "Content-Type: application/json" \
     -d '{"target_tg_userid": 987654321, "new_level": 1}' \
     http://localhost:8001/api/v1/admin/set-level
```

---

## NFC карты

### Получить список карт группы

```bash
curl -H "Authorization: Bearer <token>" \
     http://localhost:8001/api/v1/nfc/cards
```

### Добавить NFC карту

```bash
curl -X POST -H "Authorization: Bearer <token>" \
     -H "Content-Type: application/json" \
     -d '{
       "card_id": 12345678,
       "name": "Иванов Иван",
       "tg_userid": 123456789
     }' \
     http://localhost:8001/api/v1/nfc/cards
```

### Удалить NFC карту

```bash
curl -X DELETE -H "Authorization: Bearer <token>" \
     "http://localhost:8001/api/v1/nfc/cards/12345678"
```

---

## Коды ошибок

| Код | Описание |
|-----|----------|
| 400 | Неверные параметры запроса |
| 401 | Требуется авторизация |
| 403 | Недостаточно прав |
| 404 | Ресурс не найден |
| 429 | Превышен лимит запросов (100/мин) |
| 500 | Внутренняя ошибка сервера |

Пример ответа с ошибкой:
```json
{
  "detail": "Недостаточно прав для выполнения операции",
  "error_code": "HTTP_403"
}
```

---

## Swagger документация

Полная интерактивная документация API доступна по адресу:
- http://localhost:8001/docs (после запуска сервера)
