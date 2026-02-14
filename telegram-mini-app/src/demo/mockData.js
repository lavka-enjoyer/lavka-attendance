/**
 * Моковые данные для демо-режима
 * Используются для скриншотов и демонстрации без реального API
 *
 * Активация: добавить ?demo=true в URL или установить VITE_DEMO_MODE=true
 */

export const DEMO_USER = {
  fio: 'Иванов Иван Иванович',
  group: 'ИКБО-01-23',
  login: 'ivanov_ii',
  allowConfirm: true,
  admin_lvl: 0,
};

// Текущая дата для расписания
const today = new Date();
const formatDate = (date) => date.toISOString().split('T')[0];

// Функция для генерации расписания с текущей парой в формате API
const generateDemoSchedule = () => {
  const now = new Date();
  // Формат даты для API: YYYY-MM-DD
  const dateStr = now.toISOString().split('T')[0];

  // Генерируем время для "текущей" пары - начинается 30 минут назад, заканчивается через 60 минут
  const currentHour = now.getHours();
  const currentMinute = now.getMinutes();

  // Время начала текущей пары (30 минут назад)
  const currentStart = new Date(now);
  currentStart.setMinutes(currentMinute - 30);
  const currentStartStr = `${String(currentStart.getHours()).padStart(2, '0')}:${String(currentStart.getMinutes()).padStart(2, '0')}`;

  // Время конца текущей пары (через 60 минут от начала = 30 минут от сейчас)
  const currentEnd = new Date(currentStart);
  currentEnd.setMinutes(currentStart.getMinutes() + 90); // Пара длится 1.5 часа
  const currentEndStr = `${String(currentEnd.getHours()).padStart(2, '0')}:${String(currentEnd.getMinutes()).padStart(2, '0')}`;

  const lessons = [
    {
      subject: 'Математический анализ',
      type: 'ЛК',
      room: 'А-123',
      teacher: 'Петров П.П.',
      status: '+', // Был на паре
      time: '09:00 - 10:30',
    },
    {
      subject: 'Программирование на Python',
      type: 'ПР',
      room: 'В-456',
      teacher: 'Сидорова А.В.',
      status: '+',
      time: '10:40 - 12:10',
    },
    {
      subject: 'Физика',
      type: 'ЛК',
      room: 'Б-789',
      teacher: 'Козлов К.К.',
      status: null, // Текущая пара
      time: `${currentStartStr} - ${currentEndStr}`, // Динамическое время - всегда "сейчас"
    },
    {
      subject: 'Английский язык',
      type: 'ПР',
      room: 'Г-012',
      teacher: 'Смирнова Е.Н.',
      status: null,
      time: '16:20 - 17:50',
    },
  ];

  // Добавляем uuid и дату
  return lessons.map((lesson, index) => ({
    ...lesson,
    uuid: `demo-lesson-${index}`,
    date: dateStr,
  }));
};

export const DEMO_SCHEDULE = {
  lessons: generateDemoSchedule(),
};

export const DEMO_POINTS = {
  points: [
    {
      Дисциплина: 'Математический анализ',
      fields: {
        "Всего баллов (Макс. 100)": 78,
        "Посещаемость (Макс. 20)": { now: 18, max: 20 },
        "Контрольная работа (Макс. 30)": { now: 25, max: 30 },
        "Практические занятия (Макс. 50)": { now: 35, max: 50 }
      }
    },
    {
      Дисциплина: 'Программирование на Python',
      fields: {
        "Всего баллов (Макс. 100)": 92,
        "Посещаемость (Макс. 20)": { now: 20, max: 20 },
        "Лабораторные работы (Макс. 40)": { now: 38, max: 40 },
        "Курсовой проект (Макс. 40)": { now: 34, max: 40 }
      }
    },
    {
      Дисциплина: 'Физика',
      fields: {
        "Всего баллов (Макс. 100)": 65,
        "Посещаемость (Макс. 20)": { now: 14, max: 20 },
        "Лабораторные работы (Макс. 30)": { now: 21, max: 30 },
        "Экзамен (Макс. 50)": { now: 30, max: 50 }
      }
    },
    {
      Дисциплина: 'Английский язык',
      fields: {
        "Всего баллов (Макс. 100)": 85,
        "Посещаемость (Макс. 20)": { now: 19, max: 20 },
        "Устная речь (Макс. 40)": { now: 36, max: 40 },
        "Письменные задания (Макс. 40)": { now: 30, max: 40 }
      }
    },
    {
      Дисциплина: 'Базы данных',
      fields: {
        "Всего баллов (Макс. 100)": 88,
        "Посещаемость (Макс. 20)": { now: 18, max: 20 },
        "Лабораторные работы (Макс. 40)": { now: 35, max: 40 },
        "Курсовой проект (Макс. 40)": { now: 35, max: 40 }
      }
    },
  ],
};

export const DEMO_GROUP_USERS = [
  { tg_id: 1, fio: 'Иванов Иван Иванович', allowConfirm: true },
  { tg_id: 2, fio: 'Петрова Анна Сергеевна', allowConfirm: true },
  { tg_id: 3, fio: 'Сидоров Алексей Владимирович', allowConfirm: true },
  { tg_id: 4, fio: 'Козлова Мария Александровна', allowConfirm: false },
  { tg_id: 5, fio: 'Николаев Дмитрий Игоревич', allowConfirm: true },
  { tg_id: 6, fio: 'Смирнова Елена Павловна', allowConfirm: true },
  { tg_id: 7, fio: 'Федоров Андрей Николаевич', allowConfirm: true },
  { tg_id: 8, fio: 'Морозова Ольга Викторовна', allowConfirm: false },
];

