/**
 * Data export component for admin panel.
 * Allows exporting users and statistics to CSV/Excel.
 */
import React, { useState } from 'react';
import { motion } from 'framer-motion';
import {
    Download, FileSpreadsheet, FileText, Users, BarChart3,
    History, Loader2, CheckCircle, AlertTriangle, Filter, ChevronDown
} from 'lucide-react';
import { showSuccess, showError } from '../ui/toaster';

/**
 * Export button component.
 */
const ExportButton = ({ icon: Icon, label, description, onClick, loading, disabled }) => (
    <motion.button
        whileHover={{ scale: disabled ? 1 : 1.02 }}
        whileTap={{ scale: disabled ? 1 : 0.98 }}
        onClick={onClick}
        disabled={loading || disabled}
        className={`w-full p-4 rounded-xl glass border border-white/10 text-left transition-all ${
            disabled ? 'opacity-50 cursor-not-allowed' : 'hover:bg-white/5'
        }`}
    >
        <div className="flex items-center justify-between">
            <div className="flex items-center">
                <div className="p-2 mr-3 rounded-lg bg-[var(--button-color)]/20 text-[var(--button-color)]">
                    <Icon size={20} />
                </div>
                <div>
                    <div className="text-[var(--text-color)] font-medium">{label}</div>
                    <div className="text-[var(--hint-color)] text-sm">{description}</div>
                </div>
            </div>
            {loading ? (
                <Loader2 className="animate-spin text-[var(--button-color)]" size={20} />
            ) : (
                <Download size={20} className="text-[var(--hint-color)]" />
            )}
        </div>
    </motion.button>
);

/**
 * Format selector component.
 */
const FormatSelector = ({ format, onChange }) => (
    <div className="flex items-center space-x-2 mb-4">
        <span className="text-[var(--hint-color)] text-sm">Формат:</span>
        <div className="flex rounded-lg overflow-hidden border border-white/10">
            <button
                onClick={() => onChange('csv')}
                className={`px-4 py-2 text-sm font-medium transition-colors ${
                    format === 'csv'
                        ? 'bg-[var(--button-color)] text-white'
                        : 'bg-white/10 text-[var(--text-color)] hover:bg-white/20'
                }`}
            >
                <FileText size={14} className="inline mr-1" />
                CSV
            </button>
            <button
                onClick={() => onChange('xlsx')}
                className={`px-4 py-2 text-sm font-medium transition-colors ${
                    format === 'xlsx'
                        ? 'bg-[var(--button-color)] text-white'
                        : 'bg-white/10 text-[var(--text-color)] hover:bg-white/20'
                }`}
            >
                <FileSpreadsheet size={14} className="inline mr-1" />
                Excel
            </button>
        </div>
    </div>
);

/**
 * Main data export component.
 */
