/**
 * Bulk operations component for admin panel.
 * Allows bulk delete and edit operations on users.
 */
import React, { useState, useCallback } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import {
    Trash2, Edit3, X, AlertTriangle, CheckCircle,
    Loader2, Users, ChevronDown
} from 'lucide-react';
import VirtualUserList from './VirtualUserList';
import { showSuccess, showError } from '../ui/toaster';

// Admin levels
const ADMIN_LEVELS = {
    0: { name: 'Пользователь', color: 'gray' },
    1: { name: 'Модератор', color: 'blue' },
    2: { name: 'Админ', color: 'green' },
    3: { name: 'Ст. Админ', color: 'yellow' },
    4: { name: 'Суперадмин', color: 'orange' },
    5: { name: 'Владелец', color: 'red' }
};

/**
 * Confirmation modal for bulk operations.
 */
const ConfirmModal = ({ isOpen, onClose, onConfirm, title, message, loading, type = 'danger' }) => {
    if (!isOpen) return null;

    return (
        <div className="fixed inset-0 bg-black/60 backdrop-blur-sm flex items-center justify-center z-50 p-4">
            <motion.div
                initial={{ scale: 0.9, opacity: 0 }}
                animate={{ scale: 1, opacity: 1 }}
                exit={{ scale: 0.9, opacity: 0 }}
                className="w-full max-w-sm rounded-2xl p-6 glass border border-white/10"
            >
                <div className="flex items-center mb-4">
                    <div className={`p-2 rounded-full mr-3 ${type === 'danger' ? 'bg-red-500/20 text-red-500' : 'bg-[var(--button-color)]/20 text-[var(--button-color)]'}`}>
                        <AlertTriangle size={24} />
                    </div>
                    <h3 className="text-lg font-bold text-[var(--text-color)]">{title}</h3>
                </div>

                <p className="text-[var(--hint-color)] mb-6">{message}</p>

                <div className="flex space-x-3">
                    <button
                        onClick={onClose}
                        disabled={loading}
                        className="flex-1 py-2.5 px-4 rounded-xl bg-white/10 text-[var(--text-color)] font-medium hover:bg-white/20 transition-colors"
                    >
                        Отмена
                    </button>
                    <button
                        onClick={onConfirm}
                        disabled={loading}
                        className={`flex-1 py-2.5 px-4 rounded-xl font-medium transition-colors flex items-center justify-center ${
                            type === 'danger'
                                ? 'bg-red-500 text-white hover:bg-red-600'
                                : 'bg-[var(--button-color)] text-white'
                        }`}
                    >
                        {loading ? <Loader2 className="animate-spin" size={18} /> : 'Подтвердить'}
                    </button>
                </div>
            </motion.div>
        </div>
    );
};

/**
 * Bulk edit modal.
 */
