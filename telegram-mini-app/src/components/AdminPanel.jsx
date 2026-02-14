import React, { useState, useEffect, useCallback } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import {
    Users, ArrowLeft, Activity, Search, ChevronLeft, ChevronRight,
    User, Filter, X, ShieldCheck, Plus, Loader2, Trash2, UserCog,
    ChevronDown, AlertTriangle, CheckCircle, UsersRound, Key,
    BarChart3, Download, Upload, History, FileText
} from 'lucide-react';
import BulkOperations from './admin/BulkOperations';
import DataExport from './admin/DataExport';
import AnalyticsDashboard from './admin/AnalyticsDashboard';
import AuditLogViewer from './admin/AuditLogViewer';
import BulkImport from './admin/BulkImport';
import UserActionLogs from './admin/UserActionLogs';
import { SkeletonUserList, SkeletonAdminStats } from './ui/skeleton';

// Уровни админа
const ADMIN_LEVELS = {
    0: { name: 'Пользователь', color: 'gray' },
    1: { name: 'Модератор', color: 'blue' },
    2: { name: 'Админ', color: 'green' },
    3: { name: 'Ст. Админ', color: 'yellow' },
    4: { name: 'Суперадмин', color: 'orange' },
    5: { name: 'Владелец', color: 'red' }
};

// Модальное окно подтверждения
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

// Модальное окно изменения уровня админа
const AdminLevelModal = ({ isOpen, onClose, user, onConfirm, loading, currentAdminLevel }) => {
    const [selectedLevel, setSelectedLevel] = useState(user?.admin_lvl || 0);

    useEffect(() => {
        if (user) setSelectedLevel(user.admin_lvl || 0);
    }, [user]);

    if (!isOpen || !user) return null;

    return (
        <div className="fixed inset-0 bg-black/60 backdrop-blur-sm flex items-center justify-center z-50 p-4">
            <motion.div
                initial={{ scale: 0.9, opacity: 0 }}
                animate={{ scale: 1, opacity: 1 }}
                exit={{ scale: 0.9, opacity: 0 }}
                className="w-full max-w-sm rounded-2xl p-6 glass border border-white/10"
            >
                <div className="flex justify-between items-center mb-4">
                    <h3 className="text-lg font-bold text-[var(--text-color)]">Изменить уровень</h3>
                    <button onClick={onClose} className="p-1 rounded-full hover:bg-white/10 text-[var(--hint-color)]">
                        <X size={20} />
                    </button>
                </div>

                <div className="mb-4 p-3 rounded-xl bg-white/5 border border-white/10">
                    <div className="text-[var(--text-color)] font-medium">{user.login || `ID: ${user.tg_userid}`}</div>
                    {user.group_name && <div className="text-[var(--hint-color)] text-sm">{user.group_name}</div>}
                </div>

                <div className="space-y-2 mb-6">
                    {Object.entries(ADMIN_LEVELS).map(([level, info]) => {
                        const levelNum = parseInt(level);
                        const isDisabled = levelNum > currentAdminLevel;

                        return (
                            <button
                                key={level}
                                onClick={() => !isDisabled && setSelectedLevel(levelNum)}
                                disabled={isDisabled}
                                className={`w-full p-3 rounded-xl flex items-center justify-between transition-all ${
                                    selectedLevel === levelNum
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

                <button
                    onClick={() => onConfirm(selectedLevel)}
                    disabled={loading || selectedLevel === user.admin_lvl}
                    className="w-full py-3 px-4 rounded-xl bg-[var(--button-color)] text-white font-medium disabled:opacity-50 flex items-center justify-center"
                >
                    {loading ? <Loader2 className="animate-spin" size={18} /> : 'Сохранить'}
                </button>
            </motion.div>
        </div>
    );
};

// Компонент списка администраторов
const AdminsList = ({ initData, currentAdminLevel }) => {
    const [admins, setAdmins] = useState([]);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState('');
    const [actionLoading, setActionLoading] = useState(false);
    const [selectedUser, setSelectedUser] = useState(null);
    const [showLevelModal, setShowLevelModal] = useState(false);
    const [notification, setNotification] = useState(null);

    const fetchAdmins = useCallback(async () => {
        setLoading(true);
        try {
            const response = await fetch(`/api/get_all_admin?initData=${encodeURIComponent(initData)}`);
            if (!response.ok) throw new Error(`Error: ${response.status}`);
            const data = await response.json();
            setAdmins(Array.isArray(data) ? data : []);
        } catch (error) {
            setError(error.message || 'Ошибка загрузки');
        } finally {
            setLoading(false);
        }
    }, [initData]);

    useEffect(() => {
        fetchAdmins();
    }, [fetchAdmins]);

    const showNotification = (message, type = 'success') => {
        setNotification({ message, type });
        setTimeout(() => setNotification(null), 3000);
    };

    const handleChangeLevel = async (newLevel) => {
        if (!selectedUser) return;
        setActionLoading(true);
        try {
            const response = await fetch('/api/admin/set_admin_level', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    initData,
                    target_tg_userid: selectedUser.tg_userid,
                    admin_level: newLevel
                })
            });

            const data = await response.json();
            if (!response.ok) throw new Error(data.detail || 'Ошибка');

            showNotification('Уровень успешно изменен');
            setShowLevelModal(false);
            fetchAdmins();
        } catch (error) {
            showNotification(error.message, 'error');
        } finally {
            setActionLoading(false);
        }
    };

    return (
        <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            className="min-h-[calc(100vh-120px)]"
        >
            {/* Notification */}
            <AnimatePresence>
                {notification && (
                    <motion.div
                        initial={{ opacity: 0, y: -20 }}
                        animate={{ opacity: 1, y: 0 }}
                        exit={{ opacity: 0, y: -20 }}
                        className={`mb-4 p-3 rounded-xl flex items-center ${
                            notification.type === 'error'
                                ? 'bg-red-500/10 text-red-500 border border-red-500/20'
                                : 'bg-green-500/10 text-green-500 border border-green-500/20'
                        }`}
                    >
                        {notification.type === 'error' ? <AlertTriangle size={18} className="mr-2" /> : <CheckCircle size={18} className="mr-2" />}
                        {notification.message}
                    </motion.div>
                )}
            </AnimatePresence>

            {loading ? (
                <SkeletonUserList count={5} />
            ) : error ? (
                <div className="p-4 rounded-xl bg-red-500/10 text-red-500 text-center border border-red-500/20">{error}</div>
            ) : admins.length === 0 ? (
                <div className="p-8 rounded-xl glass text-center text-[var(--hint-color)] border border-white/10">
                    Нет администраторов
                </div>
            ) : (
                <div className="space-y-3">
                    {admins.map((admin, index) => (
                        <motion.div
                            key={admin.tg_userid}
                            initial={{ opacity: 0, x: -10 }}
                            animate={{ opacity: 1, x: 0 }}
                            transition={{ delay: index * 0.05 }}
                            className="p-4 rounded-xl glass border-l-4 border-[var(--button-color)] border-white/10"
                        >
                            <div className="flex justify-between items-start">
                                <div className="flex-1">
                                    <div className="flex items-center mb-1 flex-wrap gap-2">
                                        <ShieldCheck size={18} className="text-[var(--button-color)]" />
                                        <span className="text-[var(--text-color)] font-medium">{admin.login || `ID: ${admin.tg_userid}`}</span>
                                        <span className={`px-2 py-0.5 text-xs rounded-full bg-[var(--button-color)]/20 text-[var(--button-color)]`}>
                                            {ADMIN_LEVELS[admin.admin_lvl]?.name || `Lvl ${admin.admin_lvl}`}
                                        </span>
                                    </div>
                                    {admin.group_name && (
                                        <div className="text-[var(--hint-color)] text-sm mb-1">Группа: {admin.group_name}</div>
                                    )}
                                    <div className="text-[var(--hint-color)] text-xs opacity-70">ID: {admin.tg_userid}</div>
                                </div>

                                {currentAdminLevel >= 3 && admin.admin_lvl < currentAdminLevel && (
                                    <button
                                        onClick={() => { setSelectedUser(admin); setShowLevelModal(true); }}
                                        className="p-2 rounded-lg bg-white/10 text-[var(--hint-color)] hover:bg-white/20 hover:text-[var(--text-color)] transition-colors"
                                    >
                                        <UserCog size={18} />
                                    </button>
                                )}
                            </div>
                        </motion.div>
                    ))}
                </div>
            )}

            <AdminLevelModal
                isOpen={showLevelModal}
                onClose={() => { setShowLevelModal(false); setSelectedUser(null); }}
                user={selectedUser}
                onConfirm={handleChangeLevel}
                loading={actionLoading}
                currentAdminLevel={currentAdminLevel}
            />
        </motion.div>
    );
};

// Компонент списка пользователей
const UsersList = ({ initData, currentAdminLevel }) => {
    const [users, setUsers] = useState([]);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState('');
    const [currentPage, setCurrentPage] = useState(1);
    const [totalUsers, setTotalUsers] = useState(0);
    const [filterGroup, setFilterGroup] = useState('');
    const [availableGroups, setAvailableGroups] = useState([]);
    const [searchQuery, setSearchQuery] = useState('');
    const [searchResults, setSearchResults] = useState(null);
    const [searchLoading, setSearchLoading] = useState(false);
    const [actionLoading, setActionLoading] = useState(false);
    const [selectedUser, setSelectedUser] = useState(null);
    const [showDeleteConfirm, setShowDeleteConfirm] = useState(false);
    const [showLevelModal, setShowLevelModal] = useState(false);
    const [notification, setNotification] = useState(null);

    const USERS_PER_PAGE = 10;

    const showNotification = (message, type = 'success') => {
        setNotification({ message, type });
        setTimeout(() => setNotification(null), 3000);
    };

    const fetchUsers = useCallback(async () => {
        setLoading(true);
        try {
            const offset = (currentPage - 1) * USERS_PER_PAGE;
            let url = `/api/get_all_users?initData=${encodeURIComponent(initData)}&offset=${offset}`;
            if (filterGroup) url += `&group_name=${encodeURIComponent(filterGroup)}`;

            const response = await fetch(url);
            if (!response.ok) throw new Error(`Error: ${response.status}`);
            const data = await response.json();
            setUsers(Array.isArray(data) ? data : []);

            const countResponse = await fetch(`/api/get_count_users?initData=${encodeURIComponent(initData)}`);
            if (countResponse.ok) {
                const countData = await countResponse.json();
                setTotalUsers(countData["Users count"] || 0);
            }
        } catch (error) {
            setError(error.message || 'Ошибка загрузки');
        } finally {
            setLoading(false);
        }
    }, [initData, currentPage, filterGroup]);

    const fetchGroups = useCallback(async () => {
        try {
            const response = await fetch(`/api/get_available_groups?initData=${encodeURIComponent(initData)}`);
            if (response.ok) {
                const data = await response.json();
                setAvailableGroups(data.groups || []);
            }
        } catch (error) {
            console.error('Error fetching groups:', error);
        }
    }, [initData]);

    useEffect(() => {
        fetchUsers();
    }, [fetchUsers]);

    useEffect(() => {
        fetchGroups();
    }, [fetchGroups]);

    // Поиск с debounce
    useEffect(() => {
        if (!searchQuery.trim()) {
            setSearchResults(null);
            return;
        }

        const timer = setTimeout(async () => {
            setSearchLoading(true);
            try {
                const response = await fetch(
                    `/api/admin/search_users?initData=${encodeURIComponent(initData)}&query=${encodeURIComponent(searchQuery)}`
                );
                if (response.ok) {
                    const data = await response.json();
                    setSearchResults(data.users || []);
                }
            } catch (error) {
                console.error('Search error:', error);
            } finally {
                setSearchLoading(false);
            }
        }, 300);

        return () => clearTimeout(timer);
    }, [searchQuery, initData]);

    const handleDeleteUser = async () => {
        if (!selectedUser) return;
        setActionLoading(true);
        try {
            const response = await fetch('/api/admin/delete_user', {
                method: 'DELETE',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    initData,
                    target_tg_userid: selectedUser.tg_userid
                })
            });

            const data = await response.json();
            if (!response.ok) throw new Error(data.detail || 'Ошибка удаления');

            showNotification('Пользователь удален');
            setShowDeleteConfirm(false);
            setSelectedUser(null);
            fetchUsers();
            if (searchQuery) setSearchResults(prev => prev?.filter(u => u.tg_userid !== selectedUser.tg_userid));
        } catch (error) {
            showNotification(error.message, 'error');
        } finally {
            setActionLoading(false);
        }
    };

    const handleChangeLevel = async (newLevel) => {
        if (!selectedUser) return;
        setActionLoading(true);
        try {
            const response = await fetch('/api/admin/set_admin_level', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    initData,
                    target_tg_userid: selectedUser.tg_userid,
                    admin_level: newLevel
                })
            });

            const data = await response.json();
            if (!response.ok) throw new Error(data.detail || 'Ошибка');

            showNotification('Уровень изменен');
            setShowLevelModal(false);
            fetchUsers();
        } catch (error) {
            showNotification(error.message, 'error');
        } finally {
            setActionLoading(false);
        }
    };

    const displayUsers = searchResults !== null ? searchResults : users;
    const isAdmin = (adminLevel) => adminLevel && adminLevel !== 0;

    const UserCard = ({ user, index }) => (
        <motion.div
            initial={{ opacity: 0, x: -10 }}
            animate={{ opacity: 1, x: 0 }}
            transition={{ delay: index * 0.03 }}
            className="p-4 rounded-xl glass border-l-4 border-white/10"
            style={{ borderLeftColor: isAdmin(user.admin_lvl) ? 'var(--button-color)' : 'var(--hint-color)' }}
        >
            <div className="flex justify-between items-start">
                <div className="flex-1 min-w-0">
                    <div className="flex items-center mb-1 flex-wrap gap-2">
                        <User size={16} className="text-[var(--text-color)] flex-shrink-0" />
                        <span className="text-[var(--text-color)] font-medium truncate">
                            {user.login || user.fio || `ID: ${user.tg_userid}`}
                        </span>
                        {isAdmin(user.admin_lvl) && (
                            <span className="px-2 py-0.5 text-xs rounded-full bg-[var(--button-color)]/20 text-[var(--button-color)] flex-shrink-0">
                                {ADMIN_LEVELS[user.admin_lvl]?.name || `Lvl ${user.admin_lvl}`}
                            </span>
                        )}
                    </div>
                    {user.group_name && (
                        <div className="text-[var(--hint-color)] text-sm mb-1">{user.group_name}</div>
                    )}
                    {user.fio && user.login && (
                        <div className="text-[var(--hint-color)] text-xs opacity-70">{user.fio}</div>
                    )}
                    <div className="text-[var(--hint-color)] text-xs opacity-50 mt-1">ID: {user.tg_userid}</div>
                </div>

                {currentAdminLevel >= 3 && (
                    <div className="flex space-x-1 flex-shrink-0 ml-2">
                        <button
                            onClick={() => { setSelectedUser(user); setShowLevelModal(true); }}
                            className="p-2 rounded-lg bg-white/10 text-[var(--hint-color)] hover:bg-white/20 hover:text-[var(--button-color)] transition-colors"
                            title="Изменить уровень"
                        >
                            <UserCog size={16} />
                        </button>
                        <button
                            onClick={() => { setSelectedUser(user); setShowDeleteConfirm(true); }}
                            className="p-2 rounded-lg bg-white/10 text-[var(--hint-color)] hover:bg-red-500/20 hover:text-red-500 transition-colors"
                            title="Удалить"
                        >
                            <Trash2 size={16} />
                        </button>
                    </div>
                )}
            </div>
        </motion.div>
    );

    return (
        <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            className="min-h-[calc(100vh-120px)]"
        >
            {/* Notification */}
            <AnimatePresence>
                {notification && (
                    <motion.div
                        initial={{ opacity: 0, y: -20 }}
                        animate={{ opacity: 1, y: 0 }}
                        exit={{ opacity: 0, y: -20 }}
                        className={`mb-4 p-3 rounded-xl flex items-center ${
                            notification.type === 'error'
                                ? 'bg-red-500/10 text-red-500 border border-red-500/20'
                                : 'bg-green-500/10 text-green-500 border border-green-500/20'
                        }`}
                    >
                        {notification.type === 'error' ? <AlertTriangle size={18} className="mr-2" /> : <CheckCircle size={18} className="mr-2" />}
                        {notification.message}
                    </motion.div>
                )}
            </AnimatePresence>

            {/* Search */}
            <div className="mb-4">
                <div className="relative">
                    <Search size={18} className="absolute left-3 top-1/2 transform -translate-y-1/2 text-[var(--hint-color)]" />
                    <input
                        type="text"
                        value={searchQuery}
                        onChange={(e) => setSearchQuery(e.target.value)}
                        placeholder="Поиск по логину, группе, ФИО или ID..."
                        className="w-full pl-10 pr-10 py-3 rounded-xl border border-white/10 bg-black/20 text-[var(--text-color)] focus:outline-none focus:ring-2 focus:ring-[var(--button-color)]"
                    />
                    {searchQuery && (
                        <button
                            onClick={() => setSearchQuery('')}
                            className="absolute right-3 top-1/2 transform -translate-y-1/2 text-[var(--hint-color)] hover:text-[var(--text-color)]"
                        >
                            <X size={18} />
                        </button>
                    )}
                </div>
                {searchLoading && (
                    <div className="mt-2 text-[var(--hint-color)] text-sm flex items-center">
                        <Loader2 className="animate-spin mr-2" size={14} />
                        Поиск...
                    </div>
                )}
            </div>

            {/* Filter */}
            {!searchQuery && (
                <div className="p-4 mb-4 rounded-xl glass border border-white/10">
                    <div className="flex items-center mb-3">
                        <Filter size={16} className="mr-2 text-[var(--button-color)]" />
                        <span className="text-[var(--text-color)] font-medium">Фильтр по группе</span>
                    </div>
                    <div className="flex space-x-2">
                        <div className="relative flex-grow">
                            <select
                                value={filterGroup}
                                onChange={(e) => { setFilterGroup(e.target.value); setCurrentPage(1); }}
                                className="w-full p-2.5 rounded-xl border border-white/10 bg-black/20 text-[var(--text-color)] focus:outline-none focus:ring-2 focus:ring-[var(--button-color)] appearance-none"
                            >
                                <option value="">Все группы</option>
                                {availableGroups.map(group => (
                                    <option key={group} value={group}>{group}</option>
                                ))}
                            </select>
                            <div className="absolute right-3 top-1/2 transform -translate-y-1/2 pointer-events-none text-[var(--hint-color)]">
                                <ChevronDown size={16} />
                            </div>
                        </div>
                        {filterGroup && (
                            <button
                                onClick={() => setFilterGroup('')}
                                className="p-2.5 rounded-xl bg-white/10 text-[var(--text-color)] hover:bg-white/20"
                            >
                                <X size={20} />
                            </button>
                        )}
                    </div>
                </div>
            )}

            {/* Users list */}
            {loading && !searchQuery ? (
                <SkeletonUserList count={5} />
            ) : error ? (
                <div className="p-4 rounded-xl bg-red-500/10 text-red-500 text-center border border-red-500/20">{error}</div>
            ) : displayUsers.length === 0 ? (
                <div className="p-8 rounded-xl glass text-center text-[var(--hint-color)] border border-white/10">
                    {searchQuery ? 'Ничего не найдено' : 'Пользователи не найдены'}
                </div>
            ) : (
                <div className="space-y-3">
                    {displayUsers.map((user, index) => (
                        <UserCard key={user.tg_userid} user={user} index={index} />
                    ))}

                    {/* Pagination (only when not searching) */}
                    {!searchQuery && (
                        <div className="flex justify-between items-center mt-6 py-2 px-2">
                            <button
                                className={`p-2 rounded-lg flex items-center ${currentPage > 1 ? 'text-[var(--text-color)] bg-white/10 hover:bg-white/20' : 'text-[var(--hint-color)] opacity-50 cursor-not-allowed'}`}
                                onClick={() => setCurrentPage(p => Math.max(1, p - 1))}
                                disabled={currentPage <= 1}
                            >
                                <ChevronLeft size={16} className="mr-1" />
                                <span>Назад</span>
                            </button>
                            <span className="text-[var(--hint-color)] text-sm">
                                {currentPage} / {Math.max(1, Math.ceil(totalUsers / USERS_PER_PAGE))}
                            </span>
                            <button
                                className={`p-2 rounded-lg flex items-center ${currentPage < Math.ceil(totalUsers / USERS_PER_PAGE) ? 'text-[var(--text-color)] bg-white/10 hover:bg-white/20' : 'text-[var(--hint-color)] opacity-50 cursor-not-allowed'}`}
                                onClick={() => setCurrentPage(p => p + 1)}
                                disabled={currentPage >= Math.ceil(totalUsers / USERS_PER_PAGE)}
                            >
                                <span>Вперед</span>
                                <ChevronRight size={16} className="ml-1" />
                            </button>
                        </div>
                    )}
                </div>
            )}

            {/* Modals */}
            <ConfirmModal
                isOpen={showDeleteConfirm}
                onClose={() => { setShowDeleteConfirm(false); setSelectedUser(null); }}
                onConfirm={handleDeleteUser}
                title="Удалить пользователя?"
                message={`Вы уверены, что хотите удалить пользователя ${selectedUser?.login || selectedUser?.tg_userid}? Это действие нельзя отменить.`}
                loading={actionLoading}
            />

            <AdminLevelModal
                isOpen={showLevelModal}
                onClose={() => { setShowLevelModal(false); setSelectedUser(null); }}
                user={selectedUser}
                onConfirm={handleChangeLevel}
                loading={actionLoading}
                currentAdminLevel={currentAdminLevel}
            />
        </motion.div>
    );
};

// Wrapper для BulkOperations с загрузкой пользователей
const BulkOperationsWrapper = ({ initData, currentAdminLevel }) => {
    const [users, setUsers] = useState([]);
    const [loading, setLoading] = useState(true);

    const fetchUsers = useCallback(async () => {
        setLoading(true);
        try {
            const response = await fetch(`/api/get_all_users?initData=${encodeURIComponent(initData)}&offset=0&limit=1000`);
            if (response.ok) {
                const data = await response.json();
                setUsers(Array.isArray(data) ? data : []);
            }
        } catch (error) {
            console.error('Error fetching users:', error);
        } finally {
            setLoading(false);
        }
    }, [initData]);

    useEffect(() => {
        fetchUsers();
    }, [fetchUsers]);

    if (loading) {
        return <SkeletonUserList count={5} />;
    }

    return (
        <BulkOperations
            initData={initData}
            users={users}
            currentAdminLevel={currentAdminLevel}
            onRefresh={fetchUsers}
        />
    );
};

// Wrapper для DataExport с загрузкой групп
const DataExportWrapper = ({ initData }) => {
    const [groups, setGroups] = useState([]);

    useEffect(() => {
        const fetchGroups = async () => {
            try {
                const response = await fetch(`/api/get_available_groups?initData=${encodeURIComponent(initData)}`);
                if (response.ok) {
                    const data = await response.json();
                    setGroups(data.groups || []);
                }
            } catch (error) {
                console.error('Error fetching groups:', error);
            }
        };
        fetchGroups();
    }, [initData]);

    return <DataExport initData={initData} availableGroups={groups} />;
};

// Главный компонент AdminPanel
const AdminPanel = ({ onBack, initData, adminLevel = 1 }) => {
    const [stats, setStats] = useState(null);
    const [statsLoading, setStatsLoading] = useState(true);
    const [activeTab, setActiveTab] = useState('dashboard');

    useEffect(() => {
        const fetchStats = async () => {
            setStatsLoading(true);
            try {
                const response = await fetch(`/api/admin/stats?initData=${encodeURIComponent(initData)}`);
                if (response.ok) {
                    const data = await response.json();
                    setStats(data);
                }
            } catch (error) {
                console.error('Error fetching stats:', error);
            } finally {
                setStatsLoading(false);
            }
        };
        fetchStats();
    }, [initData]);

    const StatCard = ({ icon: Icon, label, value, color = 'blue' }) => (
        <div className="p-4 rounded-xl glass border border-white/10">
            <div className="flex items-center">
                <div className={`p-2 mr-3 rounded-lg bg-${color}-500/20 text-${color}-500`}>
                    <Icon size={20} />
                </div>
                <div>
                    <div className="text-[var(--hint-color)] text-sm">{label}</div>
                    <div className="text-[var(--text-color)] text-xl font-bold">
                        {statsLoading ? <Loader2 className="animate-spin" size={20} /> : value}
                    </div>
                </div>
            </div>
        </div>
    );

    return (
        <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            className="p-4 w-full max-w-md mx-auto min-h-screen flex flex-col bg-[var(--bg-color)]"
        >
            {/* Header */}
            <div className="p-4 mb-6 rounded-2xl glass border border-white/10 flex items-center justify-between shadow-lg">
                <div className="flex items-center">
                    <motion.button
                        whileHover={{ scale: 1.1 }}
                        whileTap={{ scale: 0.9 }}
                        className="mr-3 p-2 rounded-full hover:bg-white/10 transition-colors text-[var(--text-color)]"
                        onClick={onBack}
                    >
                        <ArrowLeft size={20} />
                    </motion.button>
                    <h2 className="text-xl text-[var(--text-color)] font-bold">Админ панель</h2>
                </div>
                <div className="px-2 py-1 rounded-lg bg-[var(--button-color)]/20 text-[var(--button-color)] text-xs font-medium">
                    {ADMIN_LEVELS[adminLevel]?.name || `Lvl ${adminLevel}`}
                </div>
            </div>

            {/* Tabs */}
            <div className="flex mb-6 border-b border-white/10 overflow-x-auto no-scrollbar">
                {[
                    { id: 'dashboard', label: 'Дашборд', icon: Activity },
                    { id: 'users', label: 'Пользователи', icon: Users },
                    { id: 'admins', label: 'Админы', icon: ShieldCheck },
                    { id: 'analytics', label: 'Аналитика', icon: BarChart3, minLevel: 3 },
                    { id: 'bulk', label: 'Массовые', icon: UsersRound, minLevel: 3 },
                    { id: 'export', label: 'Экспорт', icon: Download, minLevel: 3 },
                    { id: 'import', label: 'Импорт', icon: Upload, minLevel: 4 },
                    { id: 'audit', label: 'Аудит', icon: History, minLevel: 4 },
                    { id: 'actions', label: 'Логи', icon: FileText, minLevel: 3 },
                ].filter(tab => !tab.minLevel || adminLevel >= tab.minLevel).map((tab) => (
                    <button
                        key={tab.id}
                        className={`py-3 px-4 font-medium transition-all relative whitespace-nowrap flex items-center ${
                            activeTab === tab.id ? 'text-[var(--button-color)]' : 'text-[var(--hint-color)] hover:text-[var(--text-color)]'
                        }`}
                        onClick={() => setActiveTab(tab.id)}
                    >
                        <tab.icon size={14} className="mr-1.5" />
                        {tab.label}
                        {activeTab === tab.id && (
                            <motion.div
                                layoutId="activeTab"
                                className="absolute bottom-0 left-0 right-0 h-0.5 bg-[var(--button-color)]"
                            />
                        )}
                    </button>
                ))}
            </div>

            <AnimatePresence mode="wait">
                {/* Dashboard Tab */}
                {activeTab === 'dashboard' && (
                    <motion.div
                        key="dashboard"
                        initial={{ opacity: 0, x: 20 }}
                        animate={{ opacity: 1, x: 0 }}
                        exit={{ opacity: 0, x: -20 }}
                        transition={{ duration: 0.2 }}
                    >
                        {/* Stats Grid */}
                        <div className="grid grid-cols-2 gap-3 mb-6">
                            <StatCard
                                icon={Users}
                                label="Пользователей"
                                value={stats?.total_users || 0}
                            />
                            <StatCard
                                icon={UsersRound}
                                label="Групп"
                                value={stats?.total_groups || 0}
                            />
                            <StatCard
                                icon={ShieldCheck}
                                label="Админов"
                                value={stats?.total_admins || 0}
                            />
                            <StatCard
                                icon={Key}
                                label="С логином"
                                value={stats?.users_with_login || 0}
                            />
                        </div>

                        {/* Progress bar for users with login */}
                        {stats && (
                            <div className="p-4 mb-6 rounded-xl glass border border-white/10">
                                <div className="flex justify-between items-center mb-2">
                                    <span className="text-[var(--text-color)] font-medium">Активированные аккаунты</span>
                                    <span className="text-[var(--button-color)] font-bold">
                                        {stats.total_users > 0 ? Math.round((stats.users_with_login / stats.total_users) * 100) : 0}%
                                    </span>
                                </div>
                                <div className="h-2 rounded-full bg-white/10 overflow-hidden">
                                    <div
                                        className="h-full bg-[var(--button-color)] rounded-full transition-all duration-500"
                                        style={{ width: `${stats.total_users > 0 ? (stats.users_with_login / stats.total_users) * 100 : 0}%` }}
                                    />
                                </div>
                                <div className="flex justify-between mt-2 text-xs text-[var(--hint-color)]">
                                    <span>{stats.users_with_login} с логином</span>
                                    <span>{stats.total_users - stats.users_with_login} без логина</span>
                                </div>
                            </div>
                        )}

                        {/* Quick Actions */}
                        <div className="flex-grow flex flex-col space-y-3">
                            <motion.button
                                whileHover={{ scale: 1.02 }}
                                whileTap={{ scale: 0.98 }}
                                className="w-full rounded-xl p-4 flex items-center justify-between glass border border-white/10 hover:bg-white/5 transition-all"
                                onClick={() => setActiveTab('users')}
                            >
                                <div className="flex items-center">
                                    <Users className="w-5 h-5 mr-3 text-[var(--button-color)]" />
                                    <span className="text-[var(--text-color)] font-medium">Управление пользователями</span>
                                </div>
                                <ChevronRight className="w-5 h-5 text-[var(--hint-color)]" />
                            </motion.button>

                            <motion.button
                                whileHover={{ scale: 1.02 }}
                                whileTap={{ scale: 0.98 }}
                                className="w-full rounded-xl p-4 flex items-center justify-between glass border border-white/10 hover:bg-white/5 transition-all"
                                onClick={() => setActiveTab('admins')}
                            >
                                <div className="flex items-center">
                                    <ShieldCheck className="w-5 h-5 mr-3 text-[var(--button-color)]" />
                                    <span className="text-[var(--text-color)] font-medium">Управление админами</span>
                                </div>
                                <ChevronRight className="w-5 h-5 text-[var(--hint-color)]" />
                            </motion.button>
                        </div>
                    </motion.div>
                )}

                {/* Users Tab */}
                {activeTab === 'users' && (
                    <motion.div
                        key="users"
                        initial={{ opacity: 0, x: 20 }}
                        animate={{ opacity: 1, x: 0 }}
                        exit={{ opacity: 0, x: -20 }}
                        transition={{ duration: 0.2 }}
                    >
                        <UsersList initData={initData} currentAdminLevel={adminLevel} />
                    </motion.div>
                )}

                {/* Admins Tab */}
                {activeTab === 'admins' && (
                    <motion.div
                        key="admins"
                        initial={{ opacity: 0, x: 20 }}
                        animate={{ opacity: 1, x: 0 }}
                        exit={{ opacity: 0, x: -20 }}
                        transition={{ duration: 0.2 }}
                    >
                        <AdminsList initData={initData} currentAdminLevel={adminLevel} />
                    </motion.div>
                )}

                {/* Analytics Tab */}
                {activeTab === 'analytics' && (
                    <motion.div
                        key="analytics"
                        initial={{ opacity: 0, x: 20 }}
                        animate={{ opacity: 1, x: 0 }}
                        exit={{ opacity: 0, x: -20 }}
                        transition={{ duration: 0.2 }}
                    >
                        <AnalyticsDashboard initData={initData} />
                    </motion.div>
                )}

                {/* Bulk Operations Tab */}
                {activeTab === 'bulk' && (
                    <motion.div
                        key="bulk"
                        initial={{ opacity: 0, x: 20 }}
                        animate={{ opacity: 1, x: 0 }}
                        exit={{ opacity: 0, x: -20 }}
                        transition={{ duration: 0.2 }}
                    >
                        <BulkOperationsWrapper initData={initData} currentAdminLevel={adminLevel} />
                    </motion.div>
                )}

                {/* Export Tab */}
                {activeTab === 'export' && (
                    <motion.div
                        key="export"
                        initial={{ opacity: 0, x: 20 }}
                        animate={{ opacity: 1, x: 0 }}
                        exit={{ opacity: 0, x: -20 }}
                        transition={{ duration: 0.2 }}
                    >
                        <DataExportWrapper initData={initData} />
                    </motion.div>
                )}

                {/* Import Tab */}
                {activeTab === 'import' && (
                    <motion.div
                        key="import"
                        initial={{ opacity: 0, x: 20 }}
                        animate={{ opacity: 1, x: 0 }}
                        exit={{ opacity: 0, x: -20 }}
                        transition={{ duration: 0.2 }}
                    >
                        <BulkImport initData={initData} />
                    </motion.div>
                )}

                {/* Audit Tab */}
                {activeTab === 'audit' && (
                    <motion.div
                        key="audit"
                        initial={{ opacity: 0, x: 20 }}
                        animate={{ opacity: 1, x: 0 }}
                        exit={{ opacity: 0, x: -20 }}
                        transition={{ duration: 0.2 }}
                    >
                        <AuditLogViewer initData={initData} />
                    </motion.div>
                )}

                {/* User Actions Tab */}
                {activeTab === 'actions' && (
                    <motion.div
                        key="actions"
                        initial={{ opacity: 0, x: 20 }}
                        animate={{ opacity: 1, x: 0 }}
                        exit={{ opacity: 0, x: -20 }}
                        transition={{ duration: 0.2 }}
                    >
                        <UserActionLogs initData={initData} />
                    </motion.div>
                )}
            </AnimatePresence>
        </motion.div>
    );
};

export default AdminPanel;
