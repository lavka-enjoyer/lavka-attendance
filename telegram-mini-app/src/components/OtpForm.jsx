import React, { useState, useRef, useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { Shield, AlertTriangle, RefreshCw, Sparkles, X, Key, ChevronRight } from 'lucide-react';
import TotpSetupGuide from './TotpSetupGuide';

const OtpForm = ({ initData, onSuccess, onBack, hasTotpSecret = false }) => {
  const [otp, setOtp] = useState(['', '', '', '', '', '']);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [showSetupGuide, setShowSetupGuide] = useState(false);
  const [bannerDismissed, setBannerDismissed] = useState(false);
  const [otpCredentials, setOtpCredentials] = useState([]);
  const [showCredentialSelect, setShowCredentialSelect] = useState(false);
  const [selectedCredential, setSelectedCredential] = useState(null);
  const inputRefs = useRef([]);

  // Загружаем credentials при монтировании
  useEffect(() => {
    const fetchCredentials = async () => {
      try {
        const response = await fetch(`/api/check_totp_session?initData=${encodeURIComponent(initData)}`);
        const data = await response.json();

        if (data.has_session && data.otp_credentials && data.otp_credentials.length > 1) {
          setOtpCredentials(data.otp_credentials);
          setShowCredentialSelect(true);
        }
      } catch (err) {
        console.error('Error fetching credentials:', err);
      }
    };

    fetchCredentials();
  }, [initData]);

  useEffect(() => {
    // Автофокус на первое поле только когда не показываем выбор credential
    if (inputRefs.current[0] && !showCredentialSelect) {
      inputRefs.current[0].focus();
    }
  }, [showCredentialSelect]);

  const handleSelectCredential = async (credential) => {
    setLoading(true);
    setError('');

    try {
      const response = await fetch('/api/select_otp_credential', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          initData,
          credential_id: credential.id
        })
      });

      const data = await response.json();

      if (data.success) {
        setSelectedCredential(credential);
        setShowCredentialSelect(false);
        // Фокус на первое поле ввода OTP
        setTimeout(() => {
          inputRefs.current[0]?.focus();
        }, 100);
      } else {
        setError(data.error || 'Ошибка выбора метода 2FA');
      }
    } catch (err) {
      setError(err.message || 'Ошибка сети');
    } finally {
      setLoading(false);
    }
  };

  const handleChange = (index, value) => {
    // Разрешаем только цифры
    if (value && !/^\d$/.test(value)) return;

    const newOtp = [...otp];
    newOtp[index] = value;
    setOtp(newOtp);
    setError('');

    // Автоматический переход к следующему полю
    if (value && index < 5) {
      inputRefs.current[index + 1]?.focus();
    }

    // Автоматическая отправка когда все поля заполнены
    if (value && index === 5) {
      const fullOtp = newOtp.join('');
      if (fullOtp.length === 6) {
        handleSubmit(fullOtp);
      }
    }
  };

  const handleKeyDown = (index, e) => {
    if (e.key === 'Backspace' && !otp[index] && index > 0) {
      inputRefs.current[index - 1]?.focus();
    }
  };

  const handlePaste = (e) => {
    e.preventDefault();
    const pastedData = e.clipboardData.getData('text').replace(/\D/g, '').slice(0, 6);
    if (pastedData.length === 6) {
      const newOtp = pastedData.split('');
      setOtp(newOtp);
      inputRefs.current[5]?.focus();
      handleSubmit(pastedData);
    }
  };

  const handleSubmit = async (otpCode) => {
    if (otpCode.length !== 6) {
      setError('Введите 6-значный код');
      return;
    }

    setLoading(true);
    setError('');

    try {
      const response = await fetch('/api/submit_otp', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          initData,
          otp_code: otpCode
        })
      });

      const data = await response.json();

      if (data.success) {
        onSuccess(data);
      } else if (data.requires_2fa) {
        // Неверный код - очищаем поля
        setOtp(['', '', '', '', '', '']);
        setError(data.message || 'Неверный код. Попробуйте снова.');
        inputRefs.current[0]?.focus();

        // Обновляем credentials если вернулись новые
        if (data.otp_credentials && data.otp_credentials.length > 1) {
          setOtpCredentials(data.otp_credentials);
        }
      } else if (data.error) {
        setError(data.error);
      } else {
        setError('Произошла ошибка. Попробуйте позже.');
      }
    } catch (err) {
      setError(err.message || 'Ошибка сети');
    } finally {
      setLoading(false);
    }
  };

  const handleRetry = () => {
    setOtp(['', '', '', '', '', '']);
    setError('');
    inputRefs.current[0]?.focus();
  };

  const handleChangeCredential = () => {
    setShowCredentialSelect(true);
    setOtp(['', '', '', '', '', '']);
    setError('');
  };

  // Экран выбора credential
  if (showCredentialSelect && otpCredentials.length > 1) {
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
              className="flex items-center justify-center h-20 w-20 mx-auto mb-6 rounded-2xl shadow-lg shadow-blue-500/30 bg-gradient-to-br from-blue-500 to-blue-600"
            >
              <Key size={32} className="text-white" />
            </motion.div>
            <h2 className="text-2xl font-bold mb-2 text-[var(--text-color)]">
              Выберите метод 2FA
            </h2>
            <p className="text-sm opacity-70 text-[var(--hint-color)]">
              У вас настроено несколько аутентификаторов
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

          {/* Credentials list */}
          <div className="p-6 pt-0 space-y-3">
            {otpCredentials.map((credential, index) => (
              <motion.button
                key={credential.id}
                initial={{ opacity: 0, x: -20 }}
                animate={{ opacity: 1, x: 0 }}
                transition={{ delay: index * 0.1 }}
                whileHover={{ scale: 1.02 }}
                whileTap={{ scale: 0.98 }}
                onClick={() => handleSelectCredential(credential)}
                disabled={loading}
                className={`w-full p-4 rounded-xl border border-white/20 bg-white/5 flex items-center justify-between
                  hover:bg-white/10 transition-colors
                  ${loading ? 'opacity-50 cursor-not-allowed' : 'cursor-pointer'}`}
              >
                <div className="flex items-center gap-3">
                  <div className="p-2 rounded-lg bg-purple-500/20">
                    <Key size={20} className="text-purple-400" />
                  </div>
                  <div className="text-left">
                    <h4 className="font-semibold text-[var(--text-color)]">
                      {credential.userLabel || `Аутентификатор ${index + 1}`}
                    </h4>
                    <p className="text-xs text-[var(--hint-color)]">
                      Нажмите для выбора
                    </p>
                  </div>
                </div>
                <ChevronRight size={20} className="text-[var(--hint-color)]" />
              </motion.button>
            ))}
          </div>

          {/* Loading indicator */}
          {loading && (
            <div className="p-6 pt-0">
              <motion.div
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                className="flex items-center justify-center gap-2 text-[var(--hint-color)]"
              >
                <motion.div
                  animate={{ rotate: 360 }}
                  transition={{ duration: 1, repeat: Infinity, ease: "linear" }}
                  className="w-5 h-5 border-2 border-purple-500 border-t-transparent rounded-full"
                />
                <span className="text-sm">Выбор метода...</span>
              </motion.div>
            </div>
          )}

          {/* Info text */}
          <div className="p-6 pt-0">
            <p className="text-xs text-center opacity-60 text-[var(--text-color)]">
              Выберите аутентификатор, который вы используете для входа в MIREA
            </p>
          </div>
        </motion.div>
      </motion.div>
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
            className="flex items-center justify-center h-20 w-20 mx-auto mb-6 rounded-2xl shadow-lg shadow-purple-500/30 bg-gradient-to-br from-purple-500 to-purple-600"
          >
            <Shield size={32} className="text-white" />
          </motion.div>
          <h2 className="text-2xl font-bold mb-2 text-[var(--text-color)]">
            Двухфакторная аутентификация
          </h2>
          <p className="text-sm opacity-70 text-[var(--hint-color)]">
            {selectedCredential
              ? `Введите код из "${selectedCredential.userLabel}"`
              : 'Введите код из приложения для mirea.ru'
            }
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

        {/* Selected credential info */}
        {selectedCredential && otpCredentials.length > 1 && (
          <div className="px-6 mb-4">
            <button
              onClick={handleChangeCredential}
              className="w-full p-3 rounded-xl bg-blue-500/10 border border-blue-500/20 flex items-center justify-between hover:bg-blue-500/20 transition-colors"
            >
              <div className="flex items-center gap-2">
                <Key size={16} className="text-blue-400" />
                <span className="text-sm text-[var(--text-color)]">
                  {selectedCredential.userLabel}
                </span>
              </div>
              <span className="text-xs text-blue-400">Изменить</span>
            </button>
          </div>
        )}

        {/* Auto-TOTP Setup Banner */}
        <AnimatePresence>
          {!hasTotpSecret && !bannerDismissed && (
            <motion.div
              initial={{ opacity: 0, height: 0 }}
              animate={{ opacity: 1, height: 'auto' }}
              exit={{ opacity: 0, height: 0 }}
              className="px-6 mb-4"
            >
              <div
                className="p-4 rounded-xl bg-gradient-to-r from-purple-500/20 to-blue-500/20 border border-purple-500/30 cursor-pointer relative"
                onClick={() => setShowSetupGuide(true)}
              >
                <button
                  onClick={(e) => {
                    e.stopPropagation();
                    setBannerDismissed(true);
                  }}
                  className="absolute top-2 right-2 p-1 rounded-full hover:bg-white/10 transition-colors"
                >
                  <X size={16} className="text-[var(--hint-color)]" />
                </button>
                <div className="flex items-start gap-3">
                  <div className="p-2 rounded-lg bg-purple-500/20">
                    <Sparkles size={20} className="text-purple-400" />
                  </div>
                  <div className="flex-1 pr-4">
                    <h4 className="font-semibold text-[var(--text-color)] text-sm mb-1">
                      Больше не вводить код?
                    </h4>
                    <p className="text-xs text-[var(--hint-color)]">
                      Настройте автоматический ввод TOTP-кода
                    </p>
                  </div>
                </div>
              </div>
            </motion.div>
          )}
        </AnimatePresence>

        {/* OTP Input */}
        <div className="p-6 pt-0">
          <div className="flex justify-center gap-2 mb-6">
            {otp.map((digit, index) => (
              <motion.input
                key={index}
                ref={el => inputRefs.current[index] = el}
                type="text"
                inputMode="numeric"
                maxLength={1}
                value={digit}
                onChange={(e) => handleChange(index, e.target.value)}
                onKeyDown={(e) => handleKeyDown(index, e)}
                onPaste={handlePaste}
                disabled={loading}
                className={`w-12 h-14 text-center text-2xl font-bold rounded-xl border-2 transition-all outline-none
                  ${error ? 'border-red-500/50 bg-red-500/5' : 'border-white/20 bg-white/5'}
                  focus:border-purple-500 focus:ring-2 focus:ring-purple-500/20
                  text-[var(--text-color)] placeholder-[var(--hint-color)]
                  ${loading ? 'opacity-50' : ''}`}
                initial={{ scale: 0 }}
                animate={{ scale: 1 }}
                transition={{ delay: index * 0.05 }}
              />
            ))}
          </div>

          {/* Loading indicator */}
          {loading && (
            <motion.div
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              className="flex items-center justify-center gap-2 mb-4 text-[var(--hint-color)]"
            >
              <motion.div
                animate={{ rotate: 360 }}
                transition={{ duration: 1, repeat: Infinity, ease: "linear" }}
                className="w-5 h-5 border-2 border-purple-500 border-t-transparent rounded-full"
              />
              <span className="text-sm">Проверка кода...</span>
            </motion.div>
          )}

          {/* Info text */}
          <p className="text-xs text-center opacity-60 text-[var(--text-color)] mb-6">
            Откройте приложение-аутентификатор и введите 6-значный код для вашего аккаунта mirea.ru
          </p>
        </div>

        {/* Buttons */}
        <div className="p-6 pt-0">
          <motion.button
            whileHover={{ scale: 1.02 }}
            whileTap={{ scale: 0.98 }}
            className="w-full h-12 rounded-xl border border-white/20 flex items-center justify-center font-medium text-[var(--text-color)] bg-white/5"
            onClick={handleRetry}
            disabled={loading}
          >
            <RefreshCw size={18} className="mr-2" />
            Очистить
          </motion.button>
        </div>
      </motion.div>

      {/* TOTP Setup Guide Modal */}
      <TotpSetupGuide
        isOpen={showSetupGuide}
        onClose={() => setShowSetupGuide(false)}
      />
    </motion.div>
  );
};

export default OtpForm;