const BulkEditModal = ({ isOpen, onClose, onConfirm, selectedCount, loading, currentAdminLevel }) => {
    const [editField, setEditField] = useState('admin_lvl');
    const [editValue, setEditValue] = useState(0);

    if (!isOpen) return null;

    return (
        <div className="fixed inset-0 bg-black/60 backdrop-blur-sm flex items-center justify-center z-50 p-4">
            <motion.div
                initial={{ scale: 0.9, opacity: 0 }}
                animate={{ scale: 1, opacity: 1 }}
                exit={{ scale: 0.9, opacity: 0 }}
                className="w-full max-w-sm rounded-2xl p-6 glass border border-white/10"
            >
                <div className="flex justify-between items-center mb-4">
                    <h3 className="text-lg font-bold text-[var(--text-color)]">Массовое редактирование</h3>
                    <button onClick={onClose} className="p-1 rounded-full hover:bg-white/10 text-[var(--hint-color)]">
                        <X size={20} />
                    </button>
                </div>

                <p className="text-[var(--hint-color)] mb-4">
                    Выбрано пользователей: <span className="font-bold text-[var(--text-color)]">{selectedCount}</span>
                </p>

                {/* Field selector */}
                <div className="mb-4">
                    <label className="block text-sm text-[var(--hint-color)] mb-2">Поле для изменения</label>
                    <div className="relative">
                        <select
                            value={editField}
                            onChange={(e) => setEditField(e.target.value)}
                            className="w-full p-3 rounded-xl border border-white/10 bg-black/20 text-[var(--text-color)] focus:outline-none focus:ring-2 focus:ring-[var(--button-color)] appearance-none"
                        >
                            <option value="admin_lvl">Уровень админа</option>
                            <option value="allowConfirm">Разрешение на отметку</option>
                        </select>
                        <ChevronDown size={16} className="absolute right-3 top-1/2 transform -translate-y-1/2 pointer-events-none text-[var(--hint-color)]" />
                    </div>
                </div>

                {/* Value selector */}
                <div className="mb-6">
                    <label className="block text-sm text-[var(--hint-color)] mb-2">Новое значение</label>
                    {editField === 'admin_lvl' ? (
                        <div className="space-y-2">
                            {Object.entries(ADMIN_LEVELS).map(([level, info]) => {
                                const levelNum = parseInt(level);
                                const isDisabled = levelNum > currentAdminLevel;
                                return (
                                    <button
                                        key={level}
                                        onClick={() => !isDisabled && setEditValue(levelNum)}
                                        disabled={isDisabled}
                                        className={`w-full p-3 rounded-xl flex items-center justify-between transition-all ${
                                            editValue === levelNum
                                                ? 'bg-[var(--button-color)] text-white'
                                                : isDisabled
                                                    ? 'bg-white/5 text-[var(--hint-color)] opacity-50 cursor-not-allowed'
                                                    : 'bg-white/10 text-[var(--text-color)] hover:bg-white/20'
                                        }`}
                                    >
                                        <span className="font-medium">{info.name}</span>
                                        <span className="text-sm opacity-70">Уровень {level}</span>
                                    </button>
                                );
                            })}
                        </div>
                    ) : (
                        <div className="flex space-x-2">
                            <button
                                onClick={() => setEditValue(true)}
                                className={`flex-1 p-3 rounded-xl transition-all ${
                                    editValue === true
                                        ? 'bg-green-500 text-white'
                                        : 'bg-white/10 text-[var(--text-color)] hover:bg-white/20'
                                }`}
                            >
                                Разрешить
                            </button>
                            <button
                                onClick={() => setEditValue(false)}
                                className={`flex-1 p-3 rounded-xl transition-all ${
                                    editValue === false
                                        ? 'bg-red-500 text-white'
                                        : 'bg-white/10 text-[var(--text-color)] hover:bg-white/20'
                                }`}
                            >
                                Запретить
                            </button>
                        </div>
                    )}
                </div>

                <button
                    onClick={() => onConfirm(editField, editValue)}
                    disabled={loading}
                    className="w-full py-3 px-4 rounded-xl bg-[var(--button-color)] text-white font-medium disabled:opacity-50 flex items-center justify-center"
                >
                    {loading ? <Loader2 className="animate-spin" size={18} /> : 'Применить'}
                </button>
            </motion.div>
        </div>
    );
};

/**
 * Main bulk operations component.
 */
