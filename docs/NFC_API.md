# NFC Cards API

API для управления NFC картами (пропусками) пользователей.

## Обзор

Этот API позволяет:
- Добавлять NFC карты (свои или других людей)
- Получать список карт группы с актуальным статусом присутствия в университете
- Удалять карты
- Получать список пользователей группы для привязки карт
- Получать cookies MIREA другого пользователя из группы

## Авторизация

Все эндпоинты требуют авторизации. Поддерживаются два способа:

### 1. Telegram Mini App (initData)
```
GET /api/nfc/cards?initData=<telegram_init_data>
```

### 2. External Auth Token (Bearer)
```
GET /api/nfc/cards
Authorization: Bearer <external_auth_token>
```

---

## Эндпоинты

### POST /api/nfc/cards

Добавить NFC карту.

#### Request Body

```json
{
  "card_id": 3279733,
  "tg_userid": 123456789,
  "name": "Иван Иванов"
}
```

| Поле | Тип | Обязательно | Описание |
|------|-----|-------------|----------|
| `card_id` | int | Да | ID NFC карты (номер пропуска) |
| `tg_userid` | int | Нет | Telegram ID пользователя бота (если карта привязана к юзеру) |
| `name` | string | Условно | Имя владельца. **Обязательно**, если `tg_userid` не указан. Если `tg_userid` указан - берётся ФИО из БД |

#### Логика работы

1. Если указан `tg_userid`:
   - Проверяется, существует ли пользователь в БД
   - Проверяется, что пользователь из той же группы
   - Если `name` не указан - берётся `fio` из БД (или `login`, если `fio` нет)

2. Если `tg_userid` не указан:
   - Поле `name` обязательно
   - Карта сохраняется без привязки к пользователю бота

3. Карта автоматически привязывается к группе пользователя, который её добавляет

#### Response

```json
{
  "status": "success",
  "message": "NFC card added successfully",
  "card": {
    "id": 1,
    "card_id": 3279733,
    "tg_userid": 123456789,
    "name": "Иванов Иван Иванович",
    "owner_group": "ИКБО-01-23",
    "added_by": 987654321,
    "created_at": "2024-01-15T10:30:00+00:00",
    "is_in_university": null,
    "last_event_time": null
  }
}
```

#### Errors

| Код | Описание |
|-----|----------|
| 400 | `Name is required when tg_userid is not provided` - имя обязательно без tg_userid |
| 400 | `User has no group assigned` - у пользователя нет группы |
| 400 | `Linked user is from different group` - привязываемый юзер из другой группы |
| 404 | `User not found` - пользователь не найден |
| 404 | `Linked user not found` - привязываемый юзер не найден |

---

### GET /api/nfc/cards

Получить все NFC карты группы.

#### Response

```json
{
  "status": "success",
  "cards": [
    {
      "id": 1,
      "card_id": 3279733,
      "tg_userid": 123456789,
      "name": "Иванов Иван Иванович",
      "owner_group": "ИКБО-01-23",
      "added_by": 987654321,
      "created_at": "2024-01-15T10:30:00+00:00",
      "is_in_university": true,
      "last_event_time": "09:45:12"
    },
    {
      "id": 2,
      "card_id": 4567890,
      "tg_userid": null,
      "name": "Петров Пётр",
      "owner_group": "ИКБО-01-23",
      "added_by": 987654321,
      "created_at": "2024-01-15T11:00:00+00:00",
      "is_in_university": null,
      "last_event_time": null
    }
  ]
}
```

#### Поля ответа

| Поле | Тип | Описание |
|------|-----|----------|
| `id` | int | ID записи в БД |
| `card_id` | int | ID NFC карты |
| `tg_userid` | int/null | Telegram ID привязанного пользователя |
| `name` | string | Имя владельца (актуальное ФИО из БД если есть tg_userid) |
| `owner_group` | string | Группа |
| `added_by` | int | Кто добавил карту |
| `created_at` | datetime | Дата добавления |
| `is_in_university` | bool/null | Находится ли в универе (только если есть tg_userid) |
| `last_event_time` | string/null | Время последнего прохода (HH:MM:SS) |

#### Логика статуса `is_in_university`

- `true` - пользователь в университете (последний проход - вход)
- `false` - пользователь вышел из университета
- `null` - статус неизвестен (нет tg_userid, ошибка запроса, или нет данных за сегодня)

**Важно**: Для карт с `tg_userid` делается запрос к API MIREA для получения событий ACS за сегодня. Это может занять время.

---

### DELETE /api/nfc/cards/{card_id}

Удалить NFC карту.

#### Path Parameters

| Параметр | Тип | Описание |
|----------|-----|----------|
| `card_id` | int | ID NFC карты для удаления |

#### Response

```json
{
  "status": "success",
  "message": "NFC card deleted successfully"
}
```

#### Errors

| Код | Описание |
|-----|----------|
| 404 | `NFC card not found in your group` - карта не найдена в группе пользователя |

---

### GET /api/nfc/group-users

Получить список пользователей группы для выбора при добавлении карты.

Используется в UI для отображения списка "Выберите пользователя из бота".

#### Response

```json
{
  "status": "success",
  "users": [
    {
      "tg_userid": 123456789,
      "name": "Иванов Иван Иванович"
    },
    {
      "tg_userid": 987654321,
      "name": "Петров Пётр Петрович"
    }
  ]
}
```

#### Поля ответа

| Поле | Тип | Описание |
|------|-----|----------|
| `tg_userid` | int | Telegram ID пользователя |
| `name` | string | ФИО (или login, если ФИО нет) |

---

