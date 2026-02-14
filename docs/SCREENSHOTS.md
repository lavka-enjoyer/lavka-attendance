# Создание скриншотов для документации

## Демо-режим

Приложение поддерживает демо-режим с фейковыми данными для создания скриншотов без реального API.

### Способ 1: URL параметр

Добавьте `?demo=true` к URL:
```
http://localhost:5173/?demo=true
```

### Способ 2: Переменная окружения

В `.env`:
```env
VITE_DEMO_MODE=true
```

## Запуск

```bash
cd telegram-mini-app
npm run dev
```

Откройте http://localhost:5173/?demo=true

## Демо-данные

Файл `src/demo/mockData.js` содержит:

- **DEMO_USER** — фейковый пользователь (Иванов Иван Иванович, ИКБО-01-23)
- **DEMO_SCHEDULE** — расписание на 2 дня с 4-6 парами
- **DEMO_POINTS** — БРС баллы по 5 предметам
- **DEMO_ATTENDANCE_HISTORY** — история посещений

## Кастомизация данных

Отредактируйте `src/demo/mockData.js`:

```javascript
export const DEMO_USER = {
  fio: 'Ваше Имя',
  group: 'ИКБО-XX-XX',
  // ...
};
```

## Рекомендации по скриншотам

1. **Размер окна**: 375×812 (iPhone X) для мобильного вида
2. **Формат**: PNG
3. **Именование**: `main.png`, `schedule.png`, `points.png`
4. **Папка**: `docs/screenshots/`

### Рекомендуемые скриншоты

| Файл | Описание | Экран |
|------|----------|-------|
| main.png | Главный экран | MainScreen |
| schedule.png | Расписание на день | ScheduleScreen |
| points.png | БРС баллы | PointsScreen |
| login.png | Форма входа | LoginForm |
| mark.png | Отметка посещения | MarkSelfScreen |

## Chrome DevTools

1. F12 → Toggle device toolbar (Ctrl+Shift+M)
2. Выберите iPhone X или задайте 375×812
3. Сделайте скриншот: Ctrl+Shift+P → "Capture screenshot"
