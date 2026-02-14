import React, { useState, useEffect, useRef } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { ChevronLeft, ChevronRight, Calendar, Clock, MapPin, User, BookOpen, ArrowLeft, Users, Info, X } from 'lucide-react';
import { Alert, AlertDescription } from './ui/alert';
import apiService from '../services/apiService';
import AttendanceModal from './AttendanceModal';

// Улучшенный хук для обработки свайпов с определением направления и визуальным следованием
const useSwipe = (onSwipeLeft, onSwipeRight, threshold = 50, onSwipeMove = null) => {
  const touchStartX = useRef(0);
  const touchStartY = useRef(0);
  const touchCurrentX = useRef(0);
  const swipeDirection = useRef(null); // 'horizontal' | 'vertical' | null
  const isSwipeActive = useRef(false);

  const handleTouchStart = (e) => {
    touchStartX.current = e.touches[0].clientX;
    touchStartY.current = e.touches[0].clientY;
    touchCurrentX.current = e.touches[0].clientX;
    swipeDirection.current = null;
    isSwipeActive.current = false;
  };

  const handleTouchMove = (e) => {
    touchCurrentX.current = e.touches[0].clientX;
    const currentY = e.touches[0].clientY;

    const diffX = touchCurrentX.current - touchStartX.current;
    const diffY = currentY - touchStartY.current;

    // Определяем направление свайпа при первом значительном движении
    if (swipeDirection.current === null && (Math.abs(diffX) > 10 || Math.abs(diffY) > 10)) {
      if (Math.abs(diffX) > Math.abs(diffY) * 1.5) {
        // Горизонтальный свайп (X движение значительно больше Y)
        swipeDirection.current = 'horizontal';
        isSwipeActive.current = true;
      } else {
        // Вертикальный свайп или диагональный - не обрабатываем
        swipeDirection.current = 'vertical';
        isSwipeActive.current = false;
      }
    }

    // Если это горизонтальный свайп, предотвращаем скролл и вызываем callback для визуального следования
    if (swipeDirection.current === 'horizontal') {
      e.preventDefault(); // Предотвращаем вертикальный скролл
      e.stopPropagation(); // Предотвращаем срабатывание родительских обработчиков

      if (onSwipeMove) {
        onSwipeMove(diffX);
      }
    }
  };

  const handleTouchEnd = (e) => {
    const diff = touchCurrentX.current - touchStartX.current;

    // Завершаем визуальное следование
    if (onSwipeMove) {
      onSwipeMove(0, true); // true означает что свайп завершен
    }

    // Срабатываем только если это был горизонтальный свайп и порог пройден
    if (swipeDirection.current === 'horizontal' && Math.abs(diff) > threshold) {
      if (diff > 0) {
        // Свайп вправо -> предыдущий
        onSwipeRight && onSwipeRight();
      } else {
        // Свайп влево -> следующий
        onSwipeLeft && onSwipeLeft();
      }
    }

    // Сброс
    swipeDirection.current = null;
    isSwipeActive.current = false;
  };

  return {
    onTouchStart: handleTouchStart,
    onTouchMove: handleTouchMove,
    onTouchEnd: handleTouchEnd,
  };
};