const DataExport = ({ initData, availableGroups = [] }) => {
    const [format, setFormat] = useState('csv');
    const [loading, setLoading] = useState({});
    const [filterGroup, setFilterGroup] = useState('');
    const [exportHistory, setExportHistory] = useState([]);

    const downloadFile = (blob, filename) => {
        const url = window.URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = filename;
        document.body.appendChild(a);
        a.click();
        window.URL.revokeObjectURL(url);
        document.body.removeChild(a);
    };

    const handleExportUsers = async () => {
        setLoading(prev => ({ ...prev, users: true }));
        try {
            let url = `/api/admin/export/users?initData=${encodeURIComponent(initData)}&format=${format}`;
            if (filterGroup) {
                url += `&group_name=${encodeURIComponent(filterGroup)}`;
            }

            const response = await fetch(url);
            if (!response.ok) {
                const error = await response.json();
                throw new Error(error.detail || 'Ошибка экспорта');
            }

            const blob = await response.blob();
            const filename = `users_${new Date().toISOString().slice(0, 10)}.${format}`;
            downloadFile(blob, filename);

            showSuccess('Экспорт пользователей завершен');
            addToHistory('users', filename);
        } catch (error) {
            showError(error.message);
        } finally {
            setLoading(prev => ({ ...prev, users: false }));
        }
    };

    const handleExportStatistics = async () => {
        setLoading(prev => ({ ...prev, statistics: true }));
        try {
            const url = `/api/admin/export/statistics?initData=${encodeURIComponent(initData)}&format=${format}`;
            const response = await fetch(url);

            if (!response.ok) {
                const error = await response.json();
                throw new Error(error.detail || 'Ошибка экспорта');
            }

            const blob = await response.blob();
            const filename = `statistics_${new Date().toISOString().slice(0, 10)}.${format}`;
            downloadFile(blob, filename);

            showSuccess('Экспорт статистики завершен');
            addToHistory('statistics', filename);
        } catch (error) {
            showError(error.message);
        } finally {
            setLoading(prev => ({ ...prev, statistics: false }));
        }
    };

    const handleExportAuditLogs = async () => {
        setLoading(prev => ({ ...prev, audit: true }));
        try {
            const url = `/api/admin/export/audit-logs?initData=${encodeURIComponent(initData)}&format=${format}`;
            const response = await fetch(url);

            if (!response.ok) {
                const error = await response.json();
                throw new Error(error.detail || 'Ошибка экспорта');
            }

            const blob = await response.blob();
            const filename = `audit_logs_${new Date().toISOString().slice(0, 10)}.${format}`;
            downloadFile(blob, filename);

            showSuccess('Экспорт логов завершен');
            addToHistory('audit', filename);
        } catch (error) {
            showError(error.message);
        } finally {
            setLoading(prev => ({ ...prev, audit: false }));
        }
    };

    const addToHistory = (type, filename) => {
        setExportHistory(prev => [
            { type, filename, timestamp: new Date().toISOString() },
            ...prev.slice(0, 4)
        ]);
    };

    return (
        <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            className="space-y-6"
        >
            {/* Format selector */}
            <div className="p-4 rounded-xl glass border border-white/10">
                <h3 className="text-[var(--text-color)] font-medium mb-3">Настройки экспорта</h3>
                <FormatSelector format={format} onChange={setFormat} />

                {/* Group filter */}
                <div className="flex items-center space-x-2">
                    <Filter size={16} className="text-[var(--hint-color)]" />
                    <span className="text-[var(--hint-color)] text-sm">Фильтр по группе:</span>
                    <div className="relative flex-grow">
                        <select
                            value={filterGroup}
                            onChange={(e) => setFilterGroup(e.target.value)}
                            className="w-full p-2 rounded-lg border border-white/10 bg-black/20 text-[var(--text-color)] focus:outline-none focus:ring-2 focus:ring-[var(--button-color)] appearance-none text-sm"
                        >
                            <option value="">Все группы</option>
                            {availableGroups.map(group => (
                                <option key={group} value={group}>{group}</option>
                            ))}
                        </select>
                        <ChevronDown size={14} className="absolute right-2 top-1/2 transform -translate-y-1/2 pointer-events-none text-[var(--hint-color)]" />
                    </div>
                </div>
            </div>

            {/* Export buttons */}
            <div className="space-y-3">
                <h3 className="text-[var(--text-color)] font-medium px-1">Доступные экспорты</h3>

                <ExportButton
                    icon={Users}
                    label="Экспорт пользователей"
                    description="Список всех пользователей с данными"
                    onClick={handleExportUsers}
                    loading={loading.users}
                />

                <ExportButton
                    icon={BarChart3}
                    label="Экспорт статистики"
                    description="Сводная статистика по группам и активности"
                    onClick={handleExportStatistics}
                    loading={loading.statistics}
                />

                <ExportButton
                    icon={History}
                    label="Экспорт логов аудита"
                    description="История админских действий"
                    onClick={handleExportAuditLogs}
                    loading={loading.audit}
                />
            </div>

            {/* Export history */}
            {exportHistory.length > 0 && (
                <div className="p-4 rounded-xl glass border border-white/10">
                    <h3 className="text-[var(--text-color)] font-medium mb-3 flex items-center">
                        <History size={16} className="mr-2 text-[var(--button-color)]" />
                        История экспорта
                    </h3>
                    <div className="space-y-2">
                        {exportHistory.map((item, index) => (
                            <div key={index} className="flex items-center justify-between p-2 rounded-lg bg-white/5">
                                <div className="flex items-center">
                                    <CheckCircle size={14} className="mr-2 text-green-500" />
                                    <span className="text-sm text-[var(--text-color)]">{item.filename}</span>
                                </div>
                                <span className="text-xs text-[var(--hint-color)]">
                                    {new Date(item.timestamp).toLocaleTimeString()}
                                </span>
                            </div>
                        ))}
                    </div>
                </div>
            )}

            {/* Info */}
            <div className="p-4 rounded-xl bg-[var(--button-color)]/10 border border-[var(--button-color)]/20">
                <div className="flex items-start">
                    <AlertTriangle size={18} className="mr-2 mt-0.5 text-[var(--button-color)]" />
                    <div className="text-sm text-[var(--text-color)]">
                        <p className="font-medium mb-1">Примечание</p>
                        <p className="text-[var(--hint-color)]">
                            Экспорт может занять некоторое время для больших объемов данных.
                            Максимальное количество записей в одном экспорте: 10 000.
                        </p>
                    </div>
                </div>
            </div>
        </motion.div>
    );
};

export default DataExport;
