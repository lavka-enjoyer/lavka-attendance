import {
    API_ENDPOINTS,
    apiGet,
    apiPost,
    apiPatch,
    apiDelete,
    getFullApiUrl
} from '../config/api';
import { getModifiedUserAgent } from '../utils/telegramUtils';
import {
    isDemoMode,
    demoDelay,
    DEMO_USER,
    DEMO_SCHEDULE,
    DEMO_POINTS,
    DEMO_GROUP_USERS,
    DEMO_GROUP_UNIVERSITY_STATUS,
    DEMO_LESSON_ATTENDANCE,
    DEMO_AVAILABLE_GROUPS,
    DEMO_LESSONS_CALENDAR,
    DEMO_MARKING_SESSION,
    DEMO_LESSONS_COST,
} from '../demo/mockData';

/**
 * Константы типов ошибок
 */
export const ERROR_TYPES = {
    LOGIN_REQUIRED: 'LOGIN_REQUIRED',
    ACCESS_DENIED: 'ACCESS_DENIED',
    PROXY_REQUIRED: 'PROXY_REQUIRED',
    NETWORK_ERROR: 'NETWORK_ERROR',
    SERVER_ERROR: 'SERVER_ERROR',
    UNKNOWN_ERROR: 'UNKNOWN_ERROR'
};

/**
 * Определяет тип ошибки из сообщения
 * @param {string} errorMessage - Сообщение об ошибке
 * @returns {string} - Тип ошибки из ERROR_TYPES
 */
export const determineErrorType = (errorMessage) => {
    if (!errorMessage) return ERROR_TYPES.UNKNOWN_ERROR;

    const errorStr = String(errorMessage).toLowerCase();

    // Проверка на ошибки авторизации
    if (errorStr.includes('введите логин и пароль') ||
        errorStr.includes('login required') ||
        errorStr.includes('password required')) {
        return ERROR_TYPES.LOGIN_REQUIRED;
    }

    // Проверка на ошибки доступа
    if (errorStr.includes('доступ запрещен') ||
        errorStr.includes('пользователь не существует') ||
        errorStr.includes('access denied') ||
        errorStr.includes('user not found') ||
        errorStr.includes('unauthorized')) {
        return ERROR_TYPES.ACCESS_DENIED;
    }


    // Проверка на ошибки прокси
    if (errorStr.includes('прокси не хватает') ||
        errorStr.includes('нужен прокси') ||
        errorStr.includes('proxy required')) {
        return ERROR_TYPES.PROXY_REQUIRED;
    }

    // Проверка на ошибки сети
    if (errorStr.includes('network error') ||
        errorStr.includes('ошибка сети') ||
        errorStr.includes('timeout') ||
        errorStr.includes('таймаут')) {
        return ERROR_TYPES.NETWORK_ERROR;
    }

    // Проверка на ошибки сервера
    if (errorStr.includes('server error') ||
        errorStr.includes('500') ||
        errorStr.includes('ошибка сервера')) {
        return ERROR_TYPES.SERVER_ERROR;
    }

    // Если не удалось определить тип ошибки
    return ERROR_TYPES.UNKNOWN_ERROR;
};

/**
 * Сервис для работы с API приложения
 */
