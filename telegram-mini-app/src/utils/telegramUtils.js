/**
 * Утилиты для работы с Telegram WebApp
 */

/**
 * Проверяет доступность Telegram WebApp
 * @returns {boolean} Доступен ли Telegram WebApp
 */
export const isTelegramWebAppAvailable = () => {
    return Boolean(window.Telegram?.WebApp);
};

/**
 * Получает данные инициализации из Telegram WebApp
 * @returns {string} Строка initData или тестовые данные для разработки
 */
export const getInitData = () => {
    if (!isTelegramWebAppAvailable()) {
        console.warn('Telegram WebApp is not available, using test data');
        // Возвращаем тестовые данные для разработки
        return 'test_init_data_for_development';
    }
    console.log('Получены initData из Telegram WebApp');
    return window.Telegram.WebApp.initData;
};

/**
 * Получает параметры темы из Telegram WebApp
 * @returns {Object} Объект с параметрами темы или дефолтные значения
 */
export const getThemeParams = () => {
    if (!isTelegramWebAppAvailable()) {
        console.warn('Telegram WebApp is not available');
        return getDefaultThemeParams();
    }
    return window.Telegram.WebApp.themeParams || getDefaultThemeParams();
};

/**
 * Получает дефолтные параметры темы
 * @returns {Object} Объект с дефолтными параметрами темы
 */
export const getDefaultThemeParams = () => {
    return {
        bg_color: '#ffffff',
        text_color: '#000000',
        hint_color: '#999999',
        button_color: '#2481cc',
        button_text_color: '#ffffff',
        secondary_bg_color: '#f0f0f0',
        header_bg_color: '#ffffff',
        accent_text_color: '#000000',
        section_bg_color: '#f0f0f0',
        section_header_text_color: '#000000',
        subtitle_text_color: '#999999',
        destructive_text_color: '#ff3b30'
    };
};

/**
 * Формирует правдоподобный User-Agent для запросов API
 * заменяя информацию о браузере в зависимости от ОС:
 * - Для iOS использует Safari
 * - Для Android использует Chrome Mobile
 * @returns {string} Сформированный User-Agent
 */
export const getModifiedUserAgent = () => {
    const originalUserAgent = navigator.userAgent;

    // Определяем ОС
    const isIOS = /iPhone|iPad|iPod/i.test(originalUserAgent);
    const isAndroid = /Android/i.test(originalUserAgent);

    if (isIOS) {
        // Для iOS устанавливаем Safari
        // Извлекаем версию iOS
        const iosVersionMatch = originalUserAgent.match(/OS (\d+[._]\d+)/i);
        const iosVersion = iosVersionMatch ? iosVersionMatch[1].replace('.', '_') : "15_5"; // Дефолтная версия

        // Определяем тип устройства
        let deviceType = "iPhone";
        if (originalUserAgent.includes("iPad")) {
            deviceType = "iPad";
        } else if (originalUserAgent.includes("iPod")) {
            deviceType = "iPod";
        }

        return `Mozilla/5.0 (${deviceType}; CPU ${deviceType === "iPhone" ? "iPhone " : ""}OS ${iosVersion} like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/${iosVersion.replace("_", ".")} Mobile/15E148 Safari/604.1`;
    }
    else if (isAndroid) {
        // Для Android устанавливаем Chrome Mobile
        // Извлекаем версию Android
        const androidVersionMatch = originalUserAgent.match(/Android (\d+([._]\d+)*)/i);
        const androidVersion = androidVersionMatch ? androidVersionMatch[1] : "12"; // Дефолтная версия

        // Извлекаем модель устройства
        const deviceModelMatch = originalUserAgent.match(/Android [^;]+; ([^)]+)/i);
        const deviceModel = deviceModelMatch ? deviceModelMatch[1].trim() : "SM-G991B"; // Дефолтная модель

        // Генерируем случайную версию Chrome от 90 до 110
        const chromeVersion = Math.floor(Math.random() * 20) + 90;
        const chromeSubVersion = Math.floor(Math.random() * 5000);

        return `Mozilla/5.0 (Linux; Android ${androidVersion}; ${deviceModel}) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/${chromeVersion}.0.${chromeSubVersion}.${Math.floor(Math.random() * 100)} Mobile Safari/537.36`;
    }

    // Если не удалось определить ОС, возвращаем оригинальный User-Agent
    // Но удаляем информацию о конкретном браузере, оставляя только базовую информацию
    if (originalUserAgent.includes("Mozilla/5.0")) {
        const basePart = originalUserAgent.split(') ')[0] + ')';
        return `${basePart} AppleWebKit/537.36 (KHTML, like Gecko) Chrome/101.0.4951.61 Mobile Safari/537.36`;
    }

    return originalUserAgent;
};

/**
 * Применяет тему Telegram к корневому элементу
 * @param {Object} themeParams - Параметры темы
 */
