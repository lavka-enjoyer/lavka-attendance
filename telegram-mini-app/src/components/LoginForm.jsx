import React, { useState, useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { getModifiedUserAgent } from '../utils/telegramUtils';
import UserAgentConstructor from './UserAgentConstructor';
import EmailCodeForm from './EmailCodeForm';
import { Smartphone, Settings, AlertTriangle, HelpCircle, LogIn, User, Lock } from 'lucide-react';

// Функция безопасной отправки данных авторизации
const safeUpdateUser = async (initData, login, password, customUserAgent = null) => {
  try {
    // Получаем User-Agent (кастомный или автоматически сгенерированный)
    const userAgent = customUserAgent || getModifiedUserAgent();

    // Прямой запрос без использования apiService
    const response = await fetch('/api/update_user', {
      method: 'PATCH',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        initData,
        login,
        password,
        user_agent: userAgent
      })
    });

    // Получаем ответ как текст для анализа
    const responseText = await response.text();

    let data;
    try {
      // Пытаемся распарсить JSON
      data = JSON.parse(responseText);
    } catch (e) {
      // Если не JSON, используем текст как есть
      return { success: response.ok, error: response.ok ? null : responseText };
    }

    // Проверяем на требование email кода (info.requires_email_code)
    if (data && data.info && data.info.requires_email_code) {
      return { success: false, data: { requires_email_code: true, message: data.info.message } };
    }

    // Проверяем на наличие ошибки в данных
    if (data && (data.detail || data.message || data.error || data.msg)) {
      const errorMessage = data.detail || data.message || data.error || data.msg;
      return { success: false, error: errorMessage };
    }

    // Если статус успешный и нет явных ошибок в данных
    if (response.ok) {
      return { success: true, data };
    }

    // По умолчанию считаем ошибкой
    return { success: false, error: "Неизвестная ошибка авторизации" };
  } catch (error) {
    return { success: false, error: error.message || "Ошибка сети" };
  }
};

// Функция безопасного получения данных пользователя
const safeGetUserData = async (initData) => {
  try {
    const response = await fetch(`/api/checker?initData=${encodeURIComponent(initData)}`);

    const responseText = await response.text();

    try {
      const data = JSON.parse(responseText);

      // Проверка на валидность данных пользователя
      if (data && data.FIO && data.group) {
        return { success: true, data };
      }

      // Проверяем на наличие ошибки в данных
      if (data && (data.detail || data.message || data.error || data.msg)) {
        const errorMessage = data.detail || data.message || data.error || data.msg;
        return { success: false, error: errorMessage };
      }

      return { success: false, error: "Данные пользователя некорректны" };
    } catch (e) {
      return { success: false, error: responseText || "Неверный формат ответа" };
    }
  } catch (error) {
    return { success: false, error: error.message || "Ошибка сети" };
  }
};

