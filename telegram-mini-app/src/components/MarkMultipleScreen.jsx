import React, { useState, useEffect, useRef } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { Check, Search, X, Plus, AlertTriangle, ChevronLeft, QrCode, RefreshCw, Loader2 } from 'lucide-react';
import MarkingLoader from './MarkingLoader';
import { isDemoMode, demoDelay, DEMO_GROUP_USERS_RESPONSE, DEMO_AVAILABLE_GROUPS_RESPONSE } from '../demo/mockData';

// Modern Checkbox Component
const Checkbox = ({ checked, onChange, label }) => {
  return (
    <motion.div
      className="flex items-center cursor-pointer group"
      onClick={() => onChange && onChange(!checked)}
      whileTap={{ scale: 0.95 }}
    >
      <motion.div
        className={`w-6 h-6 rounded-lg flex items-center justify-center border-2 transition-colors ${
          checked
            ? 'bg-[var(--button-color)] border-[var(--button-color)]'
            : 'border-[var(--tg-theme-hint-color)]/30 bg-[var(--tg-theme-secondary-bg-color)] group-hover:border-[var(--button-color)]'
        }`}
        initial={false}
        animate={{
          scale: checked ? 1 : 1,
          backgroundColor: checked ? 'var(--button-color)' : 'var(--tg-theme-secondary-bg-color)'
        }}
      >
        <AnimatePresence>
          {checked && (
            <motion.div
              initial={{ scale: 0, opacity: 0 }}
              animate={{ scale: 1, opacity: 1 }}
              exit={{ scale: 0, opacity: 0 }}
              transition={{ type: "spring", stiffness: 300, damping: 20 }}
            >
              <Check size={14} className="text-white" strokeWidth={3} />
            </motion.div>
          )}
        </AnimatePresence>
      </motion.div>
      {label && <span className="ml-3 text-[var(--text-color)] font-medium">{label}</span>}
    </motion.div>
  );
};

// Search Modal Component
const GroupSearchModal = ({ isOpen, onClose, onSelectGroup, availableGroups, loadingGroups }) => {
  const [searchTerm, setSearchTerm] = useState('');
  const [filteredGroups, setFilteredGroups] = useState([]);

  useEffect(() => {
    if (availableGroups.length > 0) {
      setFilteredGroups(
        availableGroups.filter(group =>
          group.toLowerCase().includes(searchTerm.toLowerCase())
        )
      );
    }
  }, [searchTerm, availableGroups]);

  return (
    <AnimatePresence>
      {isOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            className="absolute inset-0 bg-black/60 backdrop-blur-sm"
            onClick={onClose}
          />
          <motion.div
            initial={{ scale: 0.9, opacity: 0, y: 20 }}
            animate={{ scale: 1, opacity: 1, y: 0 }}
            exit={{ scale: 0.9, opacity: 0, y: 20 }}
            className="glass w-full max-w-md rounded-2xl p-6 shadow-2xl relative z-10 overflow-hidden"
          >
            <div className="flex justify-between items-center mb-6">
              <h3 className="text-xl font-bold text-[var(--text-color)]">Выбрать группу</h3>
              <button
                className="p-2 rounded-full hover:bg-black/5 transition-colors text-[var(--text-color)]"
                onClick={onClose}
              >
                <X size={20} />
              </button>
            </div>

            <div className="relative mb-6">
              <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 text-gray-400" size={18} />
              <input
                type="text"
                placeholder="Поиск группы..."
                value={searchTerm}
                onChange={(e) => setSearchTerm(e.target.value)}
                className="w-full pl-10 pr-4 py-3 rounded-xl border border-[var(--tg-theme-hint-color)]/20 bg-[var(--tg-theme-bg-color)] focus:outline-none focus:ring-2 focus:ring-[var(--button-color)] transition-all text-[var(--text-color)] placeholder-[var(--tg-theme-hint-color)]"
              />
            </div>

            <div className="max-h-60 overflow-y-auto mb-6 pr-2 custom-scrollbar">
              {loadingGroups ? (
                <div className="flex justify-center items-center p-8 text-[var(--hint-color)]">
                  <Loader2 className="animate-spin mr-2" size={20} />
                  <span>Загрузка групп...</span>
                </div>
              ) : filteredGroups.length > 0 ? (
                <div className="grid grid-cols-1 gap-2">
                  {filteredGroups.map((group, index) => (
                    <motion.div
                      key={group}
                      initial={{ opacity: 0, x: -10 }}
                      animate={{ opacity: 1, x: 0 }}
                      transition={{ delay: index * 0.05 }}
                      className="p-3 rounded-xl hover:bg-[var(--button-color)] hover:text-white cursor-pointer transition-all duration-200 font-medium text-[var(--text-color)] bg-[var(--tg-theme-bg-color)]"
                      onClick={() => onSelectGroup(group)}
                    >
                      {group}
                    </motion.div>
                  ))}
                </div>
              ) : (
                <div className="text-center p-8 text-[var(--hint-color)]">
                  {searchTerm ? 'Группа не найдена' : 'Нет доступных групп'}
                </div>
              )}
            </div>

            <div className="flex justify-end">
              <motion.button
                whileHover={{ scale: 1.02 }}
                whileTap={{ scale: 0.98 }}
                className="px-6 py-2.5 rounded-xl bg-[var(--button-color)] text-white font-medium shadow-lg shadow-blue-500/20"
                onClick={onClose}
              >
                Закрыть
              </motion.button>
            </div>
          </motion.div>
        </div>
      )}
    </AnimatePresence>
  );
};

