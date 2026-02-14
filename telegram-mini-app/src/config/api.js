/**
 * Конфигурация API для приложения
 */

// Базовый URL для API (используется только для справки, запросы идут через относительные пути)
export const API_BASE_URL = import.meta.env.VITE_API_URL || '';

// Функция для формирования URL эндпоинта API
export const getApiUrl = (endpoint) => {
    // Удаляем начальный слеш, если он есть
    const cleanEndpoint = endpoint.startsWith('/') ? endpoint.substring(1) : endpoint;

    // Используем локальный прокси для обхода CORS
    return `/api/${cleanEndpoint}`;
};

// Функция для добавления параметров initData к URL
export const appendInitData = (url, initData) => {
    const separator = url.includes('?') ? '&' : '?';
    return `${url}${separator}initData=${encodeURIComponent(initData)}`;
};

// Функция для создания полного URL API с учетом initData
export const getFullApiUrl = (endpoint, initData) => {
    const apiUrl = getApiUrl(endpoint);
    return initData ? appendInitData(apiUrl, initData) : apiUrl;
};

// Объект с путями API
export const API_ENDPOINTS = {
    // Основные эндпоинты
    CHECKER: 'checker',
    EDIT_ALLOW_CONFIRM: 'edit_allow_confirm',
    DELETE_USER: 'delete',
    UPDATE_USER: 'update_user',

    // Эндпоинты для работы с группами
    GET_GROUP_USERS: 'get_group_users',
    GET_OTHER_GROUP_USERS: 'get_other_group_users',
    GET_AVAILABLE_GROUPS: 'get_available_groups',

    // Эндпоинты для отметки посещаемости
    SEND_APPROVE: 'send_approve',
    START_MASS_MARKING: 'start_mass_marking',
    GET_MARKING_STATUS: 'get_marking_status',
    CONTINUE_MARKING: 'continue_marking',

    // Другие эндпоинты
    CREATE_USER: 'create_user',
    ADD_PROXY: 'add_proxy',
    GET_COUNT_USERS: 'get_count_users',
    GET_POINTS: 'get_points',

    // Расписание
    GET_SCHEDULE: 'schedule/',
    GET_LESSON_ATTENDANCE: 'schedule/attendance',
    GET_MONTH_SCHEDULE_CACHE: 'schedule/month-cache',
    GET_LESSONS_CALENDAR: 'schedule/lessons-calendar',
    GET_LESSONS_COST: 'schedule/lessons-cost',

    // Статус нахождения в университете
    GET_UNIVERSITY_STATUS: 'university_status',
    GET_GROUP_UNIVERSITY_STATUS: 'group_university_status'
};

// Вспомогательные функции для API-запросов

/**
 * Создает базовый заголовок Content-Type для JSON-запросов
 * @returns {Object} Объект с заголовками
 */
export const getJsonHeaders = () => {
    return { 'Content-Type': 'application/json' };
};

/**
 * Проверяет успешность HTTP-ответа
 * @param {Response} response - Объект ответа fetch
 * @returns {Promise} - Промис с данными или ошибкой
 */
export const checkApiResponse = async (response) => {
    if (!response.ok) {
        // Пытаемся получить тело ответа как JSON
        let errorData;
        try {
            errorData = await response.json();
        } catch (e) {
            // Если не удается распарсить JSON, используем текст ответа
            const textResponse = await response.text().catch(() => "");
            errorData = { detail: textResponse || `Ошибка сервера: ${response.status}` };
        }


        // Извлекаем сообщение об ошибке из разных возможных форматов
        let errorMessage;
        if (typeof errorData === 'string') {
            errorMessage = errorData;
        } else if (errorData.detail) {
            errorMessage = errorData.detail;
        } else if (errorData.message) {
            errorMessage = errorData.message;
        } else if (errorData.error) {
            errorMessage = errorData.error;
        } else if (errorData.msg) {
            errorMessage = errorData.msg;
        } else {
            errorMessage = `Ошибка API: ${response.status}`;
        }

        throw new Error(errorMessage);
    }
    return response.json();
};

/**
 * Базовая функция для выполнения GET-запроса к API
 * @param {string} endpoint - Путь эндпоинта
 * @param {string} initData - Данные инициализации Telegram
 * @returns {Promise} - Промис с результатом запроса
 */
export const apiGet = async (endpoint, initData) => {
    const url = getFullApiUrl(endpoint, initData);
    const response = await fetch(url);
    return checkApiResponse(response);
};

/**
 * Базовая функция для выполнения POST-запроса к API
 * @param {string} endpoint - Путь эндпоинта
 * @param {Object} data - Данные для отправки
 * @returns {Promise} - Промис с результатом запроса
 */
export const apiPost = async (endpoint, data) => {
    const url = data.initData ? getFullApiUrl(endpoint, data.initData) : getApiUrl(endpoint);
    const response = await fetch(url, {
        method: 'POST',
        headers: getJsonHeaders(),
        body: JSON.stringify(data)
    });
    return checkApiResponse(response);
};

/**
 * Базовая функция для выполнения PATCH-запроса к API
 * @param {string} endpoint - Путь эндпоинта
 * @param {Object} data - Данные для отправки
 * @returns {Promise} - Промис с результатом запроса
 */
export const apiPatch = async (endpoint, data) => {
    const url = data.initData ? getFullApiUrl(endpoint, data.initData) : getApiUrl(endpoint);
    const response = await fetch(url, {
        method: 'PATCH',
        headers: getJsonHeaders(),
        body: JSON.stringify(data)
    });
    return checkApiResponse(response);
};

/**
 * Базовая функция для выполнения DELETE-запроса к API
 * @param {string} endpoint - Путь эндпоинта
 * @param {Object} data - Данные для отправки
 * @returns {Promise} - Промис с результатом запроса
 */
export const apiDelete = async (endpoint, data) => {
    const url = data.initData ? getFullApiUrl(endpoint, data.initData) : getApiUrl(endpoint);
    const response = await fetch(url, {
        method: 'DELETE',
        headers: getJsonHeaders(),
        body: JSON.stringify(data)
    });
    return checkApiResponse(response);
};