const apiService = {
    /**
     * Проверка авторизации пользователя
     * @param {string} initData - Данные инициализации Telegram
     * @returns {Promise} - Промис с данными пользователя
     */
    checkUserAuth: async (initData) => {
        if (isDemoMode()) {
            await demoDelay();
            return {
                FIO: DEMO_USER.fio,
                group: DEMO_USER.group,
                allowConfirm: DEMO_USER.allowConfirm,
                admin_lvl: DEMO_USER.admin_lvl,
            };
        }
        const url = getFullApiUrl(API_ENDPOINTS.CHECKER, initData);

        const response = await fetch(url);

        // Получаем тело ответа
        const responseText = await response.text();

        let data;
        try {
            // Пытаемся распарсить как JSON
            data = JSON.parse(responseText);
        } catch (e) {
            // Проверяем текст ответа на строковые сообщения
            // Если не JSON, то используем как текст
            throw new Error(responseText || "Неизвестная ошибка сервера");
        }


        // Проверяем на наличие сообщений об ошибках даже в успешном ответе
        if (data.detail === "Введите Логин и Пароль" ||
            data.message === "Введите Логин и Пароль" ||
            data.msg === "Введите Логин и Пароль" ||
            data.error === "Введите Логин и Пароль" ||
            responseText.includes("Введите Логин и Пароль")) {

            throw new Error("Введите Логин и Пароль");
        }

        if (data.detail === "Доступ запрещен" ||
            data.message === "Доступ запрещен" ||
            data.msg === "Доступ запрещен" ||
            data.error === "Доступ запрещен" ||
            responseText.includes("Доступ запрещен")) {

            throw new Error("Доступ запрещен");
        }

        if (data.detail === "Пользователь не существует" ||
            data.message === "Пользователь не существует" ||
            data.msg === "Пользователь не существует" ||
            data.error === "Пользователь не существует" ||
            responseText.includes("Пользователь не существует")) {

            throw new Error("Пользователь не существует");
        }

        // Проверяем на требование 2FA
        if (data.needs_2fa) {
            throw new Error("Требуется ввод кода 2FA");
        }

        // Проверяем на наличие обязательных полей
        if (!data.group || !data.FIO) {
            throw new Error("Неверный формат данных пользователя");
        }

        return data;
    },

    /**
     * Изменение разрешения на автоматическую отметку
     * @param {string} initData - Данные инициализации Telegram
     * @param {boolean} allowConfirm - Разрешить отмечать
     * @returns {Promise} - Промис с результатом операции
     */
    updateAllowConfirm: async (initData, allowConfirm) => {
        return apiPatch(API_ENDPOINTS.EDIT_ALLOW_CONFIRM, { initData, allowConfirm });
    },

    /**
     * Удаление пользователя
     * @param {string} initData - Данные инициализации Telegram
     * @returns {Promise} - Промис с результатом операции
     */
    deleteUser: async (initData) => {
        return apiDelete(API_ENDPOINTS.DELETE_USER, { initData });
    },

    /**
     * Обновление данных пользователя
     * @param {string} initData - Данные инициализации Telegram
     * @param {Object} userData - Данные для обновления
     * @returns {Promise} - Промис с результатом операции
     */
    updateUser: async (initData, userData) => {
        const url = getFullApiUrl(API_ENDPOINTS.UPDATE_USER, initData);

        // Получаем модифицированный User-Agent
        const userAgent = getModifiedUserAgent();

        const response = await fetch(url, {
            method: 'PATCH',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                initData,
                ...userData,
                user_agent: userAgent
            })
        });

        // Получаем текст ответа
        const responseText = await response.text();

        try {
            // Пытаемся распарсить как JSON
            const data = JSON.parse(responseText);

            // Проверяем наличие ошибок даже при успешном статусе
            if (data.detail || data.error || data.message || data.msg) {
                const errorMsg = data.detail || data.error || data.message || data.msg;
                throw new Error(errorMsg);
            }

            return data;
            // eslint-disable-next-line no-unused-vars
        } catch (e) {
            if (response.ok) {
                // Если статус успешный, возвращаем успешный результат
                return { success: true };
            }

            // Иначе выбрасываем ошибку
            throw new Error(responseText || "Неизвестная ошибка при обновлении пользователя");
        }
    },

    /**
     * Получение списка пользователей группы
     * @param {string} initData - Данные инициализации Telegram
     * @returns {Promise} - Промис со списком пользователей
     */
    getGroupUsers: async (initData) => {
        if (isDemoMode()) {
            await demoDelay();
            return DEMO_GROUP_USERS;
        }
        return apiGet(API_ENDPOINTS.GET_GROUP_USERS, initData);
    },

    /**
     * Получение списка пользователей другой группы
     * @param {string} initData - Данные инициализации Telegram
     * @param {string} groupName - Название группы
     * @returns {Promise} - Промис со списком пользователей
     */
    getOtherGroupUsers: async (initData, groupName) => {
        const endpoint = `${API_ENDPOINTS.GET_OTHER_GROUP_USERS}?group_name=${encodeURIComponent(groupName)}`;
        return apiGet(endpoint, initData);
    },

    /**
     * Получение списка доступных групп
     * @param {string} initData - Данные инициализации Telegram
     * @returns {Promise} - Промис со списком групп
     */
    getAvailableGroups: async (initData) => {
        if (isDemoMode()) {
            await demoDelay();
            return DEMO_AVAILABLE_GROUPS;
        }
        return apiGet(API_ENDPOINTS.GET_AVAILABLE_GROUPS, initData);
    },

    /**
     * Отправка подтверждения посещаемости
     * @param {string} initData - Данные инициализации Telegram
     * @param {string} url - URL из QR-кода
     * @returns {Promise} - Промис с результатом отметки
     */
    sendApprove: async (initData, url) => {
        return apiPost(API_ENDPOINTS.SEND_APPROVE, { initData, url });
    },

    /**
     * Начало массовой отметки посещаемости
     * @param {string} initData - Данные инициализации Telegram
     * @param {Array} selectedUsers - Список ID пользователей для отметки
     * @param {string} url - URL из QR-кода
     * @returns {Promise} - Промис с ID сессии отметки
     */
    startMassMarking: async (initData, selectedUsers, url) => {
        if (isDemoMode()) {
            await demoDelay();
            return { session_id: DEMO_MARKING_SESSION.session_id };
        }
        return apiPost(API_ENDPOINTS.START_MASS_MARKING, {
            initData,
            selectedUsers,
            url
        });
    },

    /**
     * Получение статуса массовой отметки
     * @param {string} sessionId - ID сессии отметки
     * @returns {Promise} - Промис со статусом отметки
     */
    getMarkingStatus: async (sessionId) => {
        if (isDemoMode()) {
            await demoDelay();
            return DEMO_MARKING_SESSION;
        }
        return apiGet(`${API_ENDPOINTS.GET_MARKING_STATUS}/${sessionId}`);
    },

    /**
     * Продолжение отметки с новым QR-кодом
     * @param {string} initData - Данные инициализации Telegram
     * @param {string} sessionId - ID сессии отметки
     * @param {string} url - Новый URL из QR-кода
     * @returns {Promise} - Промис с результатом продолжения отметки
     */
    continueMarking: async (initData, sessionId, url) => {
        return apiPost(API_ENDPOINTS.CONTINUE_MARKING, {
            initData,
            session_id: sessionId,
            url
        });
    },

    /**
     * Получение URL для статуса отметки
     * @param {string} sessionId - ID сессии отметки
     * @returns {string} - URL для получения статуса
     */
    getMarkingStatusUrl: (sessionId) => {
        return getFullApiUrl(`${API_ENDPOINTS.GET_MARKING_STATUS}/${sessionId}`);
    },

    /**
     * Получение расписания на указанную дату
     * @param {string} initData - Данные инициализации Telegram
     * @param {number} year - Год
     * @param {number} month - Месяц (1-12)
     * @param {number} day - День
     * @returns {Promise} - Промис со списком занятий
     */
    getSchedule: async (initData, year, month, day) => {
        if (isDemoMode()) {
            await demoDelay();
            return DEMO_SCHEDULE;
        }
        return apiPost(API_ENDPOINTS.GET_SCHEDULE, {
            initData,
            year,
            month,
            day
        });
    },

    /**
     * Получение статистики посещаемости по занятию
     * @param {string} initData - Данные инициализации Telegram
     * @param {string} lessonDate - Дата занятия (YYYY-MM-DD)
     * @param {string} lessonTime - Время занятия (HH:MM)
     * @param {string} lessonType - Тип занятия (ЛК, ПР, ЛАБ)
     * @param {string} lessonSubject - Название предмета
     * @param {number} lessonIndexInDay - Индекс пары в дне (0, 1, 2...)
     * @returns {Promise} - Промис со списком студентов и их статусами
     */
    getLessonAttendance: async (initData, lessonDate, lessonTime, lessonType, lessonSubject, lessonIndexInDay = 0) => {
        if (isDemoMode()) {
            await demoDelay();
            return DEMO_LESSON_ATTENDANCE;
        }
        return apiPost(API_ENDPOINTS.GET_LESSON_ATTENDANCE, {
            initData,
            lesson_date: lessonDate,
            lesson_time: lessonTime,
            lesson_type: lessonType,
            lesson_subject: lessonSubject,
            lesson_index_in_day: lessonIndexInDay
        });
    },

    /**
     * Получение расписания на месяц для кэширования (через публичное API)
     * @param {string} initData - Данные инициализации Telegram
     * @param {number} year - Год
     * @param {number} month - Месяц (1-12)
     * @returns {Promise} - Промис со словарем {дата: [список занятий]}
     */
    getMonthScheduleCache: async (initData, year, month) => {
        try {
            const result = await apiPost(API_ENDPOINTS.GET_MONTH_SCHEDULE_CACHE, {
                initData,
                year,
                month
            });
            return result;
        } catch (error) {
            // Не выбрасываем ошибку, возвращаем пустой объект
            return { schedule: {} };
        }
    },

    /**
     * Получение календаря занятий (количество пар по дням) для указанного периода
     * @param {string} initData - Данные инициализации Telegram
     * @param {number|null} startTs - Unix timestamp начала периода (опционально)
     * @param {number|null} endTs - Unix timestamp конца периода (опционально)
     * @returns {Promise} - Промис с календарем {"2025": {"11": {1: 4, 2: 3, ...}}}
     */
    getLessonsCalendar: async (initData, startTs = null, endTs = null) => {
        if (isDemoMode()) {
            await demoDelay();
            return DEMO_LESSONS_CALENDAR;
        }
        try {
            // Формируем URL с параметрами дат
            let endpoint = API_ENDPOINTS.GET_LESSONS_CALENDAR;
            const params = [];
            if (startTs !== null) {
                params.push(`start_ts=${startTs}`);
            }
            if (endTs !== null) {
                params.push(`end_ts=${endTs}`);
            }
            if (params.length > 0) {
                endpoint += (endpoint.includes('?') ? '&' : '?') + params.join('&');
            }
            const result = await apiGet(endpoint, initData);
            return result;
        } catch (error) {
            // Не выбрасываем ошибку, возвращаем пустой объект
            return { calendar: {} };
        }
    },

    /**
     * Получение статуса нахождения пользователя в университете
     * @param {string} initData - Данные инициализации Telegram
     * @returns {Promise} - Промис со статусом нахождения
     */
    getUniversityStatus: async (initData) => {
        try {
            const result = await apiGet(API_ENDPOINTS.GET_UNIVERSITY_STATUS, initData);
            return result;
        } catch (error) {
            // Не выбрасываем ошибку, возвращаем значение по умолчанию
            return {
                is_inside_university: false,
                error: error.message
            };
        }
    },

    /**
     * Получение стоимости посещения пар для всех предметов группы
     * @param {string} initData - Данные инициализации Telegram
     * @returns {Promise} - Промис с объектом {lessons_cost: {предмет: количество_пар}, cached: bool}
     */
    getLessonsCost: async (initData) => {
        if (isDemoMode()) {
            await demoDelay();
            return DEMO_LESSONS_COST;
        }
        try {
            const result = await apiGet(API_ENDPOINTS.GET_LESSONS_COST, initData);
            return result;
        } catch (error) {
            // Возвращаем пустой объект при ошибке
            return {
                lessons_cost: {},
                cached: false
            };
        }
    },

    /**
     * Получение статусов присутствия всех активированных студентов группы в университете
     * @param {string} initData - Данные инициализации Telegram
     * @returns {Promise} - Промис со списком студентов и их статусами
     */
    getGroupUniversityStatus: async (initData) => {
        if (isDemoMode()) {
            await demoDelay();
            return DEMO_GROUP_UNIVERSITY_STATUS;
        }
        try {
            const result = await apiGet(API_ENDPOINTS.GET_GROUP_UNIVERSITY_STATUS, initData);
            return result;
        } catch (error) {
            // Возвращаем пустой список при ошибке
            return {
                students: [],
                error: error.message
            };
        }
    }
};

export default apiService;