const LoginForm = ({ initData, onLoginSuccess }) => {
  const [credentials, setCredentials] = useState({ login: '', password: '' });
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [showUserAgentModal, setShowUserAgentModal] = useState(false);
  const [customUserAgent, setCustomUserAgent] = useState('');
  const [deviceInfo, setDeviceInfo] = useState('Выберите устройство');
  const [showEmailCodeForm, setShowEmailCodeForm] = useState(false);

  // Определяем читаемое устройство из User-Agent
  const formatUserAgentForDisplay = (ua) => {
    if (!ua) return 'Выберите устройство';

    if (ua.includes('iPhone') || ua.includes('iPad')) {
      const device = ua.includes('iPhone') ? 'iPhone' : 'iPad';
      const osMatch = ua.match(/OS ([0-9_]+)/);
      const osVersion = osMatch ? osMatch[1].replace('_', '.') : '?';

      // Определяем браузер для iOS
      let browser = 'Safari';
      if (ua.includes('CriOS')) browser = 'Chrome';
      if (ua.includes('FxiOS')) browser = 'Firefox';
      if (ua.includes('EdgiOS')) browser = 'Edge';
      if (ua.includes('OPiOS')) browser = 'Opera';

      return `${device} с iOS ${osVersion}, ${browser}`;
    }
    else if (ua.includes('Android')) {
      const versionMatch = ua.match(/Android ([0-9.]+)/);
      const modelMatch = ua.match(/Android [^;]+; ([^)]+)/);

      const version = versionMatch ? versionMatch[1] : '?';
      const model = modelMatch ? modelMatch[1] : '?';

      // Определяем браузер для Android
      let browser = 'Chrome';
      if (ua.includes('Firefox')) browser = 'Firefox';
      if (ua.includes('Edg')) browser = 'Edge';
      if (ua.includes('OPR')) browser = 'Opera';

      return `${model} с Android ${version}, ${browser}`;
    }

    return 'Выберите устройство';
  };

  useEffect(() => {
    if (customUserAgent) {
      setDeviceInfo(formatUserAgentForDisplay(customUserAgent));
    }
  }, [customUserAgent]);

  const handleLogin = async () => {
    // Проверка заполненности полей
    if (!credentials.login || !credentials.password) {
      setError('Пожалуйста, заполните все поля');
      return;
    }

    // Проверка наличия User-Agent
    if (!customUserAgent) {
      setError('Пожалуйста, выберите устройство');
      setShowUserAgentModal(true);
      return;
    }

    setLoading(true);
    setError('');

    try {
      // Шаг 1: Отправляем данные авторизации с опциональным кастомным User-Agent
      const updateResult = await safeUpdateUser(
          initData,
          credentials.login,
          credentials.password,
          customUserAgent || null  // Если есть кастомный - используем его, иначе null (будет использован автоматический)
      );

      if (!updateResult.success) {
        // Проверяем, нужен ли email код
        if (updateResult.data && updateResult.data.requires_email_code) {
          setShowEmailCodeForm(true);
          setLoading(false);
          return;
        }

        // Специальная обработка ошибки неверного логина/пароля
        if (updateResult.error && updateResult.error.includes("Неверный логин или пароль")) {
          setError('Неверный логин или пароль');
        } else {
          setError(updateResult.error || 'Ошибка авторизации');
        }
        setLoading(false);
        return;
      }

      // Шаг 2: Получаем данные пользователя после успешной авторизации
      const userDataResult = await safeGetUserData(initData);

      if (userDataResult.success && userDataResult.data) {
        onLoginSuccess(userDataResult.data);
      } else {
        setError(userDataResult.error || 'Не удалось получить данные пользователя');
      }
    } catch (err) {
      setError(err.message || 'Произошла ошибка при входе');
    } finally {
      setLoading(false);
    }
  };

  // Обработчик успешной проверки email кода
  const handleEmailCodeSuccess = async () => {
    setShowEmailCodeForm(false);
    setLoading(true);

    try {
      const userDataResult = await safeGetUserData(initData);

      if (userDataResult.success && userDataResult.data) {
        onLoginSuccess(userDataResult.data);
      } else {
        setError(userDataResult.error || 'Не удалось получить данные пользователя');
      }
    } catch (err) {
      setError(err.message || 'Произошла ошибка при получении данных');
    } finally {
      setLoading(false);
    }
  };

  // Обработчик возврата из email code формы
  const handleEmailCodeBack = () => {
    setShowEmailCodeForm(false);
  };

  const handleKeyPress = (e) => {
    if (e.key === 'Enter') {
      handleLogin();
    }
  };

  const handleUserAgentSave = (userAgent) => {
    setCustomUserAgent(userAgent);
    setShowUserAgentModal(false);
  };

  // Показываем email code форму если требуется подтверждение по email
  if (showEmailCodeForm) {
    return (
      <EmailCodeForm
        initData={initData}
        onSuccess={handleEmailCodeSuccess}
        onBack={handleEmailCodeBack}
      />
    );
  }

  return (
      <motion.div 
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        exit={{ opacity: 0, y: -20 }}
        className="p-4 w-full max-w-md mx-auto min-h-screen flex flex-col justify-center bg-[var(--bg-color)]" 
      >
        <motion.div 
          className="rounded-3xl shadow-2xl overflow-hidden glass" 
          initial={{ scale: 0.95 }}
          animate={{ scale: 1 }}
          transition={{ type: "spring", stiffness: 300, damping: 30 }}
        >
          {/* Header */}
          <div className="p-8 text-center pb-6">
            <motion.div 
              initial={{ scale: 0 }}
              animate={{ scale: 1 }}
              transition={{ type: "spring", stiffness: 400, damping: 20, delay: 0.1 }}
              className="flex items-center justify-center h-20 w-20 mx-auto mb-6 rounded-2xl shadow-lg shadow-blue-500/30 bg-[var(--button-color)]" 
            >
              <LogIn size={32} className="text-white ml-1" />
            </motion.div>
            <h2 className="text-2xl font-bold mb-2 text-[var(--text-color)]">
              Авторизация
            </h2>
            <p className="text-sm opacity-70 text-[var(--hint-color)]">
              Войдите в свой аккаунт (ЛКС МИРЭА)
            </p>
          </div>

          {/* Error message */}
          <AnimatePresence>
            {error && (
                <motion.div 
                  initial={{ opacity: 0, height: 0 }}
                  animate={{ opacity: 1, height: 'auto' }}
                  exit={{ opacity: 0, height: 0 }}
                  className="px-6 mb-4"
                >
                  <div className="p-3 rounded-xl flex items-center bg-red-500/10 text-red-500 border border-red-500/20">
                    <AlertTriangle size={18} className="mr-2 flex-shrink-0" />
                    <span className="text-sm font-medium">{error}</span>
                  </div>
                </motion.div>
            )}
          </AnimatePresence>

          {/* Login form */}
          <div className="p-6 pt-0 space-y-5">
            <div className="space-y-3">
              <div className="relative">
                <User className="absolute left-4 top-3.5 text-[var(--hint-color)]" size={20} />
                <input
                    placeholder="Логин"
                    value={credentials.login}
                    onChange={(e) =>
                        setCredentials((prev) => ({ ...prev, login: e.target.value }))
                    }
                    onKeyPress={handleKeyPress}
                    disabled={loading}
                    className="rounded-xl pl-12 pr-4 py-3 h-12 w-full border transition-all focus:ring-2 focus:ring-blue-500/20 outline-none bg-white/5 border-white/10 text-[var(--text-color)] placeholder-[var(--hint-color)]"
                />
              </div>
              <div className="relative">
                <Lock className="absolute left-4 top-3.5 text-[var(--hint-color)]" size={20} />
                <input
                    type="password"
                    placeholder="Пароль"
                    value={credentials.password}
                    onChange={(e) =>
                        setCredentials((prev) => ({ ...prev, password: e.target.value }))
                    }
                    onKeyPress={handleKeyPress}
                    disabled={loading}
                    className="rounded-xl pl-12 pr-4 py-3 h-12 w-full border transition-all focus:ring-2 focus:ring-blue-500/20 outline-none bg-white/5 border-white/10 text-[var(--text-color)] placeholder-[var(--hint-color)]"
                />
              </div>
            </div>

            {/* Device settings */}
            <div className="flex flex-col gap-2">
              <motion.button
                  whileHover={{ scale: 1.01 }}
                  whileTap={{ scale: 0.99 }}
                  className={`flex items-center justify-between p-3 rounded-xl border transition-colors ${
                    !customUserAgent 
                      ? 'bg-red-500/5 border-red-500/20' 
                      : 'bg-blue-500/5 border-blue-500/20'
                  }`}
                  onClick={() => setShowUserAgentModal(true)}
              >
                <div className="flex items-center">
                  <Smartphone size={18} className={`mr-3 ${!customUserAgent ? 'text-red-500' : 'text-[var(--button-color)]'}`} />
                  <span className="text-sm font-medium text-[var(--text-color)]">Устройство: {deviceInfo}</span>
                </div>
                <Settings size={16} className="text-[var(--hint-color)]" />
              </motion.button>
              
              <div className="flex items-start gap-2 px-2">
                <HelpCircle size={14} className="mt-0.5 flex-shrink-0 text-[var(--button-color)]" />
                <span className="text-xs opacity-60 text-[var(--text-color)]">
                  Выберите устройство, с которого обычно заходите в ЛКС, чтобы избежать проблем с авторизацией
                </span>
              </div>
            </div>
          </div>

          {/* Login button */}
          <div className="p-6 pt-2">
            <motion.button
                whileHover={{ scale: 1.02 }}
                whileTap={{ scale: 0.98 }}
                className="w-full h-12 rounded-xl shadow-lg shadow-blue-500/20 flex items-center justify-center font-semibold text-white relative overflow-hidden bg-[var(--button-color)]"
                style={{
                  opacity: (!credentials.login || !credentials.password || !customUserAgent) ? 0.6 : 1
                }}
                onClick={handleLogin}
                disabled={loading || !credentials.login || !credentials.password || !customUserAgent}
            >
              {loading ? (
                  <div className="flex items-center justify-center gap-2">
                    <motion.div 
                      animate={{ rotate: 360 }}
                      transition={{ duration: 1, repeat: Infinity, ease: "linear" }}
                      className="w-5 h-5 border-2 border-white border-t-transparent rounded-full"
                    />
                    <span>Вход...</span>
                  </div>
              ) : (
                  'Войти'
              )}
            </motion.button>
          </div>
        </motion.div>

        {/* User Agent Modal */}
        <AnimatePresence>
          {showUserAgentModal && (
              <UserAgentConstructor
                  onClose={() => setShowUserAgentModal(false)}
                  onSave={handleUserAgentSave}
                  initialUserAgent={customUserAgent}
              />
          )}
        </AnimatePresence>
      </motion.div>
  );
};

export default LoginForm;