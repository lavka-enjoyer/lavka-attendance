/**
 * Audit log viewer component for admin panel.
 * Shows admin action history with filters.
 */
import React, { useState, useEffect, useCallback } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import {
    History, Filter, ChevronDown, ChevronLeft, ChevronRight,
    Loader2, AlertTriangle, User, Trash2, UserCog, Upload,
    Download, Edit3, Shield, RefreshCw, X, Search
} from 'lucide-react';
import { SkeletonTable } from '../ui/skeleton';

// Action type icons
const ACTION_ICONS = {
    delete_user: Trash2,
    bulk_delete: Trash2,
    set_admin: Shield,
    bulk_edit: Edit3,
    bulk_import: Upload,
    create_user: User,
    update_user: UserCog,
    export_data: Download,
};

// Action type labels
const ACTION_LABELS = {
    delete_user: 'Удаление',
    bulk_delete: 'Масс. удаление',
    set_admin: 'Уровень админа',
    bulk_edit: 'Масс. редактирование',
    bulk_import: 'Импорт',
    create_user: 'Создание',
    update_user: 'Обновление',
    export_data: 'Экспорт',
};

/**
 * Single audit log entry.
 */
const AuditLogEntry = ({ log }) => {
    const [expanded, setExpanded] = useState(false);
    const Icon = ACTION_ICONS[log.action_type] || History;

    return (
        <motion.div
            initial={{ opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
            className="p-3 rounded-xl glass border border-white/10 mb-2"
        >
            <div className="flex items-start justify-between">
                <div className="flex items-start">
                    <div className="p-2 mr-3 rounded-lg bg-[var(--button-color)]/20 text-[var(--button-color)]">
                        <Icon size={16} />
                    </div>
                    <div>
                        <div className="text-[var(--text-color)] font-medium text-sm">
                            {ACTION_LABELS[log.action_type] || log.action_type}
                        </div>
                        <div className="text-[var(--hint-color)] text-xs">
                            Админ: {log.admin_tg_userid}
                        </div>
                        {log.target_id && (
                            <div className="text-[var(--hint-color)] text-xs">
                                Цель: {log.target_type} #{log.target_id}
                            </div>
                        )}
                    </div>
                </div>
                <div className="flex flex-col items-end">
                    <span className="text-[var(--hint-color)] text-xs">
                        {new Date(log.created_at).toLocaleString('ru-RU')}
                    </span>
                    {(log.old_value || log.new_value) && (
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
                {expanded && (
                    <motion.div
                        initial={{ opacity: 0, height: 0 }}
                        animate={{ opacity: 1, height: 'auto' }}
                        exit={{ opacity: 0, height: 0 }}
                        className="mt-3 pt-3 border-t border-white/10"
                    >
                        <div className="grid grid-cols-2 gap-2 text-xs">
                            {log.old_value && (
                                <div className="p-2 rounded-lg bg-red-500/10">
                                    <div className="text-red-500 font-medium mb-1">Было:</div>
                                    <pre className="text-[var(--hint-color)] whitespace-pre-wrap overflow-auto max-h-32">
                                        {JSON.stringify(log.old_value, null, 2)}
                                    </pre>
                                </div>
                            )}
                            {log.new_value && (
                                <div className="p-2 rounded-lg bg-green-500/10">
                                    <div className="text-green-500 font-medium mb-1">Стало:</div>
                                    <pre className="text-[var(--hint-color)] whitespace-pre-wrap overflow-auto max-h-32">
                                        {JSON.stringify(log.new_value, null, 2)}
                                    </pre>
                                </div>
                            )}
                        </div>
                        {log.ip_address && (
                            <div className="mt-2 text-xs text-[var(--hint-color)]">
                                IP: {log.ip_address}
                            </div>
                        )}
                    </motion.div>
                )}
            </AnimatePresence>
        </motion.div>
    );
};

/**
 * Main audit log viewer component.
 */
const AuditLogViewer = ({ initData }) => {
    const [logs, setLogs] = useState([]);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState(null);
    const [page, setPage] = useState(1);
    const [totalPages, setTotalPages] = useState(1);
    const [filters, setFilters] = useState({
        action_type: '',
        admin_id: '',
    });
    const [showFilters, setShowFilters] = useState(false);

    const ITEMS_PER_PAGE = 20;

    const fetchLogs = useCallback(async () => {
        setLoading(true);
        setError(null);
        try {
            let url = `/api/admin/audit-logs?initData=${encodeURIComponent(initData)}&page=${page}&limit=${ITEMS_PER_PAGE}`;

            if (filters.action_type) {
                url += `&action_type=${encodeURIComponent(filters.action_type)}`;
            }
            if (filters.admin_id) {
                url += `&admin_id=${encodeURIComponent(filters.admin_id)}`;
            }

            const response = await fetch(url);
            if (!response.ok) {
                const data = await response.json();
                throw new Error(data.detail || 'Ошибка загрузки логов');
            }

            const data = await response.json();
            setLogs(data.logs || []);
            setTotalPages(Math.ceil((data.total || 0) / ITEMS_PER_PAGE));
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
        setFilters({ action_type: '', admin_id: '' });
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
                    <History size={20} className="mr-2 text-[var(--button-color)]" />
                    Лог действий админов
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
                        <div className="grid grid-cols-2 gap-3">
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
                                <label className="block text-xs text-[var(--hint-color)] mb-1">ID админа</label>
                                <div className="relative">
                                    <Search size={14} className="absolute left-2 top-1/2 transform -translate-y-1/2 text-[var(--hint-color)]" />
                                    <input
                                        type="text"
                                        value={filters.admin_id}
                                        onChange={(e) => handleFilterChange('admin_id', e.target.value)}
                                        placeholder="Telegram ID"
                                        className="w-full pl-8 pr-3 py-2 rounded-lg border border-white/10 bg-black/20 text-[var(--text-color)] text-sm focus:outline-none"
                                    />
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
                            <AuditLogEntry key={log.id} log={log} />
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

export default AuditLogViewer;
