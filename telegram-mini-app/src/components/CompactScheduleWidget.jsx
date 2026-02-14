import React, { useState, useEffect } from 'react';
import { Calendar, Clock, BookOpen, ChevronRight, Loader, MapPin, User, Users, Info } from 'lucide-react';
import { motion, AnimatePresence } from 'framer-motion';
import apiService from '../services/apiService';
import AttendanceModal from './AttendanceModal';

// 🔧 ТЕСТОВАЯ ДАТА: Раскомментируйте и установите нужную дату для тестирования
// Формат: new Date(год, месяц-1, день)
// ВАЖНО: Месяцы в JS начинаются с 0! (0=январь, 10=ноябрь, 11=декабрь)
// Пример: new Date(2025, 10, 15) = 15 ноября 2025
const TEST_DATE = null; // 11 ноября 2025

const CompactScheduleWidget = ({ initData, onViewFullSchedule, maxHeight = 'auto' }) => {
  const [schedule, setSchedule] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [todayDate, setTodayDate] = useState(new Date());

  // Состояние для модального окна посещаемости
  const [attendanceModalOpen, setAttendanceModalOpen] = useState(false);
  const [attendanceData, setAttendanceData] = useState(null);
  const [attendanceLoading, setAttendanceLoading] = useState(false);
  const [attendanceError, setAttendanceError] = useState('');

  // Состояние для модального окна информации о стоимости
  const [costInfoModalOpen, setCostInfoModalOpen] = useState(false);
  const [costInfoData, setCostInfoData] = useState(null);

  // Кеш количества пар по предметам
  const [subjectLessonCounts, setSubjectLessonCounts] = useState({});

  useEffect(() => {
    loadTodaySchedule();
    loadLessonsCost();
  }, [initData]);

  const loadTodaySchedule = async () => {
    setLoading(true);
    setError('');

    try {
      // Используем тестовую дату если она установлена, иначе сегодняшнюю
      const today = TEST_DATE || new Date();
      setTodayDate(today);

      const year = today.getFullYear();
      const month = today.getMonth() + 1;
      const day = today.getDate();

      const result = await apiService.getSchedule(initData, year, month, day);
      setSchedule(result.lessons || []);
    } catch (err) {
      console.error('Ошибка при загрузке расписания:', err);
      // Не показываем ошибку, просто скрываем виджет
      setSchedule([]);
    } finally {
      setLoading(false);
    }
  };

  // Загрузка стоимости пар для всех предметов группы
  const loadLessonsCost = async () => {
    try {
      const result = await apiService.getLessonsCost(initData);

      if (result && result.lessons_cost) {
        setSubjectLessonCounts(result.lessons_cost);
      }
    } catch (err) {
      // Silently fail - cost data is optional
    }
  };

  // Функция для получения цвета типа занятия
  const getLessonTypeColor = (type) => {
    switch (type) {
      case 'ЛК': return 'bg-blue-100 text-blue-700';
      case 'ПР': return 'bg-green-100 text-green-700';
      case 'ЛАБ': return 'bg-purple-100 text-purple-700';
      case 'Э':
      case 'ЭКЗ': return 'bg-red-100 text-red-700';
      case 'ЗАЧ': return 'bg-orange-100 text-orange-700';
      case 'КП': return 'bg-pink-100 text-pink-700';
      case 'Конс':
      case 'КОНС': return 'bg-yellow-100 text-yellow-700';
      default: return 'bg-gray-100 text-gray-700';
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

  // Функция для получения бейджа статуса посещаемости
  const getStatusBadge = (status) => {
    switch (status) {
      case '+':
        return <span className="px-1.5 py-0.5 text-xs rounded bg-green-100 text-green-700">Был</span>;
      case 'Н':
        return <span className="px-1.5 py-0.5 text-xs rounded bg-red-100 text-red-700">Не был</span>;
      case 'У':
        return <span className="px-1.5 py-0.5 text-xs rounded bg-yellow-100 text-yellow-700">Уваж.</span>;
      default:
        return null;
    }
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
    return Math.max(0, Math.min(100, progress));
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

  // Функция для получения времени до начала пары
  const getTimeUntilStart = (lesson) => {
    const now = new Date();

    // Парсим время начала пары
    const [startTime] = lesson.time.split(' - ');
    const [startHour, startMinute] = startTime.split(':').map(Number);

    const lessonStart = new Date(now);
    lessonStart.setHours(startHour, startMinute, 0, 0);

    const untilStart = lessonStart - now;

    // Переводим в минуты
    const minutes = Math.floor(untilStart / 1000 / 60);
    const hours = Math.floor(minutes / 60);
    const mins = minutes % 60;

    if (hours > 0) {
      return `${hours}ч ${mins}м`;
    } else {
      return `${mins}м`;
    }
  };

  // Функция для поиска текущей или ближайшей предстоящей пары
  const findRelevantLesson = () => {
    const now = new Date();

    // Сначала ищем текущую пару
    for (const lesson of schedule) {
      if (isCurrentLesson(lesson)) {
        return { lesson, status: 'current' };
      }
    }

    // Если текущей пары нет, ищем ближайшую предстоящую
    for (const lesson of schedule) {
      const lessonDate = new Date(lesson.date);
      if (lessonDate.toDateString() !== now.toDateString()) {
        continue;
      }

      const [startTime] = lesson.time.split(' - ');
      const [startHour, startMinute] = startTime.split(':').map(Number);

      const lessonStart = new Date(now);
      lessonStart.setHours(startHour, startMinute, 0, 0);

      if (lessonStart > now) {
        return { lesson, status: 'upcoming' };
      }
    }

    return null;
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

  // Дозагрузка данных для текущего предмета (если его нет в кеше)
  useEffect(() => {
    const loadMissingSubjectCount = async () => {
      const relevantLessonData = schedule.length > 0 ? findRelevantLesson() : null;
      if (!relevantLessonData) return;

      const { lesson } = relevantLessonData;

      // Пропускаем если уже загружено
      if (subjectLessonCounts[lesson.subject]) {
        return;
      }

      try {
        let lessonIndexInDay = 0;
        for (const l of schedule) {
          if (l.uuid === lesson.uuid) break;
          if (l.date === lesson.date && l.type === lesson.type && l.subject === lesson.subject) {
            lessonIndexInDay++;
          }
        }

        const result = await apiService.getLessonAttendance(
          initData,
          lesson.date,
          lesson.time.split(' - ')[0],
          lesson.type,
          lesson.subject,
          lessonIndexInDay
        );

        if (result && result.total_lessons) {
          setSubjectLessonCounts(prev => ({
            ...prev,
            [lesson.subject]: result.total_lessons
          }));
        }
      } catch (err) {
        console.error(`[WIDGET ATTENDANCE] Ошибка для ${lesson.subject}:`, err);
      }
    };

    loadMissingSubjectCount();
  }, [schedule, initData, subjectLessonCounts]);

  // Обновление текущего времени каждую минуту для обновления прогресса
  useEffect(() => {
    const interval = setInterval(() => {
      // Принудительно перерисовываем компонент каждую минуту
      setSchedule(prevSchedule => [...prevSchedule]);
    }, 60000); // Каждую минуту

    return () => clearInterval(interval);
  }, []);

  // Функция для загрузки статистики посещаемости
  const loadAttendance = async (lesson) => {
    setAttendanceModalOpen(true);
    setAttendanceLoading(true);
    setAttendanceError('');
    setAttendanceData(null);

    try {
      // Вычисляем индекс этой пары в дне
      let lessonIndexInDay = 0;
      for (const l of schedule) {
        if (l.uuid === lesson.uuid) {
          break;
        }
        if (l.date === lesson.date && l.type === lesson.type && l.subject === lesson.subject) {
          lessonIndexInDay++;
        }
      }

      const result = await apiService.getLessonAttendance(
        initData,
        lesson.date,
        lesson.time.split(' - ')[0],
        lesson.type,
        lesson.subject,
        lessonIndexInDay
      );

      setAttendanceData(result);

      // Сохраняем количество пар для этого предмета
      if (result && result.total_lessons && lesson.subject) {
        setSubjectLessonCounts(prev => ({
          ...prev,
          [lesson.subject]: result.total_lessons
        }));
      }
    } catch (err) {
      console.error('Ошибка при загрузке статистики посещаемости:', err);
      setAttendanceError(err.message || 'Не удалось загрузить статистику посещаемости');
    } finally {
      setAttendanceLoading(false);
    }
  };

  // Если загружается или есть ошибка, показываем минимальную версию
  if (loading) {
    return (
      <motion.div
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        className="rounded-2xl shadow-sm p-4 mb-4 glass"
        style={{
          borderColor: 'rgba(0,0,0,0.05)'
        }}
      >
        <div className="flex items-center justify-between">
        <div className="flex items-center">
          <Calendar size={20} className="mr-2" style={{color: 'var(--hint-color)'}} />
          <span className="font-medium text-sm" style={{color: 'var(--text-color)'}}>Расписание</span>
        </div>
        <Loader size={16} className="animate-spin" style={{color: 'var(--hint-color)'}} />
      </div>
    </motion.div>
    );
  }

  // Находим релевантную пару (текущую или ближайшую)
  const relevantLessonData = schedule.length > 0 ? findRelevantLesson() : null;

  // Если нет пар на сегодня или нет релевантной пары
  if (schedule.length === 0 || !relevantLessonData) {
    return (
      <motion.div
        whileHover={{ scale: 1.01 }}
        whileTap={{ scale: 0.99 }}
        className="rounded-2xl shadow-sm p-4 mb-4 cursor-pointer glass"
        style={{
          borderColor: 'rgba(0,0,0,0.05)'
        }}
        onClick={onViewFullSchedule}
      >
        <div className="flex items-center justify-between">
          <div className="flex items-center">
            <Calendar size={18} className="mr-2" style={{color: 'var(--hint-color)'}} />
            <span className="text-sm" style={{color: 'var(--hint-color)'}}>
              {schedule.length === 0 ? 'Сегодня пар нет' : 'Все пары на сегодня завершены'}
            </span>
          </div>
          <div className="flex items-center gap-1" style={{color: 'var(--hint-color)'}}>
            <span className="text-xs">Открыть расписание</span>
            <ChevronRight size={16} />
          </div>
        </div>
      </motion.div>
    );
  }

  const { lesson, status } = relevantLessonData;
  const isCurrent = status === 'current';
  const progress = isCurrent ? getLessonProgress(lesson) : 0;
  const timeInfo = isCurrent ? getRemainingTime(lesson) : getTimeUntilStart(lesson);

  // Показываем одну релевантную пару
  return (
    <motion.div
      className={`rounded-2xl shadow-sm p-4 pb-3 mb-4 relative overflow-hidden transition-all ${
        isCurrent 
          ? 'glass border-[var(--button-color)] shadow-lg shadow-blue-500/10 bg-gradient-to-br from-blue-500/5 to-blue-500/5' 
          : 'glass shadow-sm'
      }`}
      style={{
        borderColor: isCurrent ? 'var(--button-color)' : undefined,
        borderWidth: isCurrent ? '2px' : '1px'
      }}
    >
      {/* Бейдж стоимости посещения */}
      {hasAttendanceTracking(lesson) && getAttendancePoints(lesson) && (
        <motion.div
          whileHover={{ scale: 1.05 }}
          whileTap={{ scale: 0.95 }}
          className="absolute bottom-14 right-4 flex items-center gap-1 px-2 py-1 rounded-lg bg-[var(--tg-theme-bg-color)]/50 border border-[var(--tg-theme-hint-color)]/20 cursor-pointer hover:bg-[var(--tg-theme-bg-color)] transition-all z-10"
          onClick={() => {
            setCostInfoData({
              points: getAttendancePoints(lesson),
              subject: lesson.subject
            });
            setCostInfoModalOpen(true);
          }}
        >
          <span className="text-xs font-bold text-[var(--text-color)]">{getAttendancePoints(lesson)}</span>
          <Info size={12} className="text-[var(--hint-color)]" />
        </motion.div>
      )}

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

      {/* Статус и время */}
      <div className="flex items-center justify-between mb-3 pt-1">
        <div className="flex items-center gap-2">
          {isCurrent ? (
            <div className="flex items-center gap-1.5 px-2 py-1 rounded-full bg-[var(--button-color)]">
              <motion.div 
                animate={{ opacity: [1, 0.5, 1] }}
                transition={{ duration: 1.5, repeat: Infinity }}
                className="w-2 h-2 rounded-full bg-white" 
              />
              <span className="text-xs font-bold text-white">Идёт сейчас</span>
            </div>
          ) : (
            <div className="flex items-center gap-1.5 px-2 py-1 rounded-full bg-gray-100">
              <Clock size={12} className="text-gray-500" />
              <span className="text-xs font-medium text-gray-500">Следующая пара</span>
            </div>
          )}
        </div>
        <span className="text-sm font-bold" style={{color: 'var(--button-color)'}}>
          {isCurrent ? `Осталось ${timeInfo}` : `Через ${timeInfo}`}
        </span>
      </div>

      {/* Основная информация */}
      <div className="mb-4">
        <div className="flex items-center gap-2 mb-2 flex-wrap">
          <Clock size={16} style={{color: 'var(--hint-color)'}} />
          <span className="font-medium" style={{color: 'var(--text-color)'}}>{lesson.time}</span>
          {lesson.type && (
            <span className={`px-2 py-0.5 text-xs font-bold rounded-md ${getLessonTypeColor(lesson.type)}`}>
              {getLessonTypeDisplay(lesson.type)}
            </span>
          )}
          {lesson.status && getStatusBadge(lesson.status)}
        </div>

        <div className="flex items-start gap-3 mb-2">
          <BookOpen size={18} className="mt-0.5 flex-shrink-0" style={{color: 'var(--hint-color)'}} />
          <div className="flex-grow">
            <div className="font-bold text-lg leading-tight" style={{color: 'var(--text-color)'}}>
              {lesson.subject || 'Название предмета не указано'}
            </div>
          </div>
        </div>

        {lesson.teacher && (
          <div className="flex items-center gap-2 mb-1 ml-1">
            <User size={14} style={{color: 'var(--hint-color)'}} />
            <span className="text-sm" style={{color: 'var(--hint-color)'}}>{lesson.teacher}</span>
          </div>
        )}

        {lesson.room && (
          <div className="flex items-center gap-2 ml-1">
            <MapPin size={14} style={{color: 'var(--hint-color)'}} />
            <span className="text-sm" style={{color: 'var(--hint-color)'}}>Аудитория {lesson.room}{lesson.building && lesson.building !== 'СДО' && lesson.building !== 'Дистанционно' ? ` (${lesson.building})` : ''}</span>
          </div>
        )}
      </div>

      {/* Кнопки */}
      <div className="flex gap-2 mt-2">
        {hasAttendanceTracking(lesson) && (
          <motion.button
            whileHover={{ scale: 1.02 }}
            whileTap={{ scale: 0.98 }}
            onClick={() => loadAttendance(lesson)}
            className="flex-1 py-2.5 px-3 rounded-xl font-medium transition-colors flex items-center justify-center gap-2 text-sm"
            style={{
              backgroundColor: 'var(--button-color)',
              color: 'white'
            }}
          >
            <Users size={16} />
            Кто был?
          </motion.button>
        )}
        <motion.button
          whileHover={{ scale: 1.02 }}
          whileTap={{ scale: 0.98 }}
          onClick={onViewFullSchedule}
          className="flex-1 py-2.5 px-3 rounded-xl font-medium transition-colors flex items-center justify-center gap-2 text-sm bg-[var(--tg-theme-bg-color)] border border-[var(--tg-theme-hint-color)]/10"
          style={{
            color: 'var(--text-color)'
          }}
        >
          <Calendar size={16} />
          Расписание
        </motion.button>
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
            className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/50 backdrop-blur-sm"
            onClick={() => setCostInfoModalOpen(false)}
            >
            <motion.div
                initial={{ scale: 0.9, opacity: 0 }}
                animate={{ scale: 1, opacity: 1 }}
                exit={{ scale: 0.9, opacity: 0 }}
                className="rounded-2xl shadow-xl p-6 max-w-sm w-full bg-white"
                style={{
                backgroundColor: 'var(--secondary-bg-color)'
                }}
                onClick={(e) => e.stopPropagation()}
            >
                <h3 className="text-lg font-bold mb-3" style={{ color: 'var(--text-color)' }}>
                Стоимость посещения
                </h3>
                <p className="text-sm mb-6 leading-relaxed" style={{ color: 'var(--text-color)' }}>
                За пропуск этой пары вы потеряете <strong className="text-red-500">{costInfoData.points}</strong> балла из <strong>30</strong> максимальных баллов за посещаемость в семестре.
                </p>
                <button
                onClick={() => setCostInfoModalOpen(false)}
                className="w-full py-3 px-4 rounded-xl font-bold transition-colors"
                style={{
                    backgroundColor: 'var(--button-color)',
                    color: 'white'
                }}
                >
                Понятно
                </button>
            </motion.div>
            </motion.div>
        )}
      </AnimatePresence>
    </motion.div>
  );
};

export default CompactScheduleWidget;
