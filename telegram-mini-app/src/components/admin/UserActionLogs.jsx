/**
 * User action logs component for admin panel.
 * Shows user activity history (markings, logins, etc.).
 */
import React, { useState, useEffect, useCallback } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import {
    Activity, Filter, ChevronDown, ChevronLeft, ChevronRight,
    Loader2, AlertTriangle, RefreshCw, X, Search,
    Check, CheckCircle, XCircle, UserCheck, Key, Users
} from 'lucide-react';
import { SkeletonTable } from '../ui/skeleton';

// Action type icons
const ACTION_ICONS = {
    mark_self: Check,
    mark_other: UserCheck,
    mass_marking: Users,
    external_auth: Key,
    login: Key,
    login_2fa: Key,
    toggle_permission: CheckCircle,
};

// Action type labels
const ACTION_LABELS = {
    mark_self: 'Самоотметка',
    mark_other: 'Отметка другого',
    mass_marking: 'Массовая отметка',
    external_auth: 'Внешняя авторизация',
    login: 'Вход в систему',
    login_2fa: 'Вход с 2FA',
    toggle_permission: 'Изменение разрешений',
};

// Status badges
const StatusBadge = ({ status }) => {
    const isSuccess = status === 'success';
    return (
        <span className={`inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium ${
            isSuccess ? 'bg-green-500/20 text-green-500' : 'bg-red-500/20 text-red-500'
        }`}>
            {isSuccess ? <CheckCircle size={12} className="mr-1" /> : <XCircle size={12} className="mr-1" />}
            {isSuccess ? 'Успех' : 'Ошибка'}
        </span>
    );
};

/**
 * Single action log entry.
 */