// Wrapped format for API response (used by MarkMultipleScreen)
export const DEMO_GROUP_USERS_RESPONSE = {
  users: DEMO_GROUP_USERS
};

export const DEMO_GROUP_UNIVERSITY_STATUS = {
  students: [
    { tg_id: 1, fio: 'Иванов Иван Иванович', is_inside_university: true, time_in_university: '3 ч 15 мин', last_event_time: '08:45' },
    { tg_id: 2, fio: 'Петрова Анна Сергеевна', is_inside_university: true, time_in_university: '3 ч 30 мин', last_event_time: '08:30' },
    { tg_id: 3, fio: 'Сидоров Алексей Владимирович', is_inside_university: true, time_in_university: '3 ч', last_event_time: '09:00' },
    { tg_id: 4, fio: 'Козлова Мария Александровна', is_inside_university: false, time_out_university: '2 ч 40 мин', last_event_time: '14:20' },
    { tg_id: 5, fio: 'Николаев Дмитрий Игоревич', is_inside_university: true, time_in_university: '3 ч 5 мин', last_event_time: '08:55' },
    { tg_id: 6, fio: 'Смирнова Елена Павловна', is_inside_university: false, time_out_university: 'Не заходил сегодня', last_event_time: null },
    { tg_id: 7, fio: 'Федоров Андрей Николаевич', is_inside_university: true, time_in_university: '4 ч 10 мин', last_event_time: '07:50' },
    { tg_id: 8, fio: 'Морозова Ольга Викторовна', is_inside_university: false, time_out_university: '4 ч 30 мин', last_event_time: '12:30' },
  ],
  total: 8,
  inside: 5,
  outside: 3,
};

export const DEMO_LESSON_ATTENDANCE = {
  students: [
    { fio: 'Иванов Иван Иванович', status: 'present', marked_at: '09:05' },
    { fio: 'Петрова Анна Сергеевна', status: 'present', marked_at: '09:02' },
    { fio: 'Сидоров Алексей Владимирович', status: 'present', marked_at: '09:10' },
    { fio: 'Козлова Мария Александровна', status: 'absent', marked_at: null },
    { fio: 'Николаев Дмитрий Игоревич', status: 'present', marked_at: '09:01' },
    { fio: 'Смирнова Елена Павловна', status: 'late', marked_at: '09:25' },
    { fio: 'Федоров Андрей Николаевич', status: 'present', marked_at: '08:58' },
    { fio: 'Морозова Ольга Викторовна', status: 'absent', marked_at: null },
  ],
};

export const DEMO_AVAILABLE_GROUPS = [
  'ИКБО-01-23',
  'ИКБО-02-23',
  'ИКБО-03-23',
  'ИВБО-01-23',
  'ИВБО-02-23',
];

// Wrapped format for API response (used by MarkMultipleScreen)
export const DEMO_AVAILABLE_GROUPS_RESPONSE = {
  groups: DEMO_AVAILABLE_GROUPS
};

// Стоимость посещения для каждого предмета (количество пар в семестре)
export const DEMO_LESSONS_COST = {
  lessons_cost: {
    'Математический анализ': 32,
    'Программирование на Python': 28,
    'Физика': 24,
    'Английский язык': 30,
    'Базы данных': 26,
  },
  cached: true
};

export const DEMO_LESSONS_CALENDAR = {
  calendar: {
    [today.getFullYear()]: {
      // Месяц должен быть строкой с ведущим нулём (формат API)
      [String(today.getMonth() + 1).padStart(2, '0')]: (() => {
        const days = {};
        for (let i = 1; i <= 28; i++) {
          // Пропускаем выходные (примерно)
          const date = new Date(today.getFullYear(), today.getMonth(), i);
          if (date.getDay() !== 0 && date.getDay() !== 6) {
            days[i] = Math.floor(Math.random() * 4) + 2; // 2-5 пар
          }
        }
        return days;
      })(),
    },
  },
};

export const DEMO_MARKING_SESSION = {
  session_id: 'demo-session-123',
  status: 'completed',
  total: 5,
  success: 4,
  failed: 1,
  results: [
    { fio: 'Иванов Иван Иванович', status: 'success', message: 'Отмечен' },
    { fio: 'Петрова Анна Сергеевна', status: 'success', message: 'Отмечен' },
    { fio: 'Сидоров Алексей Владимирович', status: 'success', message: 'Отмечен' },
    { fio: 'Николаев Дмитрий Игоревич', status: 'success', message: 'Отмечен' },
    { fio: 'Федоров Андрей Николаевич', status: 'failed', message: 'Уже отмечен' },
  ],
};

/**
 * Проверяет, включён ли демо-режим
 */
export function isDemoMode() {
  // Проверяем URL параметр
  if (typeof window !== 'undefined') {
    const urlParams = new URLSearchParams(window.location.search);
    if (urlParams.get('demo') === 'true') {
      return true;
    }
  }
  // Проверяем переменную окружения
  return import.meta.env.VITE_DEMO_MODE === 'true';
}

/**
 * Задержка для имитации сети
 */
export const demoDelay = (ms = 500) =>
  new Promise((resolve) => setTimeout(resolve, ms + Math.random() * 300));