// Group Tab Component
const GroupTab = ({ groupName, isActive, onClick, onClose, isMainGroup, isLoading }) => {
  return (
    <motion.div
      layout
      initial={{ opacity: 0, scale: 0.8 }}
      animate={{ opacity: 1, scale: 1 }}
      exit={{ opacity: 0, scale: 0.8 }}
      className={`relative flex items-center px-4 py-2.5 rounded-full cursor-pointer mr-2 mb-2 transition-all border ${
        isActive 
          ? 'bg-[var(--button-color)] text-white border-[var(--button-color)] shadow-md' 
          : 'bg-[var(--tg-theme-secondary-bg-color)] text-[var(--text-color)] border-transparent hover:bg-[var(--tg-theme-hint-color)]/10'
      }`}
      onClick={onClick}
    >
      <span className="truncate max-w-[100px] text-sm font-medium">{groupName}</span>
      {isLoading && (
        <Loader2 className="animate-spin ml-2" size={14} />
      )}
      {!isMainGroup && (
        <button
          className={`ml-2 p-0.5 rounded-full ${isActive ? 'hover:bg-white/20' : 'hover:bg-black/10'}`}
          onClick={(e) => {
            e.stopPropagation();
            onClose();
          }}
        >
          <X size={14} />
        </button>
      )}
    </motion.div>
  );
};

// Add Tab Button Component
const AddTabButton = ({ onClick }) => {
  return (
    <motion.button
      whileHover={{ scale: 1.1, rotate: 90 }}
      whileTap={{ scale: 0.9 }}
      className="flex items-center justify-center w-10 h-10 rounded-full bg-[var(--tg-theme-secondary-bg-color)] text-[var(--text-color)] hover:bg-[var(--button-color)] hover:text-white transition-colors shadow-sm mb-2"
      onClick={onClick}
    >
      <Plus size={20} />
    </motion.button>
  );
};

// Warning Dialog Component
const WarningDialog = ({ isOpen, onConfirm, onCancel }) => {
  return (
    <AnimatePresence>
      {isOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            className="absolute inset-0 bg-black/60 backdrop-blur-sm"
            onClick={onCancel}
          />
          <motion.div
            initial={{ scale: 0.9, opacity: 0 }}
            animate={{ scale: 1, opacity: 1 }}
            exit={{ scale: 0.9, opacity: 0 }}
            className="glass w-full max-w-md rounded-2xl p-6 shadow-2xl relative z-10 border-l-4 border-yellow-500"
          >
            <div className="flex flex-col items-center text-center mb-6">
              <div className="w-16 h-16 rounded-full bg-yellow-100 flex items-center justify-center mb-4 text-yellow-600">
                <AlertTriangle size={32} />
              </div>
              <h3 className="text-xl font-bold text-[var(--text-color)] mb-2">
                Предупреждение
              </h3>
              <p className="text-[var(--text-color)] opacity-80">
                Если группа, откуда ты выбрал пользователей, не записана на данную пару - могут возникнуть проблемы с отметкой людей из твоей группы.
              </p>
            </div>

            <div className="flex justify-center space-x-3">
              <motion.button
                whileHover={{ scale: 1.02 }}
                whileTap={{ scale: 0.98 }}
                className="px-5 py-2.5 rounded-xl bg-gray-200 text-gray-700 font-medium"
                onClick={onCancel}
              >
                Отмена
              </motion.button>
              <motion.button
                whileHover={{ scale: 1.02 }}
                whileTap={{ scale: 0.98 }}
                className="px-5 py-2.5 rounded-xl bg-[var(--button-color)] text-white font-medium shadow-lg shadow-blue-500/20"
                onClick={onConfirm}
              >
                Продолжить
              </motion.button>
            </div>
          </motion.div>
        </div>
      )}
    </AnimatePresence>
  );
};

// Utility function to sort students alphabetically
const sortStudentsByName = (students) => {
  return [...students].sort((a, b) => {
    const nameA = a.fio?.toLowerCase() || '';
    const nameB = b.fio?.toLowerCase() || '';
    return nameA.localeCompare(nameB);
  });
};

// Функция проверки валидности данных студента
const isValidStudent = (student) => {
  return student && student.tg_id && student.fio && typeof student.fio === 'string';
};

