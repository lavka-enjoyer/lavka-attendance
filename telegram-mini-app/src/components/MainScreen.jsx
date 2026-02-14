import React, { useState, useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { Alert, AlertDescription } from './ui/alert';
import apiService from '../services/apiService';
import { ShieldCheck, CalendarDays, QrCode, Users as UsersIcon, Building2, Info, TrendingUp, ChevronRight, MapPin, CheckCircle2, XCircle, LogOut, LogIn } from 'lucide-react';
import CompactScheduleWidget from './CompactScheduleWidget';

// Modern Toggle Switch with Framer Motion
const ToggleSwitch = ({ checked, onChange, disabled = false }) => {
  return (
      <div
          className={`relative w-12 h-7 cursor-pointer rounded-full p-1 transition-colors duration-300 ${
            checked ? 'bg-[var(--button-color)]' : 'bg-white/20'
          } ${disabled ? 'opacity-50 cursor-not-allowed' : ''}`}
          onClick={() => !disabled && onChange && onChange(!checked)}
      >
        <motion.div
            className="w-5 h-5 bg-white rounded-full shadow-sm"
            initial={false}
            animate={{ x: checked ? 20 : 0 }}
            transition={{ type: "spring", stiffness: 700, damping: 30 }}
        />
      </div>
  );
};

const MainScreen = ({ initData, userData, onMarkMultiple, onUpdateUserData, onViewPoints, onShowAdminPanel, onViewSchedule, onViewGroupStatus }) => {
  const [allowOthersToMark, setAllowOthersToMark] = useState(userData?.allowConfirm ?? true);
  const [scanResult, setScanResult] = useState('');
  const [isUpdatingToggle, setIsUpdatingToggle] = useState(false);
  const [isMarkingInProgress, setIsMarkingInProgress] = useState(false);
  const [markingError, setMarkingError] = useState('');
  const [universityStatus, setUniversityStatus] = useState(null);
  const [showStatusDetails, setShowStatusDetails] = useState(false);

  // Проверка наличия прав администратора
  const isAdmin = userData && userData.admin_lvl > 0;

  // Sync state with user data on load
  useEffect(() => {
    if (userData && userData.allowConfirm !== undefined) {
      setAllowOthersToMark(userData.allowConfirm);
    }
  }, [userData]);

  // Загрузка статуса нахождения в университете
  useEffect(() => {
    const fetchUniversityStatus = async () => {
      try {
        const status = await apiService.getUniversityStatus(initData);
        setUniversityStatus(status);
      } catch (error) {
        setUniversityStatus({
          is_inside_university: false,
          error: error.message
        });
      }
    };

    if (initData) {
      fetchUniversityStatus();
    }
  }, [initData]);

  // Обновление handleScanQR для обработки ошибок подписки
  const handleScanQR = () => {
    setIsMarkingInProgress(true);
    setMarkingError('');
    setScanResult('');

    if (window.Telegram?.WebApp) {
      // Add an event listener for the scan popup closing
      const handlePopupClosed = () => {
        setIsMarkingInProgress(false);
        // Remove the event listener after it's triggered
        window.Telegram.WebApp.offEvent('scanQrPopupClosed', handlePopupClosed);
      };

      // Listen for the popup being closed
      window.Telegram.WebApp.onEvent('scanQrPopupClosed', handlePopupClosed);

      window.Telegram.WebApp.showScanQrPopup(
          {
            text: 'Отсканируйте QR-код для отметки'
          },
          async (text) => {
            // Remove the close event listener since we got a result
            window.Telegram.WebApp.offEvent('scanQrPopupClosed', handlePopupClosed);

            try {
              if (!text) {
                setMarkingError('Ошибка сканирования QR');
                setIsMarkingInProgress(false);
                return true;
              }

              const response = await apiService.sendApprove(initData, text);

              if (response.result) {
                // Check for expired QR
                if (response.result.group === "none" && response.result.strok === "none") {
                  setMarkingError('Срок действия QR кода истек. Пожалуйста, отсканируйте снова.');
                } else {
                  // Successful marking
                  setScanResult(response.result.strok || 'Отметка успешно отправлена');
                }
              } else {
                setMarkingError('Неожиданный формат ответа от сервера');
              }
            } catch (err) {
              setMarkingError(err.message || 'Ошибка при отправке отметки');
            } finally {
              setIsMarkingInProgress(false);
            }
            return true;
          }
      );
    } else {
      setMarkingError('Функция сканирования QR недоступна');
      setIsMarkingInProgress(false);
    }
  };

  const handleAllowOthersToggle = async () => {
    setIsUpdatingToggle(true);

    try {
      const result = await apiService.updateAllowConfirm(initData, !allowOthersToMark);

      if (result.status === "Успешно") {
        setAllowOthersToMark(!allowOthersToMark);

        // Обновляем userData в родительском компоненте
        if (onUpdateUserData) {
          onUpdateUserData({
            ...userData,
            allowConfirm: !allowOthersToMark
          });
        }
      } else {
        // Show error message if failed
        setMarkingError('Не удалось обновить настройку');
      }
    } catch (err) {
      setMarkingError('Ошибка при обновлении настройки');
    } finally {
      setIsUpdatingToggle(false);
    }
  };


  // Функция для haptic feedback
  const triggerHaptic = (style = 'light') => {
    if (window.Telegram?.WebApp?.HapticFeedback) {
      window.Telegram.WebApp.HapticFeedback.impactOccurred(style);
    }
  };

  // Обработчик для кнопки "Отметить несколько"
  const handleMarkMultipleWithHaptic = () => {
    triggerHaptic('medium');
    onMarkMultiple();
  };

  const containerVariants = {
    hidden: { opacity: 1 },
    visible: {
      opacity: 1,
      transition: {
        staggerChildren: 0.1
      }
    }
  };

  const itemVariants = {
    hidden: { opacity: 1 },
    visible: {
      opacity: 1,
      transition: {
        duration: 0
      }
    }
  };

  return (
      <motion.div 
        className="p-4 w-full max-w-md mx-auto min-h-screen flex flex-col gap-4"
        variants={containerVariants}
        initial="hidden"
        animate="visible"
      >
        {/* Header Section */}
        <motion.div variants={itemVariants} className="flex justify-between items-start">
            <div>
                <h1 className="text-2xl font-bold tracking-tight text-[var(--text-color)]">
                    Привет, {userData?.FIO?.split(' ')[0] || 'Студент'}! 👋
                </h1>
                <p className="text-sm opacity-70 text-[var(--hint-color)]">
                    {userData?.group || 'Группа не определена'}
                </p>
            </div>
            {isAdmin && (
                <motion.button
                    whileTap={{ scale: 0.95 }}
                    onClick={onShowAdminPanel}
                    className="p-2.5 rounded-xl glass text-[var(--button-color)] shadow-lg shadow-blue-500/10"
                >
                    <ShieldCheck size={20} />
                </motion.button>
            )}
        </motion.div>

        {/* University Status Card */}
        <motion.div 
            variants={itemVariants}
            className={`rounded-2xl p-4 shadow-lg border relative overflow-hidden cursor-pointer transition-all duration-300 ${
                universityStatus?.is_inside_university 
                    ? 'bg-green-500/10 border-green-500/20' 
                    : 'glass border-white/10'
            }`}
            onClick={() => universityStatus && setShowStatusDetails(true)}
            whileHover={{ scale: 1.02 }}
            whileTap={{ scale: 0.98 }}
        >
            <div className="flex items-center justify-between relative z-10">
                <div className="flex items-center gap-3">
                    <div className={`p-2.5 rounded-xl ${
                      !universityStatus 
                        ? 'bg-gray-200/20' 
                        : universityStatus.is_inside_university 
                          ? 'bg-green-500 text-white shadow-lg shadow-green-500/30' 
                          : 'bg-white/10 text-[var(--hint-color)]'
                    }`}>
                        {!universityStatus ? (
                            <div className="w-5 h-5" />
                        ) : (
                            <MapPin size={20} />
                        )}
                    </div>
                    <div>
                        <p className="text-xs font-medium opacity-70 text-[var(--hint-color)]">Статус</p>
                        {!universityStatus ? (
                          <div className="h-5 w-32 bg-gray-200/20 rounded mt-1" />
                        ) : (
                            <p className={`font-semibold ${
                                universityStatus.is_inside_university ? 'text-green-500' : 'text-[var(--text-color)]'
                            }`}>
                                {universityStatus.is_inside_university ? 'Вы в университете' : 'Вы не в университете'}
                            </p>
                        )}
                    </div>
                </div>
                <ChevronRight size={20} className="opacity-40 text-[var(--hint-color)]" />
            </div>
        </motion.div>

        {/* Quick Actions Grid */}
        <motion.div variants={itemVariants} className="grid grid-cols-2 gap-3">
            <motion.button
                whileHover={{ scale: 1.02 }}
                whileTap={{ scale: 0.98 }}
                onClick={onViewPoints}
                className="p-4 rounded-2xl shadow-lg flex flex-col items-center justify-center gap-2 glass hover:bg-white/5 transition-colors"
            >
                <div className="p-3 rounded-full bg-blue-500/10 text-blue-500 mb-1">
                    <TrendingUp size={24} />
                </div>
                <span className="font-medium text-sm text-[var(--text-color)]">БРС</span>
            </motion.button>

            <motion.button
                whileHover={{ scale: 1.02 }}
                whileTap={{ scale: 0.98 }}
                onClick={onViewGroupStatus}
                className="p-4 rounded-2xl shadow-lg flex flex-col items-center justify-center gap-2 glass hover:bg-white/5 transition-colors"
            >
                <div className="p-3 rounded-full bg-purple-500/10 text-purple-500 mb-1">
                    <UsersIcon size={24} />
                </div>
                <span className="font-medium text-sm text-[var(--text-color)]">Кто в унике?</span>
            </motion.button>
        </motion.div>

        {/* Schedule Widget */}
        <motion.div variants={itemVariants} className="flex-grow min-h-[200px]">
             <CompactScheduleWidget
                initData={initData}
                onViewFullSchedule={onViewSchedule}
                maxHeight="100%"
             />
        </motion.div>

        {/* Main Action Button */}
        <motion.div variants={itemVariants} className="mt-auto">
            <motion.button
                whileHover={{ scale: 1.02 }}
                whileTap={{ scale: 0.98 }}
                className="w-full rounded-2xl shadow-xl shadow-blue-500/20 p-4 flex items-center justify-center relative overflow-hidden group bg-[var(--button-color)] text-white"
                onClick={handleMarkMultipleWithHaptic}
            >
                <div className="absolute inset-0 bg-white/20 translate-y-full group-hover:translate-y-0 transition-transform duration-300" />
                <QrCode className="w-6 h-6 mr-3" />
                <span className="text-lg font-bold">Отметить посещение</span>
            </motion.button>
        </motion.div>

        {/* Toggle Section */}
        <motion.div 
            variants={itemVariants} 
            className="glass rounded-2xl p-4 shadow-lg flex items-center justify-between"
        >
            <div>
                <p className="font-medium text-sm text-[var(--text-color)]">Разрешить меня отмечать</p>
                <p className="text-xs opacity-60 text-[var(--hint-color)]">Выключайте, если отсутствуете официально</p>
            </div>
            <ToggleSwitch
                checked={allowOthersToMark}
                onChange={handleAllowOthersToggle}
                disabled={isUpdatingToggle}
            />
        </motion.div>

        {/* Alerts */}
        <AnimatePresence>
            {scanResult && (
                <motion.div 
                    initial={{ opacity: 0, y: 20 }}
                    animate={{ opacity: 1, y: 0 }}
                    exit={{ opacity: 0, y: 20 }}
                    className="fixed bottom-24 left-4 right-4 z-50"
                >
                    <div className="p-4 rounded-2xl bg-green-500/90 backdrop-blur-md text-white shadow-xl flex items-center">
                        <CheckCircle2 className="h-6 w-6 mr-3" />
                        <span className="font-medium">{scanResult}</span>
                    </div>
                </motion.div>
            )}

            {markingError && (
                <motion.div 
                    initial={{ opacity: 0, y: 20 }}
                    animate={{ opacity: 1, y: 0 }}
                    exit={{ opacity: 0, y: 20 }}
                    className="fixed bottom-24 left-4 right-4 z-50"
                >
                    <div className="p-4 rounded-2xl bg-red-500/90 backdrop-blur-md text-white shadow-xl flex items-center">
                        <XCircle className="h-6 w-6 mr-3" />
                        <span className="font-medium">{markingError}</span>
                    </div>
                </motion.div>
            )}
        </AnimatePresence>

        {/* Status Details Modal */}
        <AnimatePresence>
            {showStatusDetails && universityStatus && (
                <motion.div
                    initial={{ opacity: 0 }}
                    animate={{ opacity: 1 }}
                    exit={{ opacity: 0 }}
                    className="fixed inset-0 bg-black/60 backdrop-blur-md flex items-center justify-center z-50 p-4"
                    onClick={() => setShowStatusDetails(false)}
                >
                    <motion.div
                        initial={{ scale: 0.9, opacity: 0, y: 20 }}
                        animate={{ scale: 1, opacity: 1, y: 0 }}
                        exit={{ scale: 0.9, opacity: 0, y: 20 }}
                        className="rounded-3xl shadow-2xl p-6 max-w-sm w-full max-h-[80vh] overflow-y-auto glass border border-white/10"
                        onClick={(e) => e.stopPropagation()}
                    >
                        <div className="flex justify-between items-center mb-6">
                            <h3 className="text-xl font-bold text-[var(--text-color)]">История проходов</h3>
                            <button 
                                onClick={() => setShowStatusDetails(false)} 
                                className="p-2 rounded-full hover:bg-white/10 transition-colors text-[var(--hint-color)]"
                            >
                                <XCircle size={24} />
                            </button>
                        </div>

                        <div className="space-y-4">
                            {/* Текущий статус */}
                            <div className={`p-4 rounded-2xl border ${
                                universityStatus.is_inside_university 
                                    ? 'bg-green-500/10 border-green-500/20' 
                                    : 'bg-white/5 border-white/10'
                            }`}>
                                <div className="flex items-center gap-3 mb-2">
                                    <div className={`p-2 rounded-xl ${
                                        universityStatus.is_inside_university ? 'bg-green-500 text-white' : 'bg-white/10 text-[var(--hint-color)]'
                                    }`}>
                                        <Building2 size={20} />
                                    </div>
                                    <div>
                                        <span className="text-sm font-medium text-[var(--text-color)] block">
                                            Статус
                                        </span>
                                        <strong className={universityStatus.is_inside_university ? 'text-green-500' : 'text-[var(--hint-color)]'}>
                                            {universityStatus.is_inside_university ? 'В университете' : 'Не в университете'}
                                        </strong>
                                    </div>
                                </div>
                                {universityStatus.last_event_time && (
                                    <div className="text-xs text-[var(--hint-color)] mt-2 pl-1">
                                        Последнее событие: {universityStatus.last_event_time}
                                    </div>
                                )}
                            </div>

                            {/* Лог всех событий */}
                            <div className="space-y-3">
                                <h4 className="text-sm font-medium text-[var(--hint-color)] uppercase tracking-wider ml-1">События за сегодня</h4>
                                {universityStatus.events && universityStatus.events.length > 0 ? (
                                    universityStatus.events.map((event, index) => {
                                        const fromName = event.access_point_from?.access_point_name || 'N/A';
                                        const toName = event.access_point_to?.access_point_name || 'N/A';
                                        const isEntry = toName === "Неконтролируемая территория"; // Logic might be reversed depending on API, assuming standard logic here or keeping as is

                                        return (
                                            <motion.div
                                                key={event.event_uuid || index}
                                                initial={{ opacity: 0, x: -10 }}
                                                animate={{ opacity: 1, x: 0 }}
                                                transition={{ delay: index * 0.05 }}
                                                className="p-4 rounded-2xl glass border border-white/5 relative overflow-hidden"
                                            >
                                                <div className={`absolute left-0 top-0 bottom-0 w-1 ${isEntry ? 'bg-green-500' : 'bg-red-500'}`} />
                                                
                                                <div className="flex items-center justify-between mb-2 pl-2">
                                                    <span className="font-bold text-[var(--text-color)] text-lg">
                                                        {event.time || 'N/A'}
                                                    </span>
                                                    <span className={`px-2.5 py-1 rounded-lg text-xs font-bold flex items-center gap-1 ${
                                                        isEntry 
                                                            ? 'bg-green-500/20 text-green-500' 
                                                            : 'bg-red-500/20 text-red-500'
                                                    }`}>
                                                        {isEntry ? <LogIn size={12} /> : <LogOut size={12} />}
                                                        {isEntry ? 'ВХОД' : 'ВЫХОД'}
                                                    </span>
                                                </div>
                                                
                                                <div className="text-sm text-[var(--hint-color)] pl-2 space-y-1">
                                                    <div className="flex items-center gap-2">
                                                        <div className="w-1.5 h-1.5 rounded-full bg-[var(--hint-color)] opacity-50" />
                                                        <span className="truncate">{fromName}</span>
                                                    </div>
                                                    <div className="flex items-center gap-2">
                                                        <div className="w-1.5 h-1.5 rounded-full bg-[var(--button-color)]" />
                                                        <span className="truncate text-[var(--text-color)]">{toName}</span>
                                                    </div>
                                                </div>
                                            </motion.div>
                                        );
                                    })
                                ) : (
                                    <div className="text-center p-8 rounded-2xl glass border border-white/5 text-[var(--hint-color)]">
                                        <CalendarDays size={32} className="mx-auto mb-3 opacity-30" />
                                        <p>Нет данных о проходах за сегодня</p>
                                    </div>
                                )}
                            </div>
                        </div>
                    </motion.div>
                </motion.div>
            )}
        </AnimatePresence>
      </motion.div>
  );
};

export default MainScreen;