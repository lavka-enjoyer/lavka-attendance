import React, { useState, useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { AlertTriangle, ChevronDown, ChevronUp, ArrowLeft, TrendingUp, Loader2, RefreshCw, Award, BookOpen } from 'lucide-react';
import pointsService from '../services/pointsService';

// Компонент прогресс-бара с анимацией
const ProgressBar = ({ value, max, label, color = 'var(--button-color)' }) => {
    const percentage = Math.min(100, (value / max) * 100);

    return (
        <div className="mb-4">
            <div className="flex justify-between mb-1">
                <span className="text-sm font-medium text-[var(--text-color)]">{label}</span>
                <span className="text-sm font-medium text-[var(--text-color)]">{value}/{max}</span>
            </div>
            <div className="h-2 w-full bg-black/5 rounded-full overflow-hidden">
                <motion.div
                    className="h-full rounded-full"
                    initial={{ width: 0 }}
                    animate={{ width: `${percentage}%` }}
                    transition={{ duration: 1, ease: "easeOut" }}
                    style={{ backgroundColor: color }}
                />
            </div>
        </div>
    );
};

// Компонент для статуса автомата с иконкой
const AutoPassStatus = ({ hasAutoPass }) => {
    return (
        <motion.div
            className={`mt-3 flex items-center px-3 py-2 rounded-xl inline-flex border ${
                hasAutoPass 
                ? 'bg-green-500/10 text-green-600 border-green-500/20' 
                : 'bg-red-500/10 text-red-600 border-red-500/20'
            }`}
        >
            {hasAutoPass ? (
                <TrendingUp size={16} className="mr-2" />
            ) : (
                <AlertTriangle size={16} className="mr-2" />
            )}
            <span className="font-bold text-sm">
                {hasAutoPass ? 'Автомат есть' : 'Автомата нет'}
            </span>
        </motion.div>
    );
};

// Компонент карточки дисциплины
const SubjectCard = ({ subject, index }) => {
    const [expanded, setExpanded] = useState(false);
    const totalPoints = subject.fields["Всего баллов (Макс. 100)"];
    const hasAutoPass = totalPoints >= 40;

    // Определяем цвет и градиент карточки на основе общего балла и наличия автомата
    const getCardStyles = () => {
        if (hasAutoPass) {
            return {
                borderColor: '#22c55e',
                pointsColor: '#22c55e',
                bgClass: 'bg-gradient-to-br from-green-500/5 to-green-500/5'
            };
        }
        if (totalPoints >= 85) {
            return {
                borderColor: '#22c55e',
                pointsColor: '#22c55e',
                bgClass: 'bg-gradient-to-br from-green-500/5 to-green-500/5'
            };
        }
        if (totalPoints >= 70) {
            return {
                borderColor: '#3b82f6',
                pointsColor: '#3b82f6',
                bgClass: 'bg-gradient-to-br from-blue-500/5 to-blue-500/5'
            };
        }
        if (totalPoints >= 50) {
            return {
                borderColor: '#eab308',
                pointsColor: '#eab308',
                bgClass: 'bg-gradient-to-br from-yellow-500/5 to-yellow-500/5'
            };
        }
        return {
            borderColor: '#ef4444',
            pointsColor: '#ef4444',
            bgClass: 'bg-gradient-to-br from-red-500/5 to-red-500/5'
        };
    };

    const styles = getCardStyles();

    return (
        <motion.div
            layout
            className={`glass rounded-2xl p-5 mb-4 border shadow-sm hover:shadow-md transition-all ${styles.bgClass}`}
            style={{ borderColor: styles.borderColor }}
        >
            {/* Основная информация: предмет и общие баллы */}
            <div className="flex justify-between items-start gap-4">
                <div className="flex items-start gap-3">
                    <div 
                        className="p-2 rounded-xl mt-1 border"
                        style={{ 
                            backgroundColor: styles.pointsColor + '15',
                            borderColor: styles.pointsColor + '30'
                        }}
                    >
                        <BookOpen size={20} style={{ color: styles.pointsColor }} />
                    </div>
                    <div>
                        <h3 className="text-lg font-bold text-[var(--text-color)] leading-tight mb-1">
                            {subject.Дисциплина}
                        </h3>
                        <div className="flex items-center gap-2">
                            <span className="text-xs font-medium text-[var(--hint-color)]">Всего баллов:</span>
                            <span
                                className="text-xl font-bold"
                                style={{ color: styles.pointsColor }}
                            >
                                {totalPoints}
                            </span>
                        </div>
                    </div>
                </div>
            </div>

            {/* Индикатор автомата */}
            <div className="flex justify-between items-center mt-2">
                <AutoPassStatus hasAutoPass={hasAutoPass} />
                
                <motion.button
                    whileHover={{ scale: 1.05 }}
                    whileTap={{ scale: 0.95 }}
                    className="mt-3 text-sm px-4 py-2 rounded-xl bg-[var(--button-color)] text-white shadow-lg shadow-blue-500/20 flex items-center font-medium"
                    onClick={() => setExpanded(!expanded)}
                >
                    {expanded ? 'Скрыть' : 'Подробнее'}
                    <motion.div
                        animate={{ rotate: expanded ? 180 : 0 }}
                        transition={{ duration: 0.2 }}
                        className="ml-2"
                    >
                        <ChevronDown size={16} />
                    </motion.div>
                </motion.button>
            </div>

            {/* Расширенное представление с детализацией баллов */}
            <AnimatePresence>
                {expanded && (
                    <motion.div
                        initial={{ height: 0, opacity: 0 }}
                        animate={{ height: 'auto', opacity: 1 }}
                        exit={{ height: 0, opacity: 0 }}
                        transition={{ duration: 0.3, ease: "easeInOut" }}
                        className="overflow-hidden"
                    >
                        <div className="pt-4 mt-4 border-t border-black/5">
                            {Object.entries(subject.fields).map(([key, value]) => {
                                if (key === "Всего баллов (Макс. 100)") return null;
                                return (
                                    <ProgressBar
                                        key={key}
                                        label={key}
                                        value={value.now}
                                        max={value.max}
                                        color={styles.borderColor}
                                    />
                                );
                            })}
                        </div>
                    </motion.div>
                )}
            </AnimatePresence>
        </motion.div>
    );
};

// Компонент отображения счетчика автоматов
const AutoPassCounter = ({ count, total }) => {
    const percentage = Math.round((count / total) * 100) || 0;

    return (
        <motion.div
            className="mb-6 p-5 rounded-2xl shadow-sm glass border border-[var(--button-color)] bg-gradient-to-br from-blue-500/5 to-blue-500/5"
        >
            <div className="flex justify-between items-center mb-3">
                <div className="flex items-center gap-3">
                    <div className="p-2 rounded-xl bg-[var(--button-color)] text-white shadow-lg shadow-blue-500/30">
                        <Award size={24} />
                    </div>
                    <div>
                        <p className="font-bold text-[var(--text-color)]">
                            Автоматов
                        </p>
                        <p className="text-xs text-[var(--hint-color)]">
                            Прогноз на семестр
                        </p>
                    </div>
                </div>
                <div className="text-right">
                    <p className="font-bold text-2xl text-[var(--button-color)]">
                        {count} <span className="text-sm font-normal text-[var(--text-color)]">/ {total}</span>
                    </p>
                </div>
            </div>

            <div className="h-3 w-full bg-black/5 rounded-full overflow-hidden relative">
                <motion.div
                    className="h-full rounded-full bg-[var(--button-color)]"
                    initial={{ width: 0 }}
                    animate={{ width: `${percentage}%` }}
                    transition={{ duration: 1, delay: 0.2 }}
                />
            </div>
            <p className="text-right text-xs mt-1.5 font-bold text-[var(--button-color)]">
                {percentage}% получено
            </p>
        </motion.div>
    );
};

// Анимированный компонент загрузки
const LoadingSpinner = () => {
    return (
        <div className="flex flex-col items-center justify-center h-64">
            <motion.div
                animate={{ rotate: 360 }}
                transition={{ duration: 1, repeat: Infinity, ease: "linear" }}
                className="text-[var(--button-color)] mb-4"
            >
                <Loader2 size={48} />
            </motion.div>
            <p className="text-[var(--text-color)] font-medium">Загрузка баллов...</p>
        </div>
    );
};

const PointsScreen = ({ initData, onBack, onApiError }) => {
    const [points, setPoints] = useState([]);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState(null);

    useEffect(() => {
        const fetchPoints = async () => {
            try {
                setLoading(true);
                const data = await pointsService.getPoints(initData);
                setPoints(data);
            } catch (err) {
                console.error("Error fetching points:", err);

                const errorStr = String(err);
                if (errorStr.includes("SUBSCRIPTION_ERROR")) {
                    if (onApiError && onApiError(err)) {
                        return;
                    }
                }

                if (errorStr.includes("Прокси не хватает. Оформи подписку")) {
                    if (onApiError && onApiError(new Error("SUBSCRIPTION_ERROR: Прокси не хватает. Оформите подписку для просмотра баллов"))) {
                        return;
                    }
                }

                setError(err.message || 'Не удалось загрузить данные по баллам');
            } finally {
                setLoading(false);
            }
        };

        fetchPoints();
    }, [initData, onApiError]);

    // Подсчитываем количество предметов с автоматом
    const autoPassCount = points.filter(subject =>
        subject.fields["Всего баллов (Макс. 100)"] >= 40
    ).length;

    // Для отображения во время загрузки
    if (loading) {
        return (
            <div className="p-4 w-full max-w-md mx-auto min-h-screen flex flex-col bg-[var(--bg-color)]">
                <div className="flex items-center mb-6 py-2">
                    <button className="mr-3 p-2 rounded-full bg-black/5 text-[var(--text-color)]">
                        <ArrowLeft size={20} />
                    </button>
                    <h1 className="text-xl font-bold text-[var(--text-color)]">Мои баллы (БРС)</h1>
                </div>
                <LoadingSpinner />
            </div>
        );
    }

    // Для отображения ошибки
    if (error) {
        return (
            <div className="p-4 w-full max-w-md mx-auto min-h-screen flex flex-col justify-center items-center bg-[var(--bg-color)]">
                <motion.div
                    initial={{ scale: 0.9, opacity: 0 }}
                    animate={{ scale: 1, opacity: 1 }}
                    className="glass rounded-2xl shadow-lg p-8 w-full flex flex-col items-center border border-red-500/20 bg-gradient-to-br from-red-500/5 to-red-500/5"
                >
                    <div className="mb-6 p-4 rounded-full bg-red-500/10 text-red-500">
                        <AlertTriangle size={48} />
                    </div>

                    <h2 className="text-xl font-bold text-center mb-4 text-[var(--text-color)]">
                        Ошибка загрузки
                    </h2>

                    <p className="text-center mb-8 text-[var(--hint-color)]">
                        {error}
                    </p>

                    <motion.button
                        whileHover={{ scale: 1.02 }}
                        whileTap={{ scale: 0.98 }}
                        className="w-full rounded-xl shadow-lg p-3.5 flex items-center justify-center mb-3 bg-[var(--button-color)] text-white font-medium"
                        onClick={() => window.location.reload()}
                    >
                        <RefreshCw size={18} className="mr-2" />
                        Попробовать снова
                    </motion.button>

                    <motion.button
                        whileHover={{ scale: 1.02 }}
                        whileTap={{ scale: 0.98 }}
                        className="w-full rounded-xl p-3.5 flex items-center justify-center text-[var(--text-color)] hover:bg-black/5 transition-colors"
                        onClick={onBack}
                    >
                        Вернуться назад
                    </motion.button>
                </motion.div>
            </div>
        );
    }

    return (
        <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            className="p-4 w-full max-w-md mx-auto min-h-screen flex flex-col bg-[var(--bg-color)]"
        >
            {/* Заголовок с кнопкой назад */}
            <div className="flex items-center mb-6 sticky top-0 z-10 py-2 bg-[var(--bg-color)]/80 backdrop-blur-md -mx-4 px-4">
                <motion.button
                    whileHover={{ scale: 1.1 }}
                    whileTap={{ scale: 0.9 }}
                    className="mr-3 p-2 rounded-full hover:bg-black/5 transition-colors text-[var(--text-color)]"
                    onClick={onBack}
                >
                    <ArrowLeft size={24} />
                </motion.button>
                <h1 className="text-2xl font-bold text-[var(--text-color)] flex items-center">
                    <Award className="mr-2 text-[var(--button-color)]" size={28} />
                    Мои баллы
                </h1>
            </div>

            {/* Счетчик автоматов */}
            <AutoPassCounter count={autoPassCount} total={points.length} />

            {/* Карточки с предметами и баллами */}
            <div className="flex-grow pb-4">
                {points.length === 0 ? (
                    <motion.div
                        initial={{ opacity: 0, y: 20 }}
                        animate={{ opacity: 1, y: 0 }}
                        className="text-center p-10 rounded-2xl glass border border-black/5 text-[var(--hint-color)]"
                    >
                        <p>Нет данных о баллах</p>
                    </motion.div>
                ) : (
                    points.map((subject, index) => (
                        <SubjectCard key={index} subject={subject} index={index} />
                    ))
                )}
            </div>
        </motion.div>
    );
};

export default PointsScreen;