const BulkOperations = ({ initData, users, currentAdminLevel, onRefresh }) => {
    const [selectedUsers, setSelectedUsers] = useState([]);
    const [showDeleteConfirm, setShowDeleteConfirm] = useState(false);
    const [showEditModal, setShowEditModal] = useState(false);
    const [loading, setLoading] = useState(false);
    const [result, setResult] = useState(null);

    const handleSelectUser = useCallback((userId) => {
        setSelectedUsers(prev => {
            if (prev.includes(userId)) {
                return prev.filter(id => id !== userId);
            }
            return [...prev, userId];
        });
    }, []);

    const handleSelectAll = useCallback(() => {
        if (selectedUsers.length === users.length) {
            setSelectedUsers([]);
        } else {
            setSelectedUsers(users.map(u => u.tg_userid));
        }
    }, [selectedUsers.length, users]);

    const handleBulkDelete = async () => {
        setLoading(true);
        try {
            const response = await fetch('/api/admin/bulk_delete', {
                method: 'DELETE',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    initData,
                    user_ids: selectedUsers
                })
            });

            const data = await response.json();
            if (!response.ok) throw new Error(data.detail || 'Ошибка удаления');

            setResult({
                type: 'delete',
                deleted: data.deleted || [],
                failed: data.failed || [],
                errors: data.errors || {}
            });

            showSuccess(`Удалено пользователей: ${data.deleted?.length || 0}`);
            setSelectedUsers([]);
            setShowDeleteConfirm(false);
            onRefresh?.();
        } catch (error) {
            showError(error.message);
        } finally {
            setLoading(false);
        }
    };

    const handleBulkEdit = async (field, value) => {
        setLoading(true);
        try {
            const response = await fetch('/api/admin/bulk_edit', {
                method: 'PATCH',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    initData,
                    user_ids: selectedUsers,
                    field,
                    value
                })
            });

            const data = await response.json();
            if (!response.ok) throw new Error(data.detail || 'Ошибка редактирования');

            setResult({
                type: 'edit',
                updated: data.updated || [],
                failed: data.failed || [],
                errors: data.errors || {}
            });

            showSuccess(`Обновлено пользователей: ${data.updated?.length || 0}`);
            setSelectedUsers([]);
            setShowEditModal(false);
            onRefresh?.();
        } catch (error) {
            showError(error.message);
        } finally {
            setLoading(false);
        }
    };

    return (
        <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            className="min-h-[calc(100vh-200px)]"
        >
            {/* Action bar */}
            <div className="flex items-center justify-between p-3 mb-4 rounded-xl glass border border-white/10">
                <div className="flex items-center text-[var(--text-color)]">
                    <Users size={18} className="mr-2 text-[var(--button-color)]" />
                    <span className="text-sm font-medium">Массовые операции</span>
                </div>
                <div className="flex space-x-2">
                    <button
                        onClick={() => setShowEditModal(true)}
                        disabled={selectedUsers.length === 0}
                        className="flex items-center px-3 py-2 rounded-lg bg-[var(--button-color)]/20 text-[var(--button-color)] hover:bg-[var(--button-color)]/30 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
                    >
                        <Edit3 size={16} className="mr-1" />
                        <span className="text-sm">Редактировать</span>
                    </button>
                    <button
                        onClick={() => setShowDeleteConfirm(true)}
                        disabled={selectedUsers.length === 0}
                        className="flex items-center px-3 py-2 rounded-lg bg-red-500/20 text-red-500 hover:bg-red-500/30 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
                    >
                        <Trash2 size={16} className="mr-1" />
                        <span className="text-sm">Удалить</span>
                    </button>
                </div>
            </div>

            {/* Result notification */}
            <AnimatePresence>
                {result && (
                    <motion.div
                        initial={{ opacity: 0, y: -20 }}
                        animate={{ opacity: 1, y: 0 }}
                        exit={{ opacity: 0, y: -20 }}
                        className="mb-4 p-4 rounded-xl glass border border-white/10"
                    >
                        <div className="flex items-start justify-between">
                            <div>
                                <div className="flex items-center mb-2">
                                    <CheckCircle size={18} className="mr-2 text-green-500" />
                                    <span className="font-medium text-[var(--text-color)]">
                                        {result.type === 'delete' ? 'Удаление завершено' : 'Редактирование завершено'}
                                    </span>
                                </div>
                                <div className="text-sm text-[var(--hint-color)]">
                                    {result.type === 'delete' ? (
                                        <>Удалено: {result.deleted.length}, Ошибок: {result.failed.length}</>
                                    ) : (
                                        <>Обновлено: {result.updated.length}, Ошибок: {result.failed.length}</>
                                    )}
                                </div>
                            </div>
                            <button
                                onClick={() => setResult(null)}
                                className="p-1 rounded-full hover:bg-white/10 text-[var(--hint-color)]"
                            >
                                <X size={16} />
                            </button>
                        </div>
                    </motion.div>
                )}
            </AnimatePresence>

            {/* User list */}
            <VirtualUserList
                users={users}
                loading={false}
                currentAdminLevel={currentAdminLevel}
                selectedUsers={selectedUsers}
                onSelectUser={handleSelectUser}
                onSelectAll={handleSelectAll}
                selectionMode={true}
            />

            {/* Modals */}
            <ConfirmModal
                isOpen={showDeleteConfirm}
                onClose={() => setShowDeleteConfirm(false)}
                onConfirm={handleBulkDelete}
                title="Удалить пользователей?"
                message={`Вы уверены, что хотите удалить ${selectedUsers.length} пользователей? Это действие нельзя отменить.`}
                loading={loading}
            />

            <BulkEditModal
                isOpen={showEditModal}
                onClose={() => setShowEditModal(false)}
                onConfirm={handleBulkEdit}
                selectedCount={selectedUsers.length}
                loading={loading}
                currentAdminLevel={currentAdminLevel}
            />
        </motion.div>
    );
};

export default BulkOperations;
