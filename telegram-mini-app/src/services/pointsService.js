import { API_ENDPOINTS, apiGet } from '../config/api';
import { determineErrorType, ERROR_TYPES } from './apiService';
import { isDemoMode, demoDelay, DEMO_POINTS } from '../demo/mockData';

/**
 * Сервис для работы с баллами БРС
 */
const pointsService = {
    /**
     * Получение баллов пользователя
     * @param {string} initData - Данные инициализации Telegram
     * @returns {Promise} - Промис с данными о баллах
     */
    getPoints: async (initData) => {
        if (isDemoMode()) {
            await demoDelay();
            return DEMO_POINTS.points;
        }
        try {
            const response = await fetch(`/api/${API_ENDPOINTS.GET_POINTS}?initData=${encodeURIComponent(initData)}`);

            // Получаем тело ответа
            const responseText = await response.text();

            // Проверяем на типичные ошибки подписки в тексте ответа
            if (responseText.includes("Прокси не хватает. Оформи подписку")) {
                throw new Error("SUBSCRIPTION_ERROR: Прокси не хватает. Оформите подписку для просмотра баллов");
            }

            if (responseText.includes("Оформи/Продли Подписку") ||
                responseText.includes("Оформи подписку") ||
                responseText.includes("Продли подписку")) {
                throw new Error("SUBSCRIPTION_ERROR: Требуется оформить или продлить подписку");
            }

            // Пытаемся распарсить ответ как JSON
            try {
                const data = JSON.parse(responseText);
                return data;
            } catch (e) {
                // Если не удалось распарсить как JSON, но ответ успешный
                if (response.ok) {
                    return []; // Возвращаем пустой массив, чтобы избежать ошибки
                }

                // Определяем тип ошибки
                const errorType = determineErrorType(responseText);
                if (errorType === ERROR_TYPES.SUBSCRIPTION_REQUIRED) {
                    throw new Error(`SUBSCRIPTION_ERROR: ${responseText}`);
                }

                // Если не удалось распарсить ответ и он не успешный, выбрасываем ошибку
                throw new Error(responseText || "Ошибка получения баллов");
            }
        } catch (error) {
            // Проверяем, является ли ошибка связанной с подпиской
            const errorType = determineErrorType(error.message);
            if (errorType === ERROR_TYPES.SUBSCRIPTION_REQUIRED && !error.message.includes("SUBSCRIPTION_ERROR")) {
                throw new Error(`SUBSCRIPTION_ERROR: ${error.message}`);
            }

            // Проверяем на другие специфические проблемы с API
            if (error.message.includes("Что то пошло не так ;(")) {
                throw new Error("Произошла ошибка на сервере. Пожалуйста, попробуйте позже.");
            }

            throw error;
        }
    }
};

export default pointsService;