const ActionLogEntry = ({ log }) => {
    const [expanded, setExpanded] = useState(false);
    const Icon = ACTION_ICONS[log.action_type] || Activity;

    return (
        <motion.div
            initial={{ opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
            className="p-3 rounded-xl glass border border-white/10 mb-2"
        >
            <div className="flex items-start justify-between">
                <div className="flex items-start">
                    <div className={`p-2 mr-3 rounded-lg ${
                        log.status === 'success'
                            ? 'bg-green-500/20 text-green-500'
                            : 'bg-red-500/20 text-red-500'
                    }`}>
                        <Icon size={16} />
                    </div>
                    <div>
                        <div className="flex items-center gap-2 flex-wrap">
                            <span className="text-[var(--text-color)] font-medium text-sm">
                                {ACTION_LABELS[log.action_type] || log.action_type}
                            </span>
                            <StatusBadge status={log.status} />
                        </div>
                        <div className="text-[var(--hint-color)] text-xs mt-1">
                            Пользователь: {log.actor_tg_userid}
                        </div>
                        {log.target_tg_userid && log.target_tg_userid !== log.actor_tg_userid && (
                            <div className="text-[var(--hint-color)] text-xs">
                                Цель: {log.target_tg_userid}
                            </div>
                        )}
                    </div>
                </div>
                <div className="flex flex-col items-end">
                    <span className="text-[var(--hint-color)] text-xs">
                        {new Date(log.created_at).toLocaleString('ru-RU')}
                    </span>
                    {log.details && (
                        <button
                            onClick={() => setExpanded(!expanded)}
                            className="mt-1 text-xs text-[var(--button-color)] hover:underline"
                        >
                            {expanded ? 'Скрыть' : 'Подробнее'}
                        </button>
                    )}
                </div>
            </div>

            {/* Expanded details */}
            <AnimatePresence>
                {expanded && log.details && (
                    <motion.div
                        initial={{ opacity: 0, height: 0 }}
                        animate={{ opacity: 1, height: 'auto' }}
                        exit={{ opacity: 0, height: 0 }}
                        className="mt-3 pt-3 border-t border-white/10"
                    >
                        <div className="p-2 rounded-lg bg-white/5">
                            <div className="text-[var(--hint-color)] text-xs font-medium mb-1">Детали:</div>
                            <pre className="text-[var(--hint-color)] text-xs whitespace-pre-wrap overflow-auto max-h-32">
                                {JSON.stringify(log.details, null, 2)}
                            </pre>
                        </div>
                    </motion.div>
                )}
            </AnimatePresence>
        </motion.div>
    );
};

/**
 * Stats summary component.
 */
const StatsSummary = ({ stats }) => {
    if (!stats) return null;

    return (
        <div className="grid grid-cols-3 gap-2 mb-4">
            <div className="p-3 rounded-lg glass border border-white/10 text-center">
                <div className="text-xl font-bold text-[var(--button-color)]">{stats.total_today || 0}</div>
                <div className="text-xs text-[var(--hint-color)]">Сегодня</div>
            </div>
            <div className="p-3 rounded-lg glass border border-white/10 text-center">
                <div className="text-xl font-bold text-green-500">{stats.success_rate || 0}%</div>
                <div className="text-xs text-[var(--hint-color)]">Успешных</div>
            </div>
            <div className="p-3 rounded-lg glass border border-white/10 text-center">
                <div className="text-xl font-bold text-[var(--text-color)]">{stats.unique_users || 0}</div>
                <div className="text-xs text-[var(--hint-color)]">Активных</div>
            </div>
        </div>
    );
};

/**
 * Main user action logs component.
 */
const UserActionLogs = ({ initData }) => {
    const [logs, setLogs] = useState([]);
    const [stats, setStats] = useState(null);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState(null);
    const [page, setPage] = useState(1);
    const [totalPages, setTotalPages] = useState(1);
    const [filters, setFilters] = useState({
        action_type: '',
        user_id: '',
        status: '',
    });
    const [showFilters, setShowFilters] = useState(false);

    const ITEMS_PER_PAGE = 20;

    const fetchLogs = useCallback(async () => {
        setLoading(true);
        setError(null);
        try {
            let url = `/api/admin/user-action-logs?initData=${encodeURIComponent(initData)}&page=${page}&limit=${ITEMS_PER_PAGE}`;

            if (filters.action_type) {
                url += `&action_type=${encodeURIComponent(filters.action_type)}`;
            }
            if (filters.user_id) {
                url += `&user_id=${encodeURIComponent(filters.user_id)}`;
            }
            if (filters.status) {
                url += `&status=${encodeURIComponent(filters.status)}`;
            }

            const response = await fetch(url);
            if (!response.ok) {
                const data = await response.json();
                throw new Error(data.detail || 'Ошибка загрузки логов');
            }

            const data = await response.json();
            setLogs(data.logs || []);
            setTotalPages(Math.ceil((data.total || 0) / ITEMS_PER_PAGE));
            setStats(data.stats || null);
        } catch (err) {
            setError(err.message);
        } finally {
            setLoading(false);
        }
    }, [initData, page, filters]);

    useEffect(() => {
        fetchLogs();
    }, [fetchLogs]);

    const handleFilterChange = (field, value) => {
        setFilters(prev => ({ ...prev, [field]: value }));
        setPage(1);
    };

    const clearFilters = () => {
        setFilters({ action_type: '', user_id: '', status: '' });
        setPage(1);
    };

    return (
        <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            className="space-y-4"
        >
            {/* Header */}
            <div className="flex items-center justify-between">
                <h3 className="text-[var(--text-color)] font-bold flex items-center">
                    <Activity size={20} className="mr-2 text-[var(--button-color)]" />
                    Действия пользователей
                </h3>
                <div className="flex items-center space-x-2">
                    <button
                        onClick={() => setShowFilters(!showFilters)}
                        className={`p-2 rounded-lg transition-colors ${
                            showFilters || Object.values(filters).some(v => v)
                                ? 'bg-[var(--button-color)] text-white'
                                : 'bg-white/10 text-[var(--hint-color)] hover:bg-white/20'
                        }`}
                    >
                        <Filter size={18} />
                    </button>
                    <button
                        onClick={fetchLogs}
                        disabled={loading}
                        className="p-2 rounded-lg bg-white/10 text-[var(--hint-color)] hover:bg-white/20 transition-colors"
                    >
                        <RefreshCw size={18} className={loading ? 'animate-spin' : ''} />
                    </button>
                </div>
            </div>

            {/* Stats */}
            {!loading && stats && <StatsSummary stats={stats} />}

            {/* Filters */}
            <AnimatePresence>
                {showFilters && (
                    <motion.div
                        initial={{ opacity: 0, height: 0 }}
                        animate={{ opacity: 1, height: 'auto' }}
                        exit={{ opacity: 0, height: 0 }}
                        className="p-4 rounded-xl glass border border-white/10"
                    >
                        <div className="flex items-center justify-between mb-3">
                            <span className="text-[var(--text-color)] font-medium">Фильтры</span>
                            {Object.values(filters).some(v => v) && (
                                <button
                                    onClick={clearFilters}
                                    className="text-xs text-[var(--button-color)] hover:underline flex items-center"
                                >
                                    <X size={12} className="mr-1" />
                                    Сбросить
                                </button>
                            )}
                        </div>
                        <div className="grid grid-cols-3 gap-3">
                            <div>
                                <label className="block text-xs text-[var(--hint-color)] mb-1">Тип действия</label>
                                <div className="relative">
                                    <select
                                        value={filters.action_type}
                                        onChange={(e) => handleFilterChange('action_type', e.target.value)}
                                        className="w-full p-2 rounded-lg border border-white/10 bg-black/20 text-[var(--text-color)] text-sm focus:outline-none appearance-none"
                                    >
                                        <option value="">Все</option>
                                        {Object.entries(ACTION_LABELS).map(([key, label]) => (
                                            <option key={key} value={key}>{label}</option>
                                        ))}
                                    </select>
                                    <ChevronDown size={14} className="absolute right-2 top-1/2 transform -translate-y-1/2 pointer-events-none text-[var(--hint-color)]" />
                                </div>
                            </div>
                            <div>
                                <label className="block text-xs text-[var(--hint-color)] mb-1">ID пользователя</label>
                                <div className="relative">
                                    <Search size={14} className="absolute left-2 top-1/2 transform -translate-y-1/2 text-[var(--hint-color)]" />
                                    <input
                                        type="text"
                                        value={filters.user_id}
                                        onChange={(e) => handleFilterChange('user_id', e.target.value)}
                                        placeholder="Telegram ID"
                                        className="w-full pl-8 pr-3 py-2 rounded-lg border border-white/10 bg-black/20 text-[var(--text-color)] text-sm focus:outline-none"
                                    />
                                </div>
                            </div>
                            <div>
                                <label className="block text-xs text-[var(--hint-color)] mb-1">Статус</label>
                                <div className="relative">
                                    <select
                                        value={filters.status}
                                        onChange={(e) => handleFilterChange('status', e.target.value)}
                                        className="w-full p-2 rounded-lg border border-white/10 bg-black/20 text-[var(--text-color)] text-sm focus:outline-none appearance-none"
                                    >
                                        <option value="">Все</option>
                                        <option value="success">Успех</option>
                                        <option value="failure">Ошибка</option>
                                    </select>
                                    <ChevronDown size={14} className="absolute right-2 top-1/2 transform -translate-y-1/2 pointer-events-none text-[var(--hint-color)]" />
                                </div>
                            </div>
                        </div>
                    </motion.div>
                )}
            </AnimatePresence>

            {/* Content */}
            {loading ? (
                <SkeletonTable rows={5} columns={4} />
            ) : error ? (
                <div className="p-6 rounded-xl glass border border-red-500/20 text-center">
                    <AlertTriangle size={32} className="mx-auto mb-3 text-red-500" />
                    <p className="text-[var(--text-color)] mb-2">{error}</p>
                    <button
                        onClick={fetchLogs}
                        className="px-4 py-2 rounded-lg bg-[var(--button-color)] text-white text-sm"
                    >
                        Повторить
                    </button>
                </div>
            ) : logs.length === 0 ? (
                <div className="p-8 rounded-xl glass text-center text-[var(--hint-color)] border border-white/10">
                    Логи не найдены
                </div>
            ) : (
                <>
                    {/* Log entries */}
                    <div className="space-y-2">
                        {logs.map((log) => (
                            <ActionLogEntry key={log.id} log={log} />
                        ))}
                    </div>

                    {/* Pagination */}
                    <div className="flex justify-between items-center py-2">
                        <button
                            onClick={() => setPage(p => Math.max(1, p - 1))}
                            disabled={page <= 1}
                            className={`p-2 rounded-lg flex items-center ${
                                page > 1
                                    ? 'text-[var(--text-color)] bg-white/10 hover:bg-white/20'
                                    : 'text-[var(--hint-color)] opacity-50 cursor-not-allowed'
                            }`}
                        >
                            <ChevronLeft size={16} className="mr-1" />
                            Назад
                        </button>
                        <span className="text-[var(--hint-color)] text-sm">
                            {page} / {totalPages}
                        </span>
                        <button
                            onClick={() => setPage(p => Math.min(totalPages, p + 1))}
                            disabled={page >= totalPages}
                            className={`p-2 rounded-lg flex items-center ${
                                page < totalPages
                                    ? 'text-[var(--text-color)] bg-white/10 hover:bg-white/20'
                                    : 'text-[var(--hint-color)] opacity-50 cursor-not-allowed'
                            }`}
                        >
                            Вперед
                            <ChevronRight size={16} className="ml-1" />
                        </button>
                    </div>
                </>
            )}
        </motion.div>
    );
};

export default UserActionLogs;