const ScheduleScreen = ({ initData, onBack, onApiError }) => {
  const [selectedDate, setSelectedDate] = useState(new Date());
  const [weekStart, setWeekStart] = useState(null);
  const [schedule, setSchedule] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  // Состояние для модального окна посещаемости
  const [attendanceModalOpen, setAttendanceModalOpen] = useState(false);
  const [attendanceData, setAttendanceData] = useState(null);
  const [attendanceLoading, setAttendanceLoading] = useState(false);
  const [attendanceError, setAttendanceError] = useState('');

  // Состояние для модального окна информации о стоимости
  const [costInfoModalOpen, setCostInfoModalOpen] = useState(false);
  const [costInfoData, setCostInfoData] = useState(null);

  // Кеш количества пар по предметам (subject -> total_lessons)
  const [subjectLessonCounts, setSubjectLessonCounts] = useState({});

  // Состояние для визуального следования при свайпе
  const [calendarSwipeOffset, setCalendarSwipeOffset] = useState(0);
  const [scheduleSwipeOffset, setScheduleSwipeOffset] = useState(0);
  const [isCalendarSwiping, setIsCalendarSwiping] = useState(false);
  const [isScheduleSwiping, setIsScheduleSwiping] = useState(false);

  // Состояние для анимации смены недели
  const [isWeekChanging, setIsWeekChanging] = useState(false);
  const [direction, setDirection] = useState(0);

  // Календарь занятий (количество пар по дням)
  const [lessonsCalendar, setLessonsCalendar] = useState({});

  // Отслеживание загруженного диапазона дат календаря
  const [calendarLoadedRange, setCalendarLoadedRange] = useState({
    startTs: null,
    endTs: null
  });

  // Флаг загрузки дополнительных данных календаря
  const [calendarLoading, setCalendarLoading] = useState(false);

  // Инициализация начала недели и загрузка календаря
  useEffect(() => {
    const today = new Date();
    const dayOfWeek = today.getDay();
    // Понедельник - первый день недели
    const diff = dayOfWeek === 0 ? -6 : 1 - dayOfWeek;
    const monday = new Date(today);
    monday.setDate(today.getDate() + diff);
    monday.setHours(0, 0, 0, 0);
    setWeekStart(monday);

    // Загружаем календарь занятий один раз при инициализации
    loadLessonsCalendar();

    // Загружаем стоимости пар для всей группы один раз
    loadLessonsCost();
  }, []);

  // Загрузка календаря занятий (количество пар по дням)
  const loadLessonsCalendar = async (startTs = null, endTs = null) => {
    try {
      setCalendarLoading(true);
      const result = await apiService.getLessonsCalendar(initData, startTs, endTs);

      if (result && result.calendar) {
        // Мержим новые данные с существующими
        setLessonsCalendar(prev => {
          const merged = { ...prev };
          for (const year in result.calendar) {
            if (!merged[year]) {
              merged[year] = {};
            }
            for (const month in result.calendar[year]) {
              if (!merged[year][month]) {
                merged[year][month] = {};
              }
              // Добавляем дни
              for (const day in result.calendar[year][month]) {
                merged[year][month][day] = result.calendar[year][month][day];
              }
            }
          }
          return merged;
        });

        // Обновляем диапазон загруженных дат
        const now = new Date();
        if (startTs === null && endTs === null) {
          // Первоначальная загрузка: -60 дней до +90 дней (как в бекенде по умолчанию)
          const defaultStart = new Date(now);
          defaultStart.setDate(defaultStart.getDate() - 60);
          const defaultEnd = new Date(now);
          defaultEnd.setDate(defaultEnd.getDate() + 90);

          setCalendarLoadedRange({
            startTs: Math.floor(defaultStart.getTime() / 1000),
            endTs: Math.floor(defaultEnd.getTime() / 1000)
          });
        } else {
          // Расширяем диапазон
          setCalendarLoadedRange(prev => ({
            startTs: startTs !== null ? Math.min(prev.startTs || startTs, startTs) : prev.startTs,
            endTs: endTs !== null ? Math.max(prev.endTs || endTs, endTs) : prev.endTs
          }));
        }
      }
    } catch (error) {
      // Проверяем ошибки подписки
      if (onApiError && onApiError(error)) {
        return;
      }
    } finally {
      setCalendarLoading(false);
    }
  };

  // Проверяем, нужно ли подгружать больше данных календаря при изменении weekStart
  useEffect(() => {
    if (!weekStart || !calendarLoadedRange.startTs || calendarLoading) return;

    const weekStartTs = Math.floor(weekStart.getTime() / 1000);
    const weekEndTs = weekStartTs + (7 * 24 * 60 * 60); // +7 дней

    // Проверяем, не вышли ли мы за границы загруженного диапазона
    const bufferDays = 30 * 24 * 60 * 60; // 30 дней буфер

    // Если ушли назад за пределы загруженного диапазона
    if (weekStartTs < calendarLoadedRange.startTs + bufferDays) {
      // Загружаем ещё 90 дней назад от начала загруженного диапазона
      const newStartTs = calendarLoadedRange.startTs - (90 * 24 * 60 * 60);
      const newEndTs = calendarLoadedRange.startTs;
      loadLessonsCalendar(newStartTs, newEndTs);
    }

    // Если ушли вперёд за пределы загруженного диапазона
    if (weekEndTs > calendarLoadedRange.endTs - bufferDays) {
      // Загружаем ещё 90 дней вперёд от конца загруженного диапазона
      const newStartTs = calendarLoadedRange.endTs;
      const newEndTs = calendarLoadedRange.endTs + (90 * 24 * 60 * 60);
      loadLessonsCalendar(newStartTs, newEndTs);
    }
  }, [weekStart, calendarLoadedRange, calendarLoading]);

  // Загрузка стоимости пар для всех предметов группы
  const loadLessonsCost = async () => {
    try {
      const result = await apiService.getLessonsCost(initData);

      if (result && result.lessons_cost) {
        setSubjectLessonCounts(result.lessons_cost);
      }
    } catch (error) {
      // Проверяем ошибки подписки
      if (onApiError && onApiError(error)) {
        return;
      }
    }
  };

  // Загрузка расписания при изменении выбранной даты
  useEffect(() => {
    if (selectedDate) {
      // Сбрасываем offset при смене даты
      setScheduleSwipeOffset(0);
      setIsScheduleSwiping(false);
      loadSchedule(selectedDate);
    }
  }, [selectedDate]);

  // Функция для загрузки расписания
  const loadSchedule = async (date) => {
    setLoading(true);
    setError('');

    try {
      const year = date.getFullYear();
      const month = date.getMonth() + 1; // JavaScript months are 0-indexed
      const day = date.getDate();

      const result = await apiService.getSchedule(initData, year, month, day);

      // API возвращает { lessons: [...] }
      setSchedule(result.lessons || []);
    } catch (err) {
      console.error('Ошибка при загрузке расписания:', err);

      // Проверяем ошибки подписки
      if (onApiError && onApiError(err)) {
        return;
      }

      setError(err.message || 'Не удалось загрузить расписание');
    } finally {
      setLoading(false);
    }
  };

  // Функция для получения дней текущей недели
  const getWeekDays = () => {
    if (!weekStart) return [];

    const days = [];
    for (let i = 0; i < 7; i++) {
      const date = new Date(weekStart);
      date.setDate(weekStart.getDate() + i);
      days.push(date);
    }
    return days;
  };

  // Навигация по неделям
  const previousWeek = () => {
    setDirection(-1);
    // Сбрасываем offset расписания
    setScheduleSwipeOffset(0);
    setIsScheduleSwiping(false);

    const newWeekStart = new Date(weekStart);
    newWeekStart.setDate(weekStart.getDate() - 7);
    setWeekStart(newWeekStart);
  };

  const nextWeek = () => {
    setDirection(1);
    // Сбрасываем offset расписания
    setScheduleSwipeOffset(0);
    setIsScheduleSwiping(false);

    const newWeekStart = new Date(weekStart);
    newWeekStart.setDate(weekStart.getDate() + 7);
    setWeekStart(newWeekStart);
  };

  // Навигация по дням
  const previousDay = () => {
    // Сбрасываем offset сразу
    setScheduleSwipeOffset(0);
    setIsScheduleSwiping(false);

    setTimeout(() => {
      const newDate = new Date(selectedDate);
      newDate.setDate(selectedDate.getDate() - 1);
      setSelectedDate(newDate);

      // Проверяем, нужно ли переключить неделю
      if (newDate < weekStart) {
        previousWeek();
      }
    }, 200);
  };

  const nextDay = () => {
    // Сбрасываем offset сразу
    setScheduleSwipeOffset(0);
    setIsScheduleSwiping(false);

    setTimeout(() => {
      const newDate = new Date(selectedDate);
      newDate.setDate(selectedDate.getDate() + 1);
      setSelectedDate(newDate);

      // Проверяем, нужно ли переключить неделю
      const weekEnd = new Date(weekStart);
      weekEnd.setDate(weekStart.getDate() + 6);
      if (newDate > weekEnd) {
        nextWeek();
      }
    }, 200);
  };

  // Колбэк для визуального следования при свайпе календаря
  const handleCalendarSwipeMove = (offset, isEnd = false) => {
    // Не обрабатываем свайпы во время смены недели
    if (isWeekChanging) return;

    if (isEnd) {
      setCalendarSwipeOffset(0);
      setIsCalendarSwiping(false);
    } else {
      // Используем requestAnimationFrame для плавности
      requestAnimationFrame(() => {
        setCalendarSwipeOffset(offset);
        if (!isCalendarSwiping) {
          setIsCalendarSwiping(true);
        }
      });
    }
  };

  // Колбэк для визуального следования при свайпе расписания
  const handleScheduleSwipeMove = (offset, isEnd = false) => {
    if (isEnd) {
      setScheduleSwipeOffset(0);
      setIsScheduleSwiping(false);
    } else {
      // Используем requestAnimationFrame для плавности
      requestAnimationFrame(() => {
        setScheduleSwipeOffset(offset);
        if (!isScheduleSwiping) {
          setIsScheduleSwiping(true);
        }
      });

      // Предзагрузка соседних дней при начале свайпа
      if (Math.abs(offset) > 20 && !isScheduleSwiping) {
        // Загружаем следующий или предыдущий день в фоне
        const preloadDate = new Date(selectedDate);
        if (offset < 0) {
          // Свайпаем влево - предзагружаем следующий день
          preloadDate.setDate(selectedDate.getDate() + 1);
        } else {
          // Свайпаем вправо - предзагружаем предыдущий день
          preloadDate.setDate(selectedDate.getDate() - 1);
        }
        // Можно добавить кеширование, но пока просто загружаем при переходе
      }
    }
  };

  // Свайпы для календаря (неделя)
  const calendarSwipeHandlers = useSwipe(nextWeek, previousWeek, 50, handleCalendarSwipeMove);

  // Свайпы для основного экрана (день)
  const scheduleSwipeHandlers = useSwipe(nextDay, previousDay, 50, handleScheduleSwipeMove);

  // Функция для проверки, является ли дата выбранной
  const isSelectedDate = (date) => {
    return (
      date.getDate() === selectedDate.getDate() &&
      date.getMonth() === selectedDate.getMonth() &&
      date.getFullYear() === selectedDate.getFullYear()
    );
  };

  // Функция для проверки, является ли дата сегодняшней
  const isToday = (date) => {
    const today = new Date();
    return (
      date.getDate() === today.getDate() &&
      date.getMonth() === today.getMonth() &&
      date.getFullYear() === today.getFullYear()
    );
  };

  // Форматирование названия месяца
  const getMonthName = () => {
    if (!weekStart) return '';
    const months = ['Январь', 'Февраль', 'Март', 'Апрель', 'Май', 'Июнь',
                   'Июль', 'Август', 'Сентябрь', 'Октябрь', 'Ноябрь', 'Декабрь'];
    return `${months[weekStart.getMonth()]} ${weekStart.getFullYear()}`;
  };

  // Форматирование дня недели
  const getDayName = (date) => {
    const days = ['Вс', 'Пн', 'Вт', 'Ср', 'Чт', 'Пт', 'Сб'];
    return days[date.getDay()];
  };

  // Получение иконки типа занятия
  const getLessonTypeColor = (type) => {
    switch (type) {
      case 'ЛК': return 'bg-blue-500/10 text-blue-500';
      case 'ПР': return 'bg-green-500/10 text-green-500';
      case 'ЛАБ': return 'bg-purple-500/10 text-purple-500';
      case 'Э':
      case 'ЭКЗ': return 'bg-red-500/10 text-red-500';
      case 'ЗАЧ': return 'bg-orange-500/10 text-orange-500';
      case 'КП': return 'bg-pink-500/10 text-pink-500';
      case 'Конс':
      case 'КОНС': return 'bg-yellow-500/10 text-yellow-500';
      default: return 'bg-gray-500/10 text-gray-500';
    }
  };

  // Получение отображаемого названия типа пары
  const getLessonTypeDisplay = (type) => {
    switch (type) {
      case 'Э': return 'Экзамен';
      case 'ЗАЧ': return 'Зачёт';
      case 'КП': return 'Курсовой проект';
      case 'Конс': return 'Консультация';
      default: return type;
    }
  };

  // Проверяет, есть ли пара в журнале посещаемости
  // Предмет должен быть в журнале И тип пары должен отслеживаться (не Э, ЗАЧ, КП, Конс)
  const hasAttendanceTracking = (lesson) => {
    const noTrackingTypes = ['ЗАЧ', 'Э', 'КП', 'Конс'];
    const subjectInJournal = subjectLessonCounts[lesson.subject] && subjectLessonCounts[lesson.subject] > 0;
    const typeTracked = !noTrackingTypes.includes(lesson.type);
    return subjectInJournal && typeTracked;
  };

  // Получение стиля статуса посещения
  const getStatusBadge = (status) => {
    switch (status) {
      case '+':
        return <span className="px-2 py-1 text-xs rounded-lg bg-green-500/10 text-green-500 font-medium">Был</span>;
      case 'Н':
        return <span className="px-2 py-1 text-xs rounded-lg bg-red-500/10 text-red-500 font-medium">Не был</span>;
      case 'У':
        return <span className="px-2 py-1 text-xs rounded-lg bg-yellow-500/10 text-yellow-500 font-medium">Уваж.</span>;
      default:
        return null;
    }
  };

  // Функция для загрузки статистики посещаемости
  const loadAttendance = async (lesson) => {
    setAttendanceModalOpen(true);
    setAttendanceLoading(true);
    setAttendanceError('');
    setAttendanceData(null);

    try {
      // Вычисляем индекс этой пары в дне (для случая когда несколько пар одного типа и предмета)
      // Считаем сколько таких же пар было раньше в этот день
      let lessonIndexInDay = 0;
      for (const l of schedule) {
        if (l.uuid === lesson.uuid) {
          break; // Нашли текущую пару, останавливаемся
        }
        // Проверяем: та же дата, тот же тип, тот же предмет
        if (l.date === lesson.date && l.type === lesson.type && l.subject === lesson.subject) {
          lessonIndexInDay++;
        }
      }

      const result = await apiService.getLessonAttendance(
        initData,
        lesson.date,
        lesson.time.split(' - ')[0], // Берем только начальное время
        lesson.type,
        lesson.subject,
        lessonIndexInDay // Передаем индекс пары в дне
      );

      setAttendanceData(result);

      // Сохраняем количество пар для этого предмета, если есть в ответе
      if (result && result.total_lessons && lesson.subject) {
        setSubjectLessonCounts(prev => ({
          ...prev,
          [lesson.subject]: result.total_lessons
        }));
      }
    } catch (err) {
      console.error('Ошибка при загрузке статистики посещаемости:', err);

      // Проверяем ошибки подписки
      if (onApiError && onApiError(err)) {
        setAttendanceModalOpen(false);
        return;
      }

      setAttendanceError(err.message || 'Не удалось загрузить статистику посещаемости');
    } finally {
      setAttendanceLoading(false);
    }
  };

  // Функция для получения количества занятий для даты
  const getLessonsCount = (date) => {
    const year = date.getFullYear().toString();
    const month = String(date.getMonth() + 1).padStart(2, '0');
    const day = date.getDate();

    // Получаем данные из календаря
    if (lessonsCalendar[year] && lessonsCalendar[year][month] && lessonsCalendar[year][month][day]) {
      return lessonsCalendar[year][month][day];
    }

    return 0;
  };

  // Функция для проверки, является ли пара текущей
  const isCurrentLesson = (lesson) => {
    const now = new Date();

    // Проверяем, что это сегодняшний день
    const lessonDate = new Date(lesson.date);
    if (lessonDate.toDateString() !== now.toDateString()) {
      return false;
    }

    // Парсим время начала и конца пары
    const [startTime, endTime] = lesson.time.split(' - ');
    const [startHour, startMinute] = startTime.split(':').map(Number);
    const [endHour, endMinute] = endTime.split(':').map(Number);

    const lessonStart = new Date(now);
    lessonStart.setHours(startHour, startMinute, 0, 0);

    const lessonEnd = new Date(now);
    lessonEnd.setHours(endHour, endMinute, 0, 0);

    // Проверяем, находимся ли мы между началом и концом пары
    return now >= lessonStart && now <= lessonEnd;
  };

  // Функция для расчета прогресса пары (в процентах)
  const getLessonProgress = (lesson) => {
    const now = new Date();

    // Парсим время начала и конца пары
    const [startTime, endTime] = lesson.time.split(' - ');
    const [startHour, startMinute] = startTime.split(':').map(Number);
    const [endHour, endMinute] = endTime.split(':').map(Number);

    const lessonStart = new Date(now);
    lessonStart.setHours(startHour, startMinute, 0, 0);

    const lessonEnd = new Date(now);
    lessonEnd.setHours(endHour, endMinute, 0, 0);

    const totalDuration = lessonEnd - lessonStart;
    const elapsed = now - lessonStart;

    const progress = (elapsed / totalDuration) * 100;
    return Math.max(0, Math.min(100, progress)); // Ограничиваем от 0 до 100
  };

  // Функция для расчёта баллов за посещение одной пары
  const getAttendancePoints = (lesson) => {
    // Проверяем, есть ли у нас данные о количестве пар для этого предмета
    const totalLessons = subjectLessonCounts[lesson.subject];

    if (totalLessons && totalLessons > 0) {
      // Используем реальные данные из журнала
      const pointsPerLesson = 30 / totalLessons;
      const result = pointsPerLesson.toFixed(1);
      return result;
    }

    return null;
  };

  // Функция для получения оставшегося времени до конца пары
  const getRemainingTime = (lesson) => {
    const now = new Date();

    // Парсим время окончания пары
    const [, endTime] = lesson.time.split(' - ');
    const [endHour, endMinute] = endTime.split(':').map(Number);

    const lessonEnd = new Date(now);
    lessonEnd.setHours(endHour, endMinute, 0, 0);

    const remaining = lessonEnd - now;

    // Переводим в минуты
    const minutes = Math.floor(remaining / 1000 / 60);
    const hours = Math.floor(minutes / 60);
    const mins = minutes % 60;

    if (hours > 0) {
      return `${hours}ч ${mins}м`;
    } else {
      return `${mins}м`;
    }
  };

  // Дозагрузка недостающих данных о предметах (если их нет в кеше)
  useEffect(() => {
    const loadMissingSubjectCounts = async () => {
      if (!schedule || schedule.length === 0) return;

      // Получаем предметы, для которых нет данных
      const uniqueSubjects = [...new Set(schedule.map(lesson => lesson.subject))];
      const missingSubjects = uniqueSubjects.filter(subject => !subjectLessonCounts[subject]);

      if (missingSubjects.length === 0) {
        return;
      }

      // Загружаем данные только для недостающих предметов
      for (const subject of missingSubjects) {
        const firstLesson = schedule.find(l => l.subject === subject);
        if (!firstLesson) continue;

        try {
          let lessonIndexInDay = 0;
          for (const l of schedule) {
            if (l.uuid === firstLesson.uuid) break;
            if (l.date === firstLesson.date && l.type === firstLesson.type && l.subject === firstLesson.subject) {
              lessonIndexInDay++;
            }
          }

          const result = await apiService.getLessonAttendance(
            initData,
            firstLesson.date,
            firstLesson.time.split(' - ')[0],
            firstLesson.type,
            firstLesson.subject,
            lessonIndexInDay
          );

          if (result && result.total_lessons) {
            setSubjectLessonCounts(prev => ({
              ...prev,
              [subject]: result.total_lessons
            }));
          }
        } catch (err) {
          console.error(`[ATTENDANCE POINTS] Ошибка для ${subject}:`, err);
        }
      }
    };

    loadMissingSubjectCounts();
  }, [schedule, initData, subjectLessonCounts]);

  // Обновление текущего времени каждую минуту для обновления прогресса
  useEffect(() => {
    const interval = setInterval(() => {
      // Принудительно перерисовываем компонент каждую минуту
      setSchedule(prevSchedule => [...prevSchedule]);
    }, 60000); // Каждую минуту

    return () => clearInterval(interval);
  }, []);

  const weekDays = getWeekDays();

  return (
    <motion.div 
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        exit={{ opacity: 0 }}
        className="p-4 w-full max-w-md mx-auto min-h-screen flex flex-col bg-[var(--bg-color)]"
    >
      {/* Header */}
      <div className="flex items-center mb-6">
        <motion.button
          whileHover={{ scale: 1.1 }}
          whileTap={{ scale: 0.9 }}
          onClick={onBack}
          className="mr-3 p-2 rounded-full hover:bg-white/10 transition-colors text-[var(--text-color)]"
        >
          <ArrowLeft size={24} />
        </motion.button>
        <h1 className="text-2xl font-bold flex items-center text-[var(--text-color)]">
          <Calendar className="mr-2" size={28} />
          Расписание
        </h1>
      </div>

        {/* Week Navigator */}
      <motion.div
        initial={{ y: -20, opacity: 0 }}
        animate={{ y: 0, opacity: 1 }}
        className="glass rounded-2xl p-4 mb-4 shadow-lg"
      >
        {/* Month and navigation */}
        <div className="flex items-center justify-between mb-4">
          <motion.button
            whileHover={{ scale: 1.1 }}
            whileTap={{ scale: 0.9 }}
            onClick={previousWeek}
            className="p-2 rounded-xl hover:bg-white/10 text-[var(--text-color)]"
          >
            <ChevronLeft size={20} />
          </motion.button>
          <span className="font-medium text-[var(--text-color)]">
            {getMonthName()}
          </span>
          <motion.button
            whileHover={{ scale: 1.1 }}
            whileTap={{ scale: 0.9 }}
            onClick={nextWeek}
            className="p-2 rounded-xl hover:bg-white/10 text-[var(--text-color)]"
          >
            <ChevronRight size={20} />
          </motion.button>
        </div>

        {/* Week days */}
        <div className="relative overflow-hidden">
          <AnimatePresence mode="popLayout" custom={direction} initial={false}>
            <motion.div
              key={weekStart ? weekStart.toISOString() : 'init'}
              custom={direction}
              variants={{
                enter: (direction) => ({
                  x: direction > 0 ? '100%' : '-100%',
                  opacity: 0
                }),
                center: {
                  zIndex: 1,
                  x: 0,
                  opacity: 1
                },
                exit: (direction) => ({
                  zIndex: 0,
                  x: direction < 0 ? '100%' : '-100%',
                  opacity: 0
                })
              }}
              initial="enter"
              animate={isCalendarSwiping ? { x: calendarSwipeOffset, opacity: 1 } : "center"}
              exit="exit"
              transition={{
                x: { type: "spring", stiffness: 300, damping: 30 },
                opacity: { duration: 0.2 }
              }}
              {...calendarSwipeHandlers}
              className="grid grid-cols-7 gap-2 w-full"
            >
          {weekDays.map((date, index) => {
            const selected = isSelectedDate(date);
            const today = isToday(date);
            const lessonsCount = getLessonsCount(date);

            return (
              <motion.button
                key={index}
                whileTap={{ scale: 0.95 }}
                onClick={() => setSelectedDate(date)}
                className={`flex flex-col items-center justify-center p-2 rounded-xl transition-all relative ${
                  selected ? 'shadow-lg shadow-blue-500/20' : 'hover:bg-white/5'
                }`}
                style={{
                  backgroundColor: selected
                    ? 'var(--button-color)'
                    : today
                    ? 'rgba(255, 255, 255, 0.05)'
                    : 'transparent',
                  color: selected ? 'white' : 'var(--text-color)'
                }}
              >
                <span className="text-xs mb-1 opacity-70">{getDayName(date)}</span>
                <span className={`text-lg font-medium ${today && !selected ? 'font-bold text-[var(--button-color)]' : ''}`}>
                  {date.getDate()}
                </span>
                {/* Индикатор количества пар */}
                <div className="flex items-center justify-center mt-1 min-h-[16px]">
                  {lessonsCount > 0 && (
                    <div
                      className="flex items-center justify-center w-[18px] h-[18px] rounded-full text-[10px] font-bold shadow-sm"
                      style={{
                        backgroundColor: selected ? 'white' : 'var(--button-color)',
                        color: selected ? 'var(--button-color)' : 'white'
                      }}
                    >
                      {lessonsCount}
                    </div>
                  )}
                </div>
              </motion.button>
            );
          })}
            </motion.div>
          </AnimatePresence>
        </div>
      </motion.div>

      {/* Schedule content */}
      <div className="flex-grow">
        {loading ? (
          <div className="space-y-4 pb-4">
            {[1, 2, 3].map((i) => (
              <div key={i} className="rounded-2xl p-5 glass shadow-sm">
                <div className="flex justify-between mb-3">
                  <div className="h-6 w-24 bg-gray-200/20 rounded" />
                  <div className="h-6 w-16 bg-gray-200/20 rounded" />
                </div>
                <div className="h-8 w-3/4 bg-gray-200/20 rounded mb-3" />
                <div className="h-4 w-1/2 bg-gray-200/20 rounded mb-4" />
                <div className="flex gap-2">
                  <div className="h-10 flex-1 bg-gray-200/20 rounded-xl" />
                  <div className="h-10 flex-1 bg-gray-200/20 rounded-xl" />
                </div>
              </div>
            ))}
          </div>
        ) : error ? (
          <Alert className="shadow-lg mb-4 bg-red-500/10 border-red-500/20 text-red-500">
            <AlertDescription className="font-medium">
              {error}
            </AlertDescription>
          </Alert>
        ) : schedule.length === 0 ? (
          <motion.div
            {...scheduleSwipeHandlers}
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            className="text-center py-12"
            style={{
              transform: `translateX(${scheduleSwipeOffset}px)`,
              transition: isScheduleSwiping ? 'none' : 'transform 0.3s ease-out'
            }}
          >
            <div className="w-20 h-20 mx-auto mb-4 rounded-full bg-white/5 flex items-center justify-center text-[var(--hint-color)]">
                <Calendar size={40} className="opacity-50" />
            </div>
            <p className="text-lg text-[var(--hint-color)]">
              Нет занятий на этот день
            </p>
          </motion.div>
        ) : (
          <div
            {...scheduleSwipeHandlers}
            style={{
              transform: `translateX(${scheduleSwipeOffset}px)`,
              transition: isScheduleSwiping ? 'none' : 'transform 0.3s ease-out'
            }}
          >
            <div className="space-y-4 pb-4">
            {schedule.map((lesson, index) => {
              const isCurrent = isCurrentLesson(lesson);
              const progress = isCurrent ? getLessonProgress(lesson) : 0;
              const remainingTime = isCurrent ? getRemainingTime(lesson) : '';

              return (
                <motion.div
                  key={index}
                  className={`rounded-2xl p-5 relative overflow-hidden transition-all ${
                      isCurrent 
                        ? 'glass border-[var(--button-color)] shadow-lg shadow-blue-500/10 bg-gradient-to-br from-blue-500/5 to-blue-500/5' 
                        : 'glass shadow-sm'
                  }`}
                >
                  {/* Бейдж стоимости посещения перемещен в строку с типом и статусом */}


                  {/* Прогресс-бар для текущей пары */}
                  {isCurrent && (
                    <div className="absolute top-0 left-0 right-0 h-1 bg-[var(--button-color)]/20">
                      <motion.div
                        className="h-full bg-[var(--button-color)]"
                        initial={{ width: 0 }}
                        animate={{ width: `${progress}%` }}
                        transition={{ duration: 1, ease: "linear" }}
                      />
                    </div>
                  )}

                  {/* Метка "Идёт сейчас" */}
                        {isCurrent && (
                    <div className="flex items-center gap-2 mb-4">
                      <div className="flex items-center gap-1.5 px-3 py-1 rounded-full bg-[var(--button-color)] text-white shadow-lg shadow-blue-500/30">
                        <div className="w-2 h-2 rounded-full bg-white opacity-90" />
                        <span className="text-xs font-bold">Идёт сейчас</span>
                      </div>
                      <span className="text-xs font-medium text-[var(--button-color)]">
                        Осталось {remainingTime}
                      </span>
                    </div>
                  )}

                  {/* Time and Type */}
                  <div className="flex items-center justify-between mb-3">
                    <div className="flex items-center text-[var(--text-color)]">
                        <Clock size={18} className="mr-2 text-[var(--button-color)]" />
                        <span className="font-bold text-lg">{lesson.time}</span>
                    </div>
                    <div className="flex items-center gap-2">
                        {lesson.type && (
                        <span className={`px-2.5 py-1 text-xs font-bold rounded-lg ${getLessonTypeColor(lesson.type)}`}>
                            {getLessonTypeDisplay(lesson.type)}
                        </span>
                        )}
                        {lesson.status && getStatusBadge(lesson.status)}

                        {/* Бейдж стоимости посещения */}
                        {hasAttendanceTracking(lesson) && getAttendancePoints(lesson) && (
                            <motion.div
                            whileHover={{ scale: 1.05 }}
                            whileTap={{ scale: 0.95 }}
                            className="flex items-center gap-1 px-2.5 py-1 rounded-lg bg-[var(--tg-theme-bg-color)]/50 border border-[var(--tg-theme-hint-color)]/20 cursor-pointer hover:bg-[var(--tg-theme-bg-color)] transition-all"
                            onClick={(e) => {
                                e.stopPropagation();
                                setCostInfoData({
                                points: getAttendancePoints(lesson),
                                subject: lesson.subject
                                });
                                setCostInfoModalOpen(true);
                            }}
                            >
                            <span className="text-xs font-bold text-[var(--text-color)]">{getAttendancePoints(lesson)} б.</span>
                            <Info size={12} className="text-[var(--hint-color)]" />
                            </motion.div>
                        )}
                    </div>
                </div>

                {/* Subject */}
                <div className="flex items-start mb-3">
                  <BookOpen size={18} className="mr-3 mt-1 flex-shrink-0 text-[var(--hint-color)]" />
                  <div className="flex-grow">
                    <h3 className="font-bold text-lg leading-tight text-[var(--text-color)]">
                      {lesson.subject || 'Название предмета не указано'}
                    </h3>
                  </div>
                </div>

                {/* Teacher */}
                {lesson.teacher && (
                  <div className="flex items-center mb-2 pl-1">
                    <User size={16} className="mr-3 text-[var(--hint-color)]" />
                    <span className="text-sm text-[var(--hint-color)]">
                      {lesson.teacher}
                    </span>
                  </div>
                )}

                {/* Room and Building */}
                {lesson.room && (
                  <div className="flex items-center mb-4 pl-1">
                    <MapPin size={16} className="mr-3 text-[var(--hint-color)]" />
                    <span className="text-sm text-[var(--hint-color)]">
                      Аудитория {lesson.room}{lesson.building && lesson.building !== 'СДО' && lesson.building !== 'Дистанционно' ? ` (${lesson.building})` : ''}
                    </span>
                  </div>
                )}

                {/* Кнопка "Кто был?" - только если предмет есть в журнале */}
                {hasAttendanceTracking(lesson) && (
                  <motion.button
                    whileHover={{ scale: 1.02 }}
                    whileTap={{ scale: 0.98 }}
                    onClick={() => loadAttendance(lesson)}
                    className="w-full py-3 px-4 rounded-xl flex items-center justify-center font-medium transition-colors bg-[var(--button-color)] text-white shadow-lg shadow-blue-500/20"
                  >
                    <Users size={18} className="mr-2" />
                    Кто был?
                  </motion.button>
                )}
              </motion.div>
            );
            })}
            </div>
          </div>
        )}
      </div>

      {/* Модальное окно со статистикой посещаемости */}
      <AttendanceModal
        isOpen={attendanceModalOpen}
        onClose={() => setAttendanceModalOpen(false)}
        attendanceData={attendanceData}
        loading={attendanceLoading}
        error={attendanceError}
      />

      {/* Модальное окно информации о стоимости посещения */}
      <AnimatePresence>
      {costInfoModalOpen && costInfoData && (
        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          exit={{ opacity: 0 }}
          className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/60 backdrop-blur-sm"
          onClick={() => setCostInfoModalOpen(false)}
        >
          <motion.div
            initial={{ scale: 0.9, opacity: 0 }}
            animate={{ scale: 1, opacity: 1 }}
            exit={{ scale: 0.9, opacity: 0 }}
            className="rounded-2xl shadow-2xl p-6 max-w-sm w-full glass"
            onClick={(e) => e.stopPropagation()}
          >
            <div className="flex justify-between items-center mb-4">
                <h3 className="text-xl font-bold text-[var(--text-color)]">
                Стоимость посещения
                </h3>
                <button onClick={() => setCostInfoModalOpen(false)} className="p-1 rounded-full hover:bg-white/10 text-[var(--hint-color)]">
                    <X size={20} />
                </button>
            </div>
            
            <div className="p-4 rounded-xl bg-[var(--tg-theme-secondary-bg-color)] border border-[var(--tg-theme-hint-color)]/10 mb-6">
                <p className="text-sm leading-relaxed text-[var(--text-color)]">
                За пропуск этой пары вы потеряете <strong className="text-red-400 text-lg">{costInfoData.points}</strong> балла из <strong className="text-[var(--button-color)]">30</strong> максимальных баллов за посещаемость в семестре.
                </p>
            </div>

            <motion.button
              whileHover={{ scale: 1.02 }}
              whileTap={{ scale: 0.98 }}
              onClick={() => setCostInfoModalOpen(false)}
              className="w-full py-3 px-4 rounded-xl font-medium transition-colors bg-[var(--button-color)] text-white shadow-lg shadow-blue-500/20"
            >
              Понятно
            </motion.button>
          </motion.div>
        </motion.div>
      )}
      </AnimatePresence>
    </motion.div>
  );
};

export default ScheduleScreen;