const MarkMultipleScreen = ({ onBack, onSubmit, initData, onApiError }) => {
  // Constants - moved inside component scope
  const maxApiCalls = 3;  // Сохраняем максимальное количество попыток (для обратной совместимости)

  // Функция для принудительного обновления данных
  const forceRefresh = () => {
    // Безопасно сбрасываем счетчики API
    apiCallTracker.reset('main');
    setError(''); // Очищаем ошибки
    fetchStudents(); // Перезапускаем загрузку
  };

  // State for user's group
  const [selectedStudents, setSelectedStudents] = useState([]);
  const [students, setStudents] = useState([]);
  const [loading, setLoading] = useState(true);
  const [backgroundLoading, setBackgroundLoading] = useState(false);
  const [error, setError] = useState('');
  const [loadingProgress, setLoadingProgress] = useState({
    message: "Загрузка списка студентов...",
    progress: 0
  });
  const [isScanning, setIsScanning] = useState(false);

  // State for tabs and groups
  const [activeGroupIndex, setActiveGroupIndex] = useState(0);
  const [additionalGroups, setAdditionalGroups] = useState([]);
  const [showGroupSearch, setShowGroupSearch] = useState(false);
  const [availableGroups, setAvailableGroups] = useState([]);
  const [loadingGroups, setLoadingGroups] = useState(false);
  const [showWarningDialog, setShowWarningDialog] = useState(false);

  // State for tracking loading status for each group
  const [groupLoadingStates, setGroupLoadingStates] = useState({
    main: false
  });

  // Хелперы для безопасной работы со счетчиками API запросов
  const apiCallTracker = (() => {
    // Создаем замыкание для безопасного доступа к счетчикам
    const counters = {}; // Локальное безопасное хранилище

    return {
      reset: (group = 'main') => {
        counters[group] = 0;
      },

      increment: (group = 'main') => {
        counters[group] = (counters[group] || 0) + 1;
        return counters[group];
      },

      getCount: (group = 'main') => {
        return counters[group] || 0;
      },

      isMaxReached: (group = 'main') => {
        return (counters[group] || 0) >= maxApiCalls;
      },

      remove: (group) => {
        if (group && group !== 'main' && counters[group] !== undefined) {
          delete counters[group];
        }
      }
    };
  })();

  // State for tracking students across groups
  const [groupStudents, setGroupStudents] = useState({
    // Your group's students will be stored here with the key 'main'
    main: [],
    // Other groups will be stored with their group name as key
  });

  const [groupSelectedStudents, setGroupSelectedStudents] = useState({
    // Selected students from your group
    main: [],
    // Selected students from other groups
  });

  // The following functions have been replaced by fetchFirstBatchForGroup and fetchNextBatchForGroup
  // These functions are kept as empty implementations for compatibility with any code that might call them
  const scheduleBackgroundFetchesForGroup = (groupName, initialStudents) => {
    // No longer used - for backward compatibility only
  };

  const fetchGroupStudentsInBackground = async (groupName, currentStudentList) => {
    // No longer used - for backward compatibility only
  };

  // Load user's group students on component mount
  useEffect(() => {
    fetchStudents();
    fetchAvailableGroups();
  }, [initData]);

  // Function to fetch available groups
  const fetchAvailableGroups = async () => {
    setLoadingGroups(true);
    try {
      // Demo mode check
      if (isDemoMode()) {
        await demoDelay();
        setAvailableGroups(DEMO_AVAILABLE_GROUPS_RESPONSE.groups || []);
        return;
      }

      const response = await fetch(`/api/get_available_groups?initData=${encodeURIComponent(initData)}`);

      if (!response.ok) {
        throw new Error('Не удалось загрузить список групп');
      }

      const data = await response.json();
      setAvailableGroups(data.groups || []);
    } catch (error) {
      console.error('Ошибка загрузки групп:', error);
    } finally {
      setLoadingGroups(false);
    }
  };

  // Function to fetch user's group students with initial load and background updates
  const fetchStudents = async () => {
    setLoading(true);
    setError('');

    // Сбрасываем счетчик API вызовов для основной группы
    apiCallTracker.reset('main');

    try {
      // Один запрос - загружаем студентов
      await fetchInitialStudents();

      // Завершаем загрузку сразу после первого запроса
      setLoading(false);
    } catch (error) {
      console.error('Ошибка загрузки студентов:', error);

      if (!students.length) {
        setError('Ошибка при загрузке списка студентов. Попробуйте обновить страницу.');
      }

      // If we have data from initial fetch, finish loading
      if (students.length > 0) {
        setLoading(false);
      }
    }
  };

  // Function for initial fetch - critical path
  const fetchInitialStudents = async () => {
    try {
      apiCallTracker.increment('main');

      let data;

      // Demo mode check
      if (isDemoMode()) {
        await demoDelay();
        data = DEMO_GROUP_USERS_RESPONSE;
      } else {
        // Request to get group users with timeout
        const controller = new AbortController();
        const timeoutId = setTimeout(() => controller.abort(), 8000); // 8 секунд таймаут

        const response = await fetch(`/api/get_group_users?initData=${encodeURIComponent(initData)}`, {
          signal: controller.signal
        }).catch(err => {
          console.error('Fetch error:', err);
          throw new Error('Не удалось загрузить список студентов: проблема с сетью');
        });

        clearTimeout(timeoutId);

        if (!response.ok) {
          throw new Error(`Не удалось загрузить список студентов: ${response.status}`);
        }

        data = await response.json().catch(err => {
          console.error('JSON parse error:', err);
          throw new Error('Не удалось обработать ответ сервера');
        });
      }

      // Проверка структуры данных
      if (!data || !Array.isArray(data.users)) {
        console.error('Unexpected data format:', data);
        throw new Error('Неожиданный формат данных от сервера');
      }

      // Filter out students with allowConfirm set to false and invalid students
      const filteredStudents = data.users
          .filter(student => student.allowConfirm !== false)
          .filter(isValidStudent);

      // Sort students alphabetically
      const sortedStudents = sortStudentsByName(filteredStudents);

      setStudents(sortedStudents);

      // Update groupStudents
      setGroupStudents(prev => ({
        ...prev,
        main: sortedStudents
      }));

      // Auto-select all students
      const allStudentIds = sortedStudents.map(s => s.tg_id);
      setGroupSelectedStudents(prev => {
        const updated = {
          ...prev,
          main: allStudentIds
        };

        // Пересчитываем selectedStudents из актуального состояния groupSelectedStudents
        const allSelected = Object.values(updated).flat();
        setSelectedStudents(allSelected);

        return updated;
      });

    } catch (error) {
      console.error(`Ошибка первичной загрузки студентов:`, error);
      throw error;
    }
  };

  // Function to fetch all background calls (replacing scheduleBackgroundFetches)
  const fetchAllBackgroundCalls = async () => {
    try {
      // Second API call
      await fetchNextBatch(2);

      // Update progress
      setLoadingProgress({
        message: "Загрузка дополнительных студентов (2/2)...",
        progress: 66
      });

      // Third API call
      await fetchNextBatch(3);

      // All calls completed successfully
      setLoading(false);

    } catch (error) {
      console.error('Ошибка при выполнении фоновых вызовов:', error);

      // If we got some data, we can still show the UI
      if (students.length > 0) {
        setLoading(false);
      } else {
        throw error; // Propagate error if we have no data at all
      }
    }
  };

  // Function to fetch the next batch of students
  const fetchNextBatch = async (batchNumber) => {
    return new Promise((resolve, reject) => {
      // In demo mode, just resolve immediately - no additional batches needed
      if (isDemoMode()) {
        resolve();
        return;
      }

      if (apiCallTracker.isMaxReached('main')) {
        resolve(); // No more calls needed
        return;
      }

      const attempt = apiCallTracker.increment('main');

      // Request with timeout
      const controller = new AbortController();
      const timeoutId = setTimeout(() => {
        controller.abort();
        reject(new Error(`Превышено время ожидания для запроса ${attempt}`));
      }, 8000);

      fetch(`/api/get_group_users?initData=${encodeURIComponent(initData)}`, {
        signal: controller.signal
      })
          .then(response => {
            clearTimeout(timeoutId);

            if (!response.ok) {
              throw new Error(`Ошибка сервера: ${response.status}`);
            }

            return response.json();
          })
          .then(data => {
            if (!data || !Array.isArray(data.users)) {
              console.warn('Неожиданный формат данных:', data);
              resolve(); // Continue despite the error
              return;
            }

            // Filter out students with allowConfirm set to false and invalid students
            const filteredStudents = data.users
                .filter(student => student.allowConfirm !== false)
                .filter(isValidStudent);

            // Check if we got new students
            const currentStudentIds = new Set(students.map(student => student.tg_id));

            // Find new students that aren't in current list
            const newStudents = filteredStudents.filter(student => !currentStudentIds.has(student.tg_id));

            if (newStudents.length > 0) {
              // We have new students - update lists
              const updatedStudents = [...students, ...newStudents];
              const sortedStudents = sortStudentsByName(updatedStudents);

              // Update both state variables
              setStudents(sortedStudents);
              setGroupStudents(prev => ({
                ...prev,
                main: sortedStudents
              }));

              // Auto-select new students
              const newStudentIds = newStudents.map(s => s.tg_id);
              setGroupSelectedStudents(prev => {
                const updated = {
                  ...prev,
                  main: [...(prev.main || []), ...newStudentIds]
                };

                // Пересчитываем selectedStudents из актуального состояния
                const allSelected = Object.values(updated).flat();
                setSelectedStudents(allSelected);

                return updated;
              });

              // Clear error if we were successful in getting data
              if (error) {
                setError('');
              }
            }

            resolve();
          })
          .catch(error => {
            clearTimeout(timeoutId);
            console.error(`Ошибка запроса ${attempt}:`, error);

            // Don't fail the entire process for a single request
            // Instead, we resolve with what we have so the next request can proceed
            resolve();
          });
    });
  };

  // Function to fetch students from another group - single request like main group
  const fetchOtherGroupStudents = async (groupName) => {
    // Set loading state for this group
    setGroupLoadingStates(prev => ({...prev, [groupName]: true}));

    // Initialize API call count for this group
    apiCallTracker.reset(groupName);

    // Show group-specific loading message
    setLoadingProgress({
      message: `Загрузка студентов группы ${groupName}...`,
      progress: 0
    });

    // Set loading true to show the loading screen
    setLoading(true);

    try {
      // Single API call - same as main group
      const students = await fetchFirstBatchForGroup(groupName);

      // Loading completed
      setGroupLoadingStates(prev => ({...prev, [groupName]: false}));
      setLoading(false);

      return students;
    } catch (error) {
      console.error(`Ошибка загрузки студентов группы ${groupName}:`, error);

      // Показываем более понятное сообщение об ошибке
      if (error.name === 'AbortError') {
        setError(`Превышено время ожидания при загрузке группы ${groupName}. Попробуйте ещё раз.`);
      } else {
        setError(`Ошибка при загрузке студентов группы ${groupName}. ${error.message}`);
      }

      // If all attempts failed, remove the group
      if ((!groupStudents[groupName] || groupStudents[groupName].length === 0)) {
        setAdditionalGroups(prev => prev.filter(g => g !== groupName));

        // If active group is being removed, switch to main
        if (activeGroupIndex === additionalGroups.indexOf(groupName) + 1) {
          setActiveGroupIndex(0);
        }
      }

      // End loading state
      setGroupLoadingStates(prev => ({...prev, [groupName]: false}));
      setLoading(false);

      return groupStudents[groupName] || [];
    }
  };

  // Function to fetch the first batch of students for a group
  const fetchFirstBatchForGroup = async (groupName) => {
    try {
      apiCallTracker.increment(groupName);

      let data;

      // Demo mode check - return demo data for other groups too
      if (isDemoMode()) {
        await demoDelay();
        // Generate mock data for other group (with hidden FIO)
        data = {
          users: DEMO_GROUP_USERS_RESPONSE.users.map((user, idx) => ({
            ...user,
            tg_id: user.tg_id + 1000 + idx, // Different IDs for other group
          }))
        };
      } else {
        // Request to get group users with timeout
        const controller = new AbortController();
        const timeoutId = setTimeout(() => controller.abort(), 8000);

        const response = await fetch(
            `/api/get_other_group_users?initData=${encodeURIComponent(initData)}&group_name=${encodeURIComponent(groupName)}`,
            { signal: controller.signal }
        ).catch(err => {
          console.error('Fetch error:', err);
          throw new Error(`Не удалось загрузить студентов группы ${groupName}: проблема с сетью`);
        });

        clearTimeout(timeoutId);

        if (!response.ok) {
          throw new Error(`Не удалось загрузить студентов группы ${groupName}: ${response.status}`);
        }

        data = await response.json().catch(err => {
          console.error('JSON parse error:', err);
          throw new Error('Не удалось обработать ответ сервера');
        });
      }

      // Check data format
      if (!data || !Array.isArray(data.users)) {
        console.warn(`Неожиданный формат данных для группы ${groupName}:`, data);
        throw new Error(`Ошибка при загрузке студентов группы ${groupName} - неверный формат данных`);
      }

      // Filter and sort students
      const filteredStudents = data.users
          .filter(student => student.allowConfirm !== false)
          .filter(isValidStudent);

      const sortedStudents = sortStudentsByName(filteredStudents);

      // Update groupStudents
      setGroupStudents(prev => ({
        ...prev,
        [groupName]: sortedStudents
      }));

      // Initialize selected students for this group (Auto-select all)
      const allStudentIds = sortedStudents.map(s => s.tg_id);
      setGroupSelectedStudents(prev => {
        const updated = {
          ...prev,
          [groupName]: allStudentIds
        };

        // Пересчитываем selectedStudents из актуального состояния groupSelectedStudents
        const allSelected = Object.values(updated).flat();
        setSelectedStudents(allSelected);

        return updated;
      });

      // Clear error if successful
      setError('');

      return sortedStudents;
    } catch (error) {
      console.error(`Ошибка первичной загрузки студентов группы ${groupName}:`, error);
      throw error;
    }
  };

  // Function to fetch subsequent batches for a group
  const fetchNextBatchForGroup = async (groupName, batchNumber, currentStudents) => {
    return new Promise((resolve, reject) => {
      // In demo mode, just resolve immediately - no additional batches needed
      if (isDemoMode()) {
        resolve();
        return;
      }

      if (apiCallTracker.isMaxReached(groupName)) {
        resolve(); // No more calls needed
        return;
      }

      const attempt = apiCallTracker.increment(groupName);

      // Request with timeout
      const controller = new AbortController();
      const timeoutId = setTimeout(() => {
        controller.abort();
        // Don't fail completely on timeout, just resolve with what we have
        resolve();
      }, 8000);

      fetch(`/api/get_other_group_users?initData=${encodeURIComponent(initData)}&group_name=${encodeURIComponent(groupName)}`, {
        signal: controller.signal
      })
          .then(response => {
            clearTimeout(timeoutId);

            if (!response.ok) {
              throw new Error(`Ошибка сервера: ${response.status}`);
            }

            return response.json();
          })
          .then(data => {
            if (!data || !Array.isArray(data.users)) {
              console.warn(`Неожиданный формат данных для группы ${groupName}:`, data);
              resolve(); // Continue despite error
              return;
            }

            // Filter students
            const filteredStudents = data.users
                .filter(student => student.allowConfirm !== false)
                .filter(isValidStudent);

            // Check for new students
            const currentStudentIds = new Set((groupStudents[groupName] || currentStudents || []).map(student => student.tg_id));
            const newStudents = filteredStudents.filter(student => !currentStudentIds.has(student.tg_id));

            if (newStudents.length > 0) {
              // Update with new students
              const updatedStudents = [...(groupStudents[groupName] || currentStudents || []), ...newStudents];
              const sortedStudents = sortStudentsByName(updatedStudents);

              // Update groupStudents
              setGroupStudents(prev => ({
                ...prev,
                [groupName]: sortedStudents
              }));

              // Auto-select new students
              const newStudentIds = newStudents.map(s => s.tg_id);
              setGroupSelectedStudents(prev => {
                const updated = {
                  ...prev,
                  [groupName]: [...(prev[groupName] || []), ...newStudentIds]
                };

                // Пересчитываем selectedStudents из актуального состояния
                const allSelected = Object.values(updated).flat();
                setSelectedStudents(allSelected);

                return updated;
              });

              // Clear error if successful
              if (error) {
                setError('');
              }
            }

            resolve();
          })
          .catch(error => {
            clearTimeout(timeoutId);
            console.error(`Ошибка запроса ${attempt} для группы ${groupName}:`, error);

            // Don't fail the entire process for a single request error
            // Just resolve with what we have
            resolve();
          });
    });
  };

  // Handler for toggling student selection in current active group
  const handleStudentToggle = (studentId) => {
    const currentGroupKey = activeGroupIndex === 0 ? 'main' : additionalGroups[activeGroupIndex - 1];

    setGroupSelectedStudents(prev => {
      const updatedGroup = { ...prev };

      if (updatedGroup[currentGroupKey].includes(studentId)) {
        updatedGroup[currentGroupKey] = updatedGroup[currentGroupKey].filter(id => id !== studentId);
      } else {
        updatedGroup[currentGroupKey] = [...updatedGroup[currentGroupKey], studentId];
      }

      // Update the main selectedStudents array for backward compatibility
      const allSelected = Object.values(updatedGroup).flat();
      setSelectedStudents(allSelected);

      return updatedGroup;
    });
  };

  // Function to select or deselect all students in the active group
  const toggleSelectAll = () => {
    const currentGroupKey = activeGroupIndex === 0 ? 'main' : additionalGroups[activeGroupIndex - 1];
    const currentGroupStudents = groupStudents[currentGroupKey] || [];

    setGroupSelectedStudents(prev => {
      const updatedGroup = { ...prev };

      if (updatedGroup[currentGroupKey].length === currentGroupStudents.length) {
        // If all are selected, deselect all
        updatedGroup[currentGroupKey] = [];
      } else {
        // Otherwise, select all
        updatedGroup[currentGroupKey] = currentGroupStudents.map(student => student.tg_id);
      }

      // Update the main selectedStudents array for backward compatibility
      const allSelected = Object.values(updatedGroup).flat();
      setSelectedStudents(allSelected);

      return updatedGroup;
    });
  };

  // Handler for adding a new group tab
  const handleAddGroup = async (groupName) => {
    if (!groupName || additionalGroups.includes(groupName)) {
      return;
    }

    // Add the group to the list
    setAdditionalGroups(prev => [...prev, groupName]);

    // Set it as active (we need to use the updated length after adding)
    setActiveGroupIndex(additionalGroups.length + 1);

    // Close the search modal
    setShowGroupSearch(false);

    // Fetch students for this group with full loading
    await fetchOtherGroupStudents(groupName);
  };

  // Handler for removing a group tab
  const handleRemoveGroup = (groupName) => {
    const groupIndex = additionalGroups.indexOf(groupName) + 1; // +1 because 0 is main group

    // Remove the group
    setAdditionalGroups(prev => prev.filter(g => g !== groupName));

    // If the active group is being removed, switch to main group
    if (activeGroupIndex === groupIndex) {
      setActiveGroupIndex(0);
    } else if (activeGroupIndex > groupIndex) {
      // If the active group is after the removed one, update index
      setActiveGroupIndex(activeGroupIndex - 1);
    }

    // Remove the group's students and selections
    setGroupStudents(prev => {
      const updated = { ...prev };
      delete updated[groupName];
      return updated;
    });

    setGroupSelectedStudents(prev => {
      const updated = { ...prev };
      delete updated[groupName];

      // Update the main selectedStudents array for backward compatibility
      const allSelected = Object.values(updated).flat();
      setSelectedStudents(allSelected);

      return updated;
    });

    // Remove loading state for this group
    setGroupLoadingStates(prev => {
      const updated = { ...prev };
      delete updated[groupName];
      return updated;
    });

    // Remove API call count for this group
    apiCallTracker.remove(groupName);
  };

  const handleStartMarkingClick = () => {
    if (selectedStudents.length > 0) {
      // Check if students from multiple groups are selected
      const hasMultipleGroupSelections = Object.keys(groupSelectedStudents).filter(
          key => groupSelectedStudents[key].length > 0
      ).length > 1;

      if (hasMultipleGroupSelections) {
        // Show warning dialog
        setShowWarningDialog(true);
      } else {
        // Proceed with QR scanning
        startQrScanning();
      }
    } else {
      setError("Выберите хотя бы одного студента");
    }
  };

  // Function to start QR scanning process
  const startQrScanning = () => {
    // Use Telegram QR scanner
    if (window.Telegram?.WebApp) {
      setIsScanning(true);

      // Add event listener for popup closing
      const handlePopupClosed = () => {
        setIsScanning(false);
        // Remove the event listener after it's triggered
        window.Telegram.WebApp.offEvent('scanQrPopupClosed', handlePopupClosed);
      };

      // Listen for the popup being closed
      window.Telegram.WebApp.onEvent('scanQrPopupClosed', handlePopupClosed);

      window.Telegram.WebApp.showScanQrPopup(
          {
            text: 'Отсканируйте QR-код для отметки студентов'
          },
          (text) => {
            // Remove the close event listener since we got a result
            window.Telegram.WebApp.offEvent('scanQrPopupClosed', handlePopupClosed);

            // Close QR scanner
            window.Telegram.WebApp.closeScanQrPopup();

            // Check received data
            if (!text) {
              setError("Ошибка сканирования QR-кода");
              setIsScanning(false);
              return true;
            }

            // Navigate to marking screen with selected students and QR URL
            onSubmit({
              selectedStudents,
              url: text
            });

            return true;
          }
      );
    } else {
      setError("Функция сканирования QR недоступна");
    }
  };

  if (loading) {
    return <MarkingLoader
        status="checking"
        message={loadingProgress.message}
        progress={loadingProgress.progress}
    />;
  }

  // Get current group's students
  const currentGroupKey = activeGroupIndex === 0 ? 'main' : additionalGroups[activeGroupIndex - 1];
  const currentStudents = groupStudents[currentGroupKey] || [];
  const currentSelectedStudents = groupSelectedStudents[currentGroupKey] || [];
  const isCurrentGroupLoading = groupLoadingStates[currentGroupKey] || false;

  return (
    <motion.div 
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      exit={{ opacity: 0, y: -20 }}
      className="p-4 w-full max-w-md mx-auto min-h-screen flex flex-col bg-[var(--bg-color)]"
    >
      {/* Header */}
      <motion.div 
        initial={{ y: -20, opacity: 0 }}
        animate={{ y: 0, opacity: 1 }}
        className="glass p-4 mb-6 text-center rounded-2xl shadow-sm"
      >
        <h2 className="text-xl font-bold text-[var(--text-color)]">Выбери кого отметить</h2>
      </motion.div>

      {/* Error notification with refresh button */}
      <AnimatePresence>
        {error && (
          <motion.div
            initial={{ height: 0, opacity: 0 }}
            animate={{ height: 'auto', opacity: 1 }}
            exit={{ height: 0, opacity: 0 }}
            className="mb-4 p-4 rounded-xl shadow-sm bg-red-500 text-white flex items-center justify-between"
          >
            <div className="flex-1 text-sm font-medium">{error}</div>
            <button
              className="ml-3 p-2 rounded-full bg-white/20 hover:bg-white/30 transition-colors"
              onClick={forceRefresh}
              title="Обновить"
            >
              <RefreshCw size={18} />
            </button>
          </motion.div>
        )}
      </AnimatePresence>

      {/* Group tabs */}
      <div className="flex overflow-x-auto mb-4 no-scrollbar pb-2">
        <GroupTab
          groupName="Твоя группа"
          isActive={activeGroupIndex === 0}
          onClick={() => setActiveGroupIndex(0)}
          onClose={() => {}} // Cannot close main group tab
          isMainGroup={true}
          isLoading={groupLoadingStates.main || false}
        />

        <AnimatePresence>
          {additionalGroups.map((group, index) => (
            <GroupTab
              key={group}
              groupName={group}
              isActive={activeGroupIndex === index + 1}
              onClick={() => setActiveGroupIndex(index + 1)}
              onClose={() => handleRemoveGroup(group)}
              isMainGroup={false}
              isLoading={groupLoadingStates[group] || false}
            />
          ))}
        </AnimatePresence>

        <AddTabButton onClick={() => setShowGroupSearch(true)} />
      </div>

      {/* Scrollable student list */}
      <motion.div
        layout
        className="glass p-4 mb-4 rounded-2xl flex-grow overflow-y-auto max-h-[calc(100vh-270px)] custom-scrollbar relative"
      >
        {/* Group loading indicator */}
        <AnimatePresence>
          {isCurrentGroupLoading && (
            <motion.div 
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
              className="absolute top-4 right-4 text-[var(--button-color)]"
            >
              <Loader2 className="animate-spin" size={20} />
            </motion.div>
          )}
        </AnimatePresence>

        {currentStudents.length === 0 ? (
          <div className="flex flex-col items-center justify-center h-40 text-[var(--hint-color)]">
            <Search size={40} className="mb-2 opacity-50" />
            <p className="text-center text-sm">
              {activeGroupIndex === 0
                ? 'Нет доступных студентов для отметки в вашей группе'
                : `Нет студентов из группы ${additionalGroups[activeGroupIndex - 1]} в боте`}
            </p>
          </div>
        ) : (
          <>
            {/* Select All button */}
            <div className="flex items-center justify-between py-3 border-b border-gray-200/10 mb-2">
              <span className="text-[var(--text-color)] font-bold text-sm uppercase tracking-wider opacity-80">
                Выбрать всех
              </span>
              <Checkbox
                checked={currentSelectedStudents.length === currentStudents.length && currentStudents.length > 0}
                onChange={toggleSelectAll}
              />
            </div>

            {/* Student list */}
            <div className="space-y-1">
              {currentStudents.map((student, index) => (
                <motion.div
                  key={student.tg_id}
                  initial={{ opacity: 0, x: -10 }}
                  animate={{ opacity: 1, x: 0 }}
                  transition={{ delay: index * 0.03 }}
                  className="flex items-center justify-between py-3 px-2 rounded-xl hover:bg-black/5 transition-colors"
                >
                  <span className="text-[var(--text-color)] font-medium">
                    {activeGroupIndex === 0
                      ? (student.fio || `Студент ID ${student.tg_id}`)
                      : "ФИО скрыто для безопасности"}
                  </span>
                  <Checkbox
                    checked={currentSelectedStudents.includes(student.tg_id)}
                    onChange={() => handleStudentToggle(student.tg_id)}
                  />
                </motion.div>
              ))}
            </div>
          </>
        )}
      </motion.div>

      {/* Navigation buttons - fixed at bottom */}
      <div className="sticky bottom-0 pb-4 pt-2 flex justify-between space-x-3 bg-[var(--bg-color)] z-10">
        <motion.button
          whileHover={{ scale: 1.02 }}
          whileTap={{ scale: 0.98 }}
          className="flex-1 rounded-xl shadow-sm p-3.5 flex items-center justify-center glass text-[var(--text-color)] font-medium"
          onClick={onBack}
        >
          <ChevronLeft className="mr-2" size={20} />
          <span>Назад</span>
        </motion.button>

        <motion.button
          whileHover={{ scale: 1.02 }}
          whileTap={{ scale: 0.98 }}
          className={`flex-1 rounded-xl shadow-lg p-3.5 flex items-center justify-center font-medium transition-all ${
            selectedStudents.length === 0 
              ? 'bg-gray-200 text-gray-400 cursor-not-allowed' 
              : 'bg-[var(--button-color)] text-white shadow-blue-500/30'
          }`}
          onClick={handleStartMarkingClick}
          disabled={selectedStudents.length === 0 || isScanning}
        >
          {isScanning ? (
            <>
              <span className="mr-2">Сканирование...</span>
              <Loader2 className="animate-spin" size={20} />
            </>
          ) : (
            <>
              <span className="mr-2">Отметить</span>
              <QrCode size={20} />
            </>
          )}
        </motion.button>
      </div>

      {/* Group search modal */}
      <GroupSearchModal
        isOpen={showGroupSearch}
        onClose={() => setShowGroupSearch(false)}
        onSelectGroup={handleAddGroup}
        availableGroups={availableGroups.filter(group => !additionalGroups.includes(group))}
        loadingGroups={loadingGroups}
      />

      {/* Warning dialog */}
      <WarningDialog
        isOpen={showWarningDialog}
        onConfirm={() => {
          setShowWarningDialog(false);
          startQrScanning();
        }}
        onCancel={() => setShowWarningDialog(false)}
      />
    </motion.div>
  );
};

export default MarkMultipleScreen;