### GET /api/nfc/mirea-cookies

Получить cookies MIREA для пользователя из своей группы.

Используется в NFC приложении для получения авторизационных данных другого пользователя, чтобы использовать его пропуск.

#### Query Parameters

| Параметр | Тип | Обязательно | Описание |
|----------|-----|-------------|----------|
| `target_tg_userid` | int | Да | Telegram ID пользователя, чьи cookies нужны |

#### Response

```json
{
  "status": "success",
  "tg_userid": 123456789,
  "name": "Иванов Иван Иванович",
  "cookies": {
    ".AspNetCore.Cookies": "CfDJ8...",
    "другие_cookies": "значение"
  },
  "message": "MIREA cookies obtained successfully"
}
```

#### Поля ответа

| Поле | Тип | Описание |
|------|-----|----------|
| `tg_userid` | int | Telegram ID пользователя |
| `name` | string | ФИО пользователя |
| `cookies` | object | Словарь cookies для авторизации в MIREA |

#### Errors

| Код | Описание |
|-----|----------|
| 400 | `Target user has no credentials configured` - у пользователя не настроен логин/пароль |
| 403 | `Target user is from different group` - пользователь из другой группы |
| 401 | `Invalid MIREA credentials for target user` - неверные данные авторизации |
| 404 | `Target user not found` - пользователь не найден |
| 503 | `Proxy service unavailable` - проблема с прокси |

#### Пример

```bash
curl "https://api.example.com/api/nfc/mirea-cookies?target_tg_userid=123456789" \
  -H "Authorization: Bearer <token>"
```

---

## Примеры использования

### Добавление своей карты (пользователь есть в боте)

```bash
curl -X POST "https://api.example.com/api/nfc/cards" \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{
    "card_id": 3279733,
    "tg_userid": 123456789
  }'
```

### Добавление карты друга (нет в боте)

```bash
curl -X POST "https://api.example.com/api/nfc/cards" \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{
    "card_id": 4567890,
    "name": "Сидоров Сидор"
  }'
```

### Получение списка карт

```bash
curl "https://api.example.com/api/nfc/cards" \
  -H "Authorization: Bearer <token>"
```

### Удаление карты

```bash
curl -X DELETE "https://api.example.com/api/nfc/cards/3279733" \
  -H "Authorization: Bearer <token>"
```

### Получение cookies пользователя

```bash
curl "https://api.example.com/api/nfc/mirea-cookies?target_tg_userid=123456789" \
  -H "Authorization: Bearer <token>"
```

---

## Структура БД

### Таблица `nfc_cards`

```sql
CREATE TABLE nfc_cards (
    id SERIAL PRIMARY KEY,
    card_id BIGINT NOT NULL,
    tg_userid BIGINT NULL,
    name TEXT NOT NULL,
    owner_group TEXT NOT NULL,
    added_by BIGINT NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(card_id, owner_group)
);
```

**Уникальный индекс**: `(card_id, owner_group)` - одна карта может быть добавлена в разные группы.

---

## Flow для приложения

```
┌─────────────────────────────────────────────────────────────────┐
│                     ДОБАВЛЕНИЕ КАРТЫ                             │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  1. Пользователь нажимает "Добавить карту"                      │
│                                                                  │
│  2. Выбор: "Пользователь есть в боте?" [Да] / [Нет]             │
│                                                                  │
│  ┌──────────────────┐      ┌──────────────────┐                 │
│  │      [Да]        │      │      [Нет]       │                 │
│  └────────┬─────────┘      └────────┬─────────┘                 │
│           │                         │                            │
│           ▼                         ▼                            │
│  ┌──────────────────┐      ┌──────────────────┐                 │
│  │ GET /group-users │      │ Ввод имени       │                 │
│  │ Показать список  │      │ вручную          │                 │
│  │ для выбора       │      │                  │                 │
│  └────────┬─────────┘      └────────┬─────────┘                 │
│           │                         │                            │
│           ▼                         ▼                            │
│  ┌──────────────────┐      ┌──────────────────┐                 │
│  │ Выбрать юзера    │      │ Ввести card_id   │                 │
│  │ Ввести card_id   │      │                  │                 │
│  └────────┬─────────┘      └────────┬─────────┘                 │
│           │                         │                            │
│           ▼                         ▼                            │
│  ┌─────────────────────────────────────────────┐                │
│  │ POST /cards                                  │                │
│  │ {card_id, tg_userid?/name?}                  │                │
│  └─────────────────────────────────────────────┘                │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────┐
│                     ИСПОЛЬЗОВАНИЕ КАРТЫ                          │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  1. GET /cards - получить список карт                           │
│                                                                  │
│  2. Показать список с именами и статусами:                      │
│     ┌────────────────────────────────────────┐                  │
│     │ [✓] Иванов Иван        - В универе     │                  │
│     │ [✗] Петров Пётр        - Вышел 14:30   │                  │
│     │ [?] Сидоров Сидор      - Нет данных    │                  │
│     └────────────────────────────────────────┘                  │
│                                                                  │
│  3. Выбрать карту для использования в NFC                       │
│                                                                  │
│  4. Приложить телефон к турникету                               │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

---

## Важные заметки

1. **Группа автоматическая** - карта всегда привязывается к группе пользователя, который её добавляет
2. **ФИО актуальное** - при получении списка имя берётся из БД, а не из сохранённого значения
3. **Статус только для привязанных** - `is_in_university` доступен только для карт с `tg_userid`
4. **Одна карта - много групп** - одна и та же карта может быть добавлена в разные группы
5. **Удаление только своей группы** - удалить можно только карты из своей группы
