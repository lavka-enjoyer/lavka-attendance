import React, { useState, useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { X, HelpCircle, Smartphone, Laptop, Tablet, Check, Globe, ChevronDown } from 'lucide-react';

// Кастомный компонент выбора из списка
const CustomSelect = ({ value, onChange, options, placeholder }) => {
    const [isOpen, setIsOpen] = useState(false);
    const [selectedValue, setSelectedValue] = useState(value);

    useEffect(() => {
        setSelectedValue(value);
    }, [value]);

    const handleSelect = (option) => {
        setSelectedValue(option.value);
        onChange(option.value);
        setIsOpen(false);
    };

    const getDisplayText = () => {
        const selected = options.find(opt => opt.value === selectedValue);
        return selected ? selected.label : placeholder || 'Выберите...';
    };

    return (
        <div className="relative">
            <button
                type="button"
                className="w-full p-3 rounded-lg border flex justify-between items-center"
                style={{
                    backgroundColor: 'var(--bg-color)',
                    color: 'var(--text-color)',
                    borderColor: 'var(--hint-color)'
                }}
                onClick={() => setIsOpen(!isOpen)}
            >
                <span className="truncate">{getDisplayText()}</span>
                <ChevronDown size={16} className={`transition-transform ${isOpen ? 'rotate-180' : ''}`} />
            </button>

            {isOpen && (
                <div
                    className="absolute z-10 mt-1 w-full rounded-lg shadow-lg max-h-60 overflow-auto"
                    style={{
                        backgroundColor: 'var(--bg-color)',
                        border: '1px solid var(--hint-color)'
                    }}
                >
                    {options.map((option) => (
                        <div
                            key={option.value}
                            className="p-3 cursor-pointer hover:opacity-80 transition-opacity"
                            style={{
                                backgroundColor: selectedValue === option.value ? 'rgba(36, 129, 204, 0.1)' : 'transparent',
                                color: 'var(--text-color)',
                                borderBottom: '1px solid rgba(0,0,0,0.05)'
                            }}
                            onClick={() => handleSelect(option)}
                        >
                            {option.label}
                        </div>
                    ))}
                </div>
            )}
        </div>
    );
};

// Компонент-конструктор User-Agent
const UserAgentConstructor = ({ onClose, onSave, initialUserAgent }) => {
    // Определение текущего устройства
    const detectCurrentDevice = () => {
        const ua = navigator.userAgent;
        if (/iPhone/i.test(ua)) return 'iPhone';
        if (/iPad/i.test(ua)) return 'iPad';
        if (/Android/i.test(ua)) {
            if (/Mobile/i.test(ua)) return 'Android-смартфон';
            return 'Android-планшет';
        }
        return 'Android-смартфон'; // По умолчанию
    };

    // Определение текущей модели
    const detectCurrentModel = () => {
        const ua = navigator.userAgent;

        // Для Android попробуем извлечь модель
        if (/Android/i.test(ua)) {
            const modelMatch = ua.match(/Android [^;]+; ([^)]+)/i);
            return modelMatch ? modelMatch[1].trim() : "SM-G991B";
        }

        return "iPhone 13"; // Для iOS модель по умолчанию
    };

    // Определение текущей версии ОС
    const detectCurrentOSVersion = () => {
        const ua = navigator.userAgent;

        // Для iOS
        if (/iPhone|iPad/i.test(ua)) {
            const versionMatch = ua.match(/OS (\d+[._]\d+)/i);
            if (versionMatch) {
                return versionMatch[1].replace('_', '.');
            }
            return "15.5";
        }

        // Для Android
        if (/Android/i.test(ua)) {
            const versionMatch = ua.match(/Android (\d+([._]\d+)*)/i);
            return versionMatch ? versionMatch[1] : "12";
        }

        return "12"; // По умолчанию для Android
    };

    // Определяем текущий браузер
    const detectCurrentBrowser = () => {
        const ua = navigator.userAgent;
        if (/Chrome/i.test(ua) && !/Chromium|Edge/i.test(ua)) return 'Chrome';
        if (/Firefox/i.test(ua)) return 'Firefox';
        if (/Safari/i.test(ua) && !/Chrome|Chromium/i.test(ua)) return 'Safari';
        if (/Edge/i.test(ua)) return 'Edge';
        if (/Opera|OPR/i.test(ua)) return 'Opera';
        return 'Chrome'; // По умолчанию
    };

    const [deviceType, setDeviceType] = useState(detectCurrentDevice());
    const [model, setModel] = useState(''); // Начинаем с пустой модели, чтобы пользователь выбрал
    const [osVersion, setOsVersion] = useState(detectCurrentOSVersion());
    const [browser, setBrowser] = useState(detectCurrentBrowser());
    const [customModel, setCustomModel] = useState('');
    const [customOSVersion, setCustomOSVersion] = useState('');
    const [showInfo, setShowInfo] = useState(false);
    const [generatedUserAgent, setGeneratedUserAgent] = useState('');
    const [showPreview, setShowPreview] = useState(true); // Всегда показываем предпросмотр
    const [autoMode, setAutoMode] = useState(true);

    // Обновленный список популярных Android-устройств
    const popularAndroidModels = [
        "Samsung Galaxy S25 Ultra",
        "Google Pixel 9 Pro",
        "Samsung Galaxy Z Fold 6",
        "OnePlus 13",
        "Google Pixel 9a",
        "Samsung Galaxy S25",
        "Nothing Phone 3a Pro",
        "Samsung Galaxy Z Flip 6",
        "OnePlus Open",
        "Motorola Razr 2025",
        "Xiaomi 15 Ultra",
        "Vivo X200 Pro",
        "Honor Magic V3",
        "Realme GT 6",
        "Asus ROG Phone 9",
        "Samsung Galaxy A25 5G",
        "Samsung Galaxy A16 5G",
        "CMF Phone 1",
        "Google Pixel 9",
        "Samsung Galaxy S24",
        // Старые модели
        "Samsung Galaxy S23 Ultra",
        "Samsung Galaxy S23+",
        "Samsung Galaxy S23",
        "Samsung Galaxy S22 Ultra",
        "Samsung Galaxy S22+",
        "Samsung Galaxy S22",
        "Samsung Galaxy S21",
        "Samsung Galaxy A54",
        "Samsung Galaxy A53",
        "Samsung Galaxy A52",
        "Samsung Galaxy A34",
        "Samsung Galaxy A33",
        "Samsung Galaxy A14",
        "Samsung Galaxy A13",
        "Xiaomi Redmi Note 12 Pro",
        "Xiaomi Redmi Note 12",
        "Xiaomi Redmi Note 11",
        "Xiaomi Redmi Note 10",
        "Xiaomi 13 Pro",
        "Xiaomi 13",
        "Xiaomi 12",
        "Google Pixel 7 Pro",
        "Google Pixel 7",
        "Google Pixel 6",
        "OnePlus 11",
        "OnePlus 10 Pro",
        "OnePlus Nord 3",
        "Huawei P50 Pro",
        "Huawei Nova 10",
        "Oppo Reno 8 Pro",
        "Oppo Find X5 Pro",
        "Vivo X90 Pro",
        "Honor 70",
        "Realme GT Neo 3"
    ];

    // Обновленные модели iPhone
    const iPhoneModels = [
        "iPhone 16 Pro Max",
        "iPhone 16 Pro",
        "iPhone 16",
        "iPhone 16 Plus",
        "iPhone 16e",
        "iPhone 15 Pro Max",
        "iPhone 15 Pro",
        "iPhone 15",
        "iPhone 15 Plus",
        "iPhone 14 Pro Max",
        "iPhone 14 Pro",
        "iPhone 14",
        "iPhone 14 Plus",
        "iPhone 13",
        "iPhone 13 mini",
        "iPhone 12",
        "iPhone 12 mini",
        "iPhone SE (2022)",
        "iPhone 11",
        "iPhone XR",
        // Старые модели
        "iPhone 13 Pro Max",
        "iPhone 13 Pro",
        "iPhone 12 Pro Max",
        "iPhone 12 Pro",
        "iPhone 11 Pro Max",
        "iPhone 11 Pro",
        "iPhone XS Max",
        "iPhone XS",
        "iPhone X",
        "iPhone SE (2020)"
    ];

    // Модели iPad
    const iPadModels = [
        "iPad Pro 12.9-inch (6th generation)",
        "iPad Pro 11-inch (4th generation)",
        "iPad Air (5th generation)",
        "iPad (10th generation)",
        "iPad mini (6th generation)",
        "iPad Pro 12.9-inch (5th generation)",
        "iPad Pro 11-inch (3rd generation)",
        "iPad (9th generation)",
        "iPad Air (4th generation)",
        "iPad (8th generation)",
        "iPad Pro 12.9-inch (4th generation)",
        "iPad Pro 11-inch (2nd generation)"
    ];

    // Популярные модели в зависимости от типа устройства
    const getPopularModels = () => {
        if (deviceType === 'iPhone') return iPhoneModels;
        if (deviceType === 'iPad') return iPadModels;
        return popularAndroidModels;
    };

    // Версии iOS
    const iOSVersions = ["14.4", "14.8", "15.0", "15.5", "15.7", "16.0", "16.3", "16.5", "16.7", "17.0", "17.3", "17.4", "17.5", "18.0", "18.1"];

    // Версии Android
    const androidVersions = ["9", "10", "11", "12", "12.1", "13", "14", "15"];

    // Популярные браузеры
    const browsers = [
        "Chrome",
        "Safari",
        "Firefox",
        "Edge",
        "Opera"
    ];

    // Генерация User-Agent
    const generateUserAgent = () => {
        let userAgent = '';

        // Проверка на валидность данных
        if (!model && !customModel) {
            return ''; // Возвращаем пустую строку, если модель не выбрана
        }

        // Для iOS устройств
        if (deviceType === 'iPhone' || deviceType === 'iPad') {
            // Заменяем точку на подчеркивание для iOS версии
            const formattedVersion = (customOSVersion || osVersion).replace('.', '_');
            const safariVersion = parseFloat(customOSVersion || osVersion).toFixed(1);
            const actualModel = customModel || model || (deviceType === 'iPhone' ? 'iPhone' : 'iPad');

            // Если выбран Safari или браузер не выбран (по умолчанию Safari для iOS)
            if (browser === 'Safari' || !browser) {
                userAgent = `Mozilla/5.0 (${deviceType}; CPU ${deviceType} OS ${formattedVersion} like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/${safariVersion} Mobile/15E148 Safari/604.1`;
            }
            // Chrome на iOS
            else if (browser === 'Chrome') {
                // Chrome на iOS по-прежнему использует движок Safari WebKit, но с другим User-Agent
                const chromeVersion = Math.floor(Math.random() * 20) + 110;
                userAgent = `Mozilla/5.0 (${deviceType}; CPU ${deviceType} OS ${formattedVersion} like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) CriOS/${chromeVersion}.0.${Math.floor(Math.random() * 5000)}.${Math.floor(Math.random() * 100)} Mobile/15E148 Safari/604.1`;
            }
            // Firefox на iOS
            else if (browser === 'Firefox') {
                const ffVersion = Math.floor(Math.random() * 20) + 40;
                userAgent = `Mozilla/5.0 (${deviceType}; CPU ${deviceType} OS ${formattedVersion} like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) FxiOS/${ffVersion}.0 Mobile/15E148 Safari/605.1.15`;
            }
            // Edge на iOS
            else if (browser === 'Edge') {
                const edgeVersion = Math.floor(Math.random() * 20) + 100;
                userAgent = `Mozilla/5.0 (${deviceType}; CPU ${deviceType} OS ${formattedVersion} like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) EdgiOS/${edgeVersion}.0.${Math.floor(Math.random() * 1000)}.${Math.floor(Math.random() * 100)} Mobile/15E148 Safari/605.1.15`;
            }
            // Opera на iOS
            else if (browser === 'Opera') {
                const operaVersion = Math.floor(Math.random() * 10) + 18;
                userAgent = `Mozilla/5.0 (${deviceType}; CPU ${deviceType} OS ${formattedVersion} like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) OPiOS/${operaVersion}.0.${Math.floor(Math.random() * 1000)}.${Math.floor(Math.random() * 100)} Mobile/15E148 Safari/605.1.15`;
            }
        }
        // Для Android устройств
        else {
            const actualModel = customModel || model;
            const actualVersion = customOSVersion || osVersion;

            // Генерация для разных браузеров
            if (browser === 'Chrome') {
                // Генерируем случайную версию Chrome
                const chromeVersion = Math.floor(Math.random() * 20) + 110;
                const chromeSubVersion = Math.floor(Math.random() * 5000);
                const randomNum = Math.floor(Math.random() * 100);

                userAgent = `Mozilla/5.0 (Linux; Android ${actualVersion}; ${actualModel}) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/${chromeVersion}.0.${chromeSubVersion}.${randomNum} Mobile Safari/537.36`;
            }
            else if (browser === 'Firefox') {
                // Генерируем версию Firefox
                const ffVersion = Math.floor(Math.random() * 30) + 110;
                userAgent = `Mozilla/5.0 (Android ${actualVersion}; Mobile; rv:${ffVersion}.0) Gecko/${ffVersion}.0 Firefox/${ffVersion}.0`;
            }
            else if (browser === 'Edge') {
                // Для Edge
                const edgeVersion = Math.floor(Math.random() * 20) + 110;
                userAgent = `Mozilla/5.0 (Linux; Android ${actualVersion}; ${actualModel}) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/${edgeVersion}.0.0.0 Mobile Safari/537.36 EdgA/${edgeVersion}.0.${Math.floor(Math.random() * 1000)}.${Math.floor(Math.random() * 100)}`;
            }
            else if (browser === 'Opera') {
                // Для Opera
                const operaVersion = Math.floor(Math.random() * 10) + 70;
                userAgent = `Mozilla/5.0 (Linux; Android ${actualVersion}; ${actualModel}) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/${operaVersion}.0.${Math.floor(Math.random() * 3000)}.${Math.floor(Math.random() * 100)} Mobile Safari/537.36 OPR/${operaVersion}.${Math.floor(Math.random() * 10)}.${Math.floor(Math.random() * 100)}`;
            }
            else if (browser === 'Safari') {
                // Safari на Android (редкий случай, но возможный)
                userAgent = `Mozilla/5.0 (Linux; Android ${actualVersion}; ${actualModel}) AppleWebKit/537.36 (KHTML, like Gecko) Version/4.0 Chrome/${Math.floor(Math.random() * 20) + 110}.0.${Math.floor(Math.random() * 5000)}.${Math.floor(Math.random() * 100)} Mobile Safari/537.36`;
            }
            else {
                // По умолчанию Chrome
                const chromeVersion = Math.floor(Math.random() * 20) + 110;
                userAgent = `Mozilla/5.0 (Linux; Android ${actualVersion}; ${actualModel}) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/${chromeVersion}.0.${Math.floor(Math.random() * 5000)}.${Math.floor(Math.random() * 100)} Mobile Safari/537.36`;
            }
        }

        return userAgent;
    };

    // Обновляем генерированный User-Agent при изменении параметров
    useEffect(() => {
        const newUserAgent = generateUserAgent();
        setGeneratedUserAgent(newUserAgent);
    }, [deviceType, model, osVersion, customModel, customOSVersion, browser]);

    // Форматирование User-Agent для отображения пользователю
    const formatUserAgentForDisplay = (ua) => {
        if (!ua) return 'Выберите модель устройства';

        let result = '';
        let browserInfo = '';

        // Определяем браузер
        if (ua.includes('CriOS') || (ua.includes('Chrome') && !ua.includes('Edg'))) {
            browserInfo = 'Chrome';
        } else if (ua.includes('FxiOS') || ua.includes('Firefox')) {
            browserInfo = 'Firefox';
        } else if ((ua.includes('Safari') && !ua.includes('Chrome')) || ua.includes('Version')) {
            browserInfo = 'Safari';
        } else if (ua.includes('EdgiOS') || ua.includes('Edg')) {
            browserInfo = 'Edge';
        } else if (ua.includes('OPiOS') || ua.includes('OPR')) {
            browserInfo = 'Opera';
        }

        if (ua.includes('iPhone') || ua.includes('iPad')) {
            const device = ua.includes('iPhone') ? 'iPhone' : 'iPad';
            const osMatch = ua.match(/OS ([0-9_]+)/);
            const osVersion = osMatch ? osMatch[1].replace('_', '.') : '?';

            result = `${device} с iOS ${osVersion}, ${browserInfo}`;
        }
        else if (ua.includes('Android')) {
            const versionMatch = ua.match(/Android ([0-9.]+)/);
            const modelMatch = ua.match(/Android [^;]+; ([^)]+)/);

            const version = versionMatch ? versionMatch[1] : '?';
            const model = modelMatch ? modelMatch[1] : '?';

            result = `${model} с Android ${version}, ${browserInfo}`;
        }

        return result;
    };

    const handleAutoGenerate = () => {
        setAutoMode(true);
        setDeviceType(detectCurrentDevice());
        setOsVersion(detectCurrentOSVersion());
        setBrowser(detectCurrentBrowser());
        setCustomModel('');
        setCustomOSVersion('');
        // Не устанавливаем модель автоматически - пользователь должен выбрать
        setModel('');
        setShowPreview(true);
    };

    const handleSave = () => {
        if (!generatedUserAgent) {
            // Если User-Agent не сгенерирован, сообщаем пользователю
            alert('Пожалуйста, выберите модель устройства');
            return;
        }
        onSave(generatedUserAgent);
        onClose();
    };

    // При выборе параметра вручную отключаем автоматический режим
    useEffect(() => {
        if (model || customModel) {
            setAutoMode(false);
        }
    }, [deviceType, model, osVersion, browser, customModel, customOSVersion]);

    // Создаем опции для селектов
    const createModelOptions = () => {
        let options = [
            { value: '', label: 'Выберите модель устройства' },
            { value: 'custom', label: 'Другое (ввести вручную)' }
        ];

        getPopularModels().forEach(m => {
            options.push({ value: m, label: m });
        });

        return options;
    };

    const createOSVersionOptions = () => {
        const versions = deviceType === 'iPhone' || deviceType === 'iPad' ? iOSVersions : androidVersions;
        let options = [
            { value: '', label: `Выберите версию ${deviceType === 'iPhone' || deviceType === 'iPad' ? 'iOS' : 'Android'}` },
            { value: 'current', label: `Текущая версия (${detectCurrentOSVersion()})` },
            { value: 'custom', label: 'Другая (ввести вручную)' }
        ];

        versions.forEach(v => {
            options.push({
                value: v,
                label: `${deviceType === 'iPhone' || deviceType === 'iPad' ? 'iOS' : 'Android'} ${v}`
            });
        });

        return options;
    };

    return (
        <motion.div 
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            className="fixed inset-0 bg-black/60 backdrop-blur-sm flex items-center justify-center z-50 p-4"
        >
            <motion.div
                initial={{ scale: 0.9, opacity: 0 }}
                animate={{ scale: 1, opacity: 1 }}
                exit={{ scale: 0.9, opacity: 0 }}
                className="w-full max-w-md rounded-2xl p-6 shadow-xl overflow-y-auto max-h-[90vh]"
                style={{ backgroundColor: 'var(--secondary-bg-color)' }}
            >
                {/* Заголовок */}
                <div className="flex justify-between items-center mb-6">
                    <h3 className="text-lg font-bold flex items-center" style={{ color: 'var(--text-color)' }}>
                        <Smartphone className="mr-2" size={20} />
                        Настройка устройства
                    </h3>
                    <button
                        className="p-1 rounded-full hover:bg-black hover:bg-opacity-10 transition-colors"
                        onClick={onClose}
                        style={{ color: 'var(--text-color)' }}
                    >
                        <X size={20} />
                    </button>
                </div>

                {/* Информация о назначении */}
                <div className="mb-6">
                    <button
                        className="text-sm flex items-center mb-2 font-medium"
                        onClick={() => setShowInfo(!showInfo)}
                        style={{ color: 'var(--button-color)' }}
                    >
                        <HelpCircle size={16} className="mr-1" />
                        Зачем это нужно?
                    </button>

                    <AnimatePresence>
                        {showInfo && (
                            <motion.div
                                initial={{ height: 0, opacity: 0 }}
                                animate={{ height: 'auto', opacity: 1 }}
                                exit={{ height: 0, opacity: 0 }}
                                className="overflow-hidden"
                            >
                                <div
                                    className="p-3 text-sm rounded-xl my-2"
                                    style={{
                                        backgroundColor: 'rgba(36, 129, 204, 0.1)',
                                        color: 'var(--text-color)'
                                    }}
                                >
                                    <p className="mb-2">
                                        ЛКС МИРЭА проверяет, с какого устройства выполняется вход. Если вы обычно заходите с iPhone, а бот попытается войти как Android, это может вызвать подозрения или ошибку.
                                    </p>
                                    <p>
                                        Выберите устройство, максимально похожее на ваше реальное, чтобы избежать проблем с авторизацией.
                                    </p>
                                </div>
                            </motion.div>
                        )}
                    </AnimatePresence>
                </div>

                {/* Предпросмотр User-Agent */}
                {showPreview && (
                    <div className="mb-4 p-3 rounded-lg" style={{
                        backgroundColor: 'rgba(36, 129, 204, 0.08)',
                        color: 'var(--text-color)',
                        border: '1px solid rgba(36, 129, 204, 0.2)'
                    }}>
                        <div className="text-sm font-medium mb-1">Текущие настройки:</div>
                        <div className="text-sm" style={{ color: 'var(--hint-color)' }}>
                            {formatUserAgentForDisplay(generatedUserAgent)}
                        </div>
                    </div>
                )}

                {/* Выбор типа устройства */}
                <div className="mb-4">
                    <label
                        className="block text-sm font-medium mb-2"
                        style={{ color: 'var(--text-color)' }}
                    >
                        Тип устройства
                    </label>
                    <div className="grid grid-cols-3 gap-2">
                        {['iPhone', 'Android', 'iPad'].map((type) => (
                            <button
                                key={type}
                                className={`p-3 rounded-xl border flex flex-col items-center justify-center transition-all ${deviceType === type ? 'border-[var(--button-color)] ring-1 ring-[var(--button-color)]' : 'border-gray-200'}`}
                                style={{
                                    backgroundColor: deviceType === type ? 'rgba(36, 129, 204, 0.1)' : 'var(--bg-color)',
                                    color: 'var(--text-color)'
                                }}
                                onClick={() => setDeviceType(type)}
                            >
                                {type === 'iPhone' && <Smartphone size={24} className="mb-1" />}
                                {type === 'Android' && <Smartphone size={24} className="mb-1" />}
                                {type === 'iPad' && <Tablet size={24} className="mb-1" />}
                                <span className="text-xs font-medium">{type}</span>
                            </button>
                        ))}
                    </div>
                </div>

                {/* Выбор модели */}
                <div className="mb-4">
                    <label
                        className="block text-sm font-medium mb-2"
                        style={{ color: 'var(--text-color)' }}
                    >
                        Модель устройства
                    </label>

                    <CustomSelect
                        value={model}
                        onChange={(value) => {
                            if (value === 'custom') {
                                setModel('custom');
                                setCustomModel('');
                            } else {
                                setModel(value);
                                setCustomModel('');
                            }
                        }}
                        options={createModelOptions()}
                        placeholder="Выберите модель устройства"
                    />

                    {model === 'custom' && (
                        <input
                            type="text"
                            placeholder="Введите модель устройства"
                            value={customModel}
                            onChange={(e) => setCustomModel(e.target.value)}
                            className="w-full p-3 rounded-xl border mt-2 outline-none focus:ring-2 focus:ring-blue-500/20"
                            style={{
                                backgroundColor: 'var(--bg-color)',
                                color: 'var(--text-color)',
                                borderColor: 'var(--hint-color)'
                            }}
                        />
                    )}
                </div>

                {/* Выбор версии ОС */}
                <div className="mb-4">
                    <label
                        className="block text-sm font-medium mb-2"
                        style={{ color: 'var(--text-color)' }}
                    >
                        Версия {deviceType === 'iPhone' || deviceType === 'iPad' ? 'iOS' : 'Android'}
                    </label>

                    <CustomSelect
                        value={osVersion}
                        onChange={(value) => {
                            if (value === 'current') {
                                setOsVersion(detectCurrentOSVersion());
                                setCustomOSVersion('');
                            } else if (value === 'custom') {
                                setOsVersion('custom');
                                setCustomOSVersion('');
                            } else {
                                setOsVersion(value);
                                setCustomOSVersion('');
                            }
                        }}
                        options={createOSVersionOptions()}
                        placeholder={`Выберите версию ${deviceType === 'iPhone' || deviceType === 'iPad' ? 'iOS' : 'Android'}`}
                    />

                    {osVersion === 'custom' && (
                        <input
                            type="text"
                            placeholder={`Введите версию ${deviceType === 'iPhone' || deviceType === 'iPad' ? 'iOS' : 'Android'}`}
                            value={customOSVersion}
                            onChange={(e) => setCustomOSVersion(e.target.value)}
                            className="w-full p-3 rounded-xl border mt-2 outline-none focus:ring-2 focus:ring-blue-500/20"
                            style={{
                                backgroundColor: 'var(--bg-color)',
                                color: 'var(--text-color)',
                                borderColor: 'var(--hint-color)'
                            }}
                        />
                    )}
                </div>

                {/* Выбор браузера (для iOS и Android) */}
                <div className="mb-6">
                    <label
                        className="block text-sm font-medium mb-2"
                        style={{ color: 'var(--text-color)' }}
                    >
                        Браузер
                    </label>
                    <div className="grid grid-cols-3 gap-2">
                        {browsers.map((b) => (
                            <button
                                key={b}
                                className={`p-2 rounded-xl border flex flex-col items-center justify-center transition-all ${browser === b ? 'border-[var(--button-color)] ring-1 ring-[var(--button-color)]' : 'border-gray-200'}`}
                                style={{
                                    backgroundColor: browser === b ? 'rgba(36, 129, 204, 0.1)' : 'var(--bg-color)',
                                    color: 'var(--text-color)',
                                    // Делаем Safari более выделяющимся для iOS
                                    borderWidth: (deviceType === 'iPhone' || deviceType === 'iPad') && b === 'Safari' ? '2px' : '1px'
                                }}
                                onClick={() => setBrowser(b)}
                            >
                                <Globe size={16} className="mb-1" />
                                <span className="text-xs font-medium">{b}</span>
                                {(deviceType === 'iPhone' || deviceType === 'iPad') && b === 'Safari' && (
                                    <span className="text-xs mt-1 font-bold" style={{ color: 'var(--button-color)' }}>
                                        (рекомендуется)
                                    </span>
                                )}
                            </button>
                        ))}
                    </div>
                </div>

                {/* Кнопки действий */}
                <div className="flex justify-end space-x-3">
                    <button
                        className="px-4 py-2.5 rounded-xl font-medium transition-colors hover:bg-gray-100"
                        style={{
                            backgroundColor: 'rgba(0,0,0,0.05)',
                            color: 'var(--text-color)'
                        }}
                        onClick={onClose}
                    >
                        Отмена
                    </button>
                    <button
                        className="px-4 py-2.5 rounded-xl flex items-center font-medium shadow-sm transition-transform active:scale-95"
                        style={{
                            backgroundColor: 'var(--button-color)',
                            color: 'var(--button-text-color)',
                            opacity: generatedUserAgent ? 1 : 0.5
                        }}
                        onClick={handleSave}
                        disabled={!generatedUserAgent}
                    >
                        <Check size={18} className="mr-2" />
                        Применить
                    </button>
                </div>
            </motion.div>
        </motion.div>
    );
};

export default UserAgentConstructor;