export const applyTelegramTheme = (themeParams = null) => {
    const params = themeParams || getThemeParams();
    const root = document.documentElement;

    // Apply all colors from Telegram theme
    root.style.setProperty('--bg-color', params.bg_color || '#ffffff');
    root.style.setProperty('--text-color', params.text_color || '#000000');
    root.style.setProperty('--hint-color', params.hint_color || '#999999');
    root.style.setProperty('--button-color', params.button_color || '#2481cc');
    root.style.setProperty('--button-text-color', params.button_text_color || '#ffffff');
    root.style.setProperty('--secondary-bg-color', params.secondary_bg_color || '#f0f0f0');
    root.style.setProperty('--header-bg-color', params.header_bg_color || params.bg_color || '#ffffff');
    root.style.setProperty('--accent-text-color', params.accent_text_color || params.text_color || '#000000');
    root.style.setProperty('--section-bg-color', params.section_bg_color || params.secondary_bg_color || '#f0f0f0');
    root.style.setProperty('--section-header-text-color', params.section_header_text_color || params.text_color || '#000000');
    root.style.setProperty('--subtitle-text-color', params.subtitle_text_color || params.hint_color || '#999999');
    root.style.setProperty('--destructive-text-color', params.destructive_text_color || '#ff3b30');

    // Additional shades for gradients
    root.style.setProperty('--bg-color-lighter', colorMix(params.bg_color || '#ffffff', '#ffffff', 0.2));
    root.style.setProperty('--bg-color-darker', colorMix(params.bg_color || '#ffffff', '#000000', 0.1));

    // Adapt background color to entire document
    document.body.style.backgroundColor = params.bg_color || '#ffffff';
    document.body.style.color = params.text_color || '#000000';
};

/**
 * Смешивает два цвета с указанным соотношением
 * @param {string} color1 - Первый цвет
 * @param {string} color2 - Второй цвет
 * @param {number} ratio - Соотношение от 0 до 1
 * @returns {string} Смешанный цвет в формате CSS
 */
export const colorMix = (color1, color2, ratio) => {
    // Simple color mixing using CSS functions
    return `color-mix(in srgb, ${color1}, ${color2} ${ratio * 100}%)`;
};

/**
 * Запускает сканирование QR-кода
 * @param {string} text - Текст подсказки в окне сканирования
 * @param {Function} callback - Функция обработки результата сканирования
 * @returns {boolean} Успешно ли запущено сканирование
 */
export const scanQR = (text, callback) => {
    if (!isTelegramWebAppAvailable()) {
        console.error("Telegram WebApp is not available for QR scanning");
        return false;
    }

    window.Telegram.WebApp.showScanQrPopup(
        { text },
        (result) => {
            window.Telegram.WebApp.closeScanQrPopup();
            if (callback) callback(result);
            return true;
        }
    );

    return true;
};

/**
 * Показывает диалог подтверждения
 * @param {string} text - Текст подтверждения
 * @param {Function} callback - Функция обработки результата
 */
export const showConfirm = (text, callback) => {
    if (!isTelegramWebAppAvailable()) {
        console.warn('Telegram WebApp is not available, using browser confirm');
        const confirmed = window.confirm(text);
        if (callback) callback(confirmed);
        return;
    }

    window.Telegram.WebApp.showConfirm(text, callback);
};

/**
 * Сообщает Telegram WebApp о готовности
 */
export const ready = () => {
    if (isTelegramWebAppAvailable()) {
        window.Telegram.WebApp.ready();
    }
};

/**
 * Добавляет слушатель событий Telegram WebApp
 * @param {string} eventName - Название события
 * @param {Function} callback - Функция-обработчик
 */
export const addEventHandler = (eventName, callback) => {
    if (isTelegramWebAppAvailable()) {
        window.Telegram.WebApp.onEvent(eventName, callback);
    }
};

/**
 * Удаляет слушатель событий Telegram WebApp
 * @param {string} eventName - Название события
 * @param {Function} callback - Функция-обработчик
 */
export const removeEventHandler = (eventName, callback) => {
    if (isTelegramWebAppAvailable()) {
        window.Telegram.WebApp.offEvent(eventName, callback);
    }
};

/**
 * Подготавливает приложение для работы с Telegram WebApp
 */
export const initTelegramWebApp = () => {
    if (isTelegramWebAppAvailable()) {
        const tg = window.Telegram.WebApp;

        // Сообщаем о готовности
        ready();

        // Расширяем на весь экран
        tg.expand();

        // Включаем закрытие через свайп
        tg.enableClosingConfirmation();

        // Применяем safe area insets
        if (tg.safeAreaInset) {
            const root = document.documentElement;
            root.style.setProperty('--tg-safe-area-inset-top', `${tg.safeAreaInset.top}px`);
            root.style.setProperty('--tg-safe-area-inset-bottom', `${tg.safeAreaInset.bottom}px`);
            root.style.setProperty('--tg-safe-area-inset-left', `${tg.safeAreaInset.left}px`);
            root.style.setProperty('--tg-safe-area-inset-right', `${tg.safeAreaInset.right}px`);
        }

        // Применяем тему
        document.documentElement.classList.add('telegram-theme');
        applyTelegramTheme();

        // Слушаем изменения темы
        addEventHandler('themeChanged', () => {
            applyTelegramTheme();
        });

        // Слушаем изменения viewport
        addEventHandler('viewportChanged', () => {
            if (tg.isExpanded) {
                console.log('Viewport expanded');
            }
        });

        return true;
    }

    console.warn('Telegram WebApp is not available, running in standalone mode');
    // Применяем дефолтную тему для режима без Telegram
    document.documentElement.classList.add('telegram-theme');
    applyTelegramTheme(getDefaultThemeParams());

    return false;
};