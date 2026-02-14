/**
 * Virtual scroll list for efficient rendering of large user lists.
 */
import React, { useRef, useCallback } from 'react';
import { useVirtualizer } from '@tanstack/react-virtual';
import { User, UserCog, Trash2, CheckSquare, Square, Loader2 } from 'lucide-react';

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
 * Virtual user list with efficient rendering.
 */
const VirtualUserList = ({
    users,
    loading,
    error,
    currentAdminLevel = 0,
    selectedUsers = [],
    onSelectUser,
    onSelectAll,
    onEditLevel,
    onDelete,
    selectionMode = false,
    emptyMessage = 'Пользователи не найдены'
}) => {
    const parentRef = useRef(null);

    const rowVirtualizer = useVirtualizer({
        count: users.length,
        getScrollElement: () => parentRef.current,
        estimateSize: () => 80,
        overscan: 5,
    });

    const isAdmin = (adminLevel) => adminLevel && adminLevel !== 0;
    const isSelected = (userId) => selectedUsers.includes(userId);

    const handleSelect = useCallback((userId) => {
        if (onSelectUser) {
            onSelectUser(userId);
        }
    }, [onSelectUser]);

    if (loading) {
        return (
            <div className="flex justify-center items-center p-8 text-[var(--hint-color)]">
                <Loader2 className="animate-spin mr-2" size={20} />
                <span>Загрузка...</span>
            </div>
        );
    }

    if (error) {
        return (
            <div className="p-4 rounded-xl bg-red-500/10 text-red-500 text-center border border-red-500/20">
                {error}
            </div>
        );
    }

    if (users.length === 0) {
        return (
            <div className="p-8 rounded-xl glass text-center text-[var(--hint-color)] border border-white/10">
                {emptyMessage}
            </div>
        );
    }

    return (
        <div className="flex flex-col">
            {/* Select all header */}
            {selectionMode && onSelectAll && (
                <div className="flex items-center justify-between p-3 mb-2 rounded-xl glass border border-white/10">
                    <button
                        onClick={onSelectAll}
                        className="flex items-center text-[var(--text-color)] hover:text-[var(--button-color)] transition-colors"
                    >
                        {selectedUsers.length === users.length ? (
                            <CheckSquare size={18} className="mr-2 text-[var(--button-color)]" />
                        ) : (
                            <Square size={18} className="mr-2" />
                        )}
                        <span className="text-sm font-medium">
                            {selectedUsers.length === users.length ? 'Снять выбор' : 'Выбрать все'}
                        </span>
                    </button>
                    <span className="text-sm text-[var(--hint-color)]">
                        Выбрано: {selectedUsers.length} из {users.length}
                    </span>
                </div>
            )}

            {/* Virtual list container */}
            <div
                ref={parentRef}
                className="overflow-auto rounded-xl"
                style={{ height: '500px' }}
            >
                <div
                    style={{
                        height: `${rowVirtualizer.getTotalSize()}px`,
                        width: '100%',
                        position: 'relative',
                    }}
                >
                    {rowVirtualizer.getVirtualItems().map((virtualRow) => {
                        const user = users[virtualRow.index];
                        const selected = isSelected(user.tg_userid);

                        return (
                            <div
                                key={user.tg_userid}
                                data-index={virtualRow.index}
                                ref={rowVirtualizer.measureElement}
                                className="absolute top-0 left-0 w-full"
                                style={{
                                    transform: `translateY(${virtualRow.start}px)`,
                                }}
                            >
                                <div
                                    className={`p-4 mb-2 rounded-xl glass border-l-4 border-white/10 transition-all ${
                                        selected ? 'bg-[var(--button-color)]/10 border-l-[var(--button-color)]' : ''
                                    }`}
                                    style={{
                                        borderLeftColor: selected
                                            ? 'var(--button-color)'
                                            : isAdmin(user.admin_lvl)
                                                ? 'var(--button-color)'
                                                : 'var(--hint-color)'
                                    }}
                                >
                                    <div className="flex justify-between items-start">
                                        {/* Selection checkbox */}
                                        {selectionMode && (
                                            <button
                                                onClick={() => handleSelect(user.tg_userid)}
                                                className="mr-3 flex-shrink-0"
                                            >
                                                {selected ? (
                                                    <CheckSquare size={20} className="text-[var(--button-color)]" />
                                                ) : (
                                                    <Square size={20} className="text-[var(--hint-color)]" />
                                                )}
                                            </button>
                                        )}

                                        {/* User info */}
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
                                                <div className="text-[var(--hint-color)] text-sm mb-1">
                                                    {user.group_name}
                                                </div>
                                            )}
                                            {user.fio && user.login && (
                                                <div className="text-[var(--hint-color)] text-xs opacity-70">
                                                    {user.fio}
                                                </div>
                                            )}
                                            <div className="text-[var(--hint-color)] text-xs opacity-50 mt-1">
                                                ID: {user.tg_userid}
                                            </div>
                                        </div>

                                        {/* Actions */}
                                        {!selectionMode && currentAdminLevel >= 3 && (
                                            <div className="flex space-x-1 flex-shrink-0 ml-2">
                                                {onEditLevel && (
                                                    <button
                                                        onClick={() => onEditLevel(user)}
                                                        className="p-2 rounded-lg bg-white/10 text-[var(--hint-color)] hover:bg-white/20 hover:text-[var(--button-color)] transition-colors"
                                                        title="Изменить уровень"
                                                    >
                                                        <UserCog size={16} />
                                                    </button>
                                                )}
                                                {onDelete && (
                                                    <button
                                                        onClick={() => onDelete(user)}
                                                        className="p-2 rounded-lg bg-white/10 text-[var(--hint-color)] hover:bg-red-500/20 hover:text-red-500 transition-colors"
                                                        title="Удалить"
                                                    >
                                                        <Trash2 size={16} />
                                                    </button>
                                                )}
                                            </div>
                                        )}
                                    </div>
                                </div>
                            </div>
                        );
                    })}
                </div>
            </div>

            {/* Stats footer */}
            <div className="mt-2 text-center text-sm text-[var(--hint-color)]">
                Всего пользователей: {users.length}
            </div>
        </div>
    );
};

export default VirtualUserList;
