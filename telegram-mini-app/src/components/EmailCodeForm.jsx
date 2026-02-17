import React, { useState, useRef, useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { Mail, AlertTriangle, RefreshCw } from 'lucide-react';

const EmailCodeForm = ({ initData, onSuccess, onBack }) => {
  const [code, setCode] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const inputRef = useRef(null);

  useEffect(() => {
    inputRef.current?.focus();
  }, []);

  const handleSubmit = async (e) => {
    if (e) e.preventDefault();

    const trimmedCode = code.trim();
    if (!trimmedCode) {
      setError('Введите код из письма');
      return;
    }

    setLoading(true);
    setError('');

    try {
      const response = await fetch('/api/submit_email_code', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          initData,
          email_code: trimmedCode,
        }),
      });

      const data = await response.json();

      if (data.success) {
        onSuccess(data);
      } else if (data.requires_email_code) {
        // Неверный код - очищаем поле
        setCode('');
        setError(data.message || 'Неверный код. Попробуйте снова.');
        inputRef.current?.focus();
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

  const handleKeyPress = (e) => {
    if (e.key === 'Enter') {
      handleSubmit();
    }
  };

  const handleRetry = () => {
    setCode('');
    setError('');
    inputRef.current?.focus();
  };

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
            className="flex items-center justify-center h-20 w-20 mx-auto mb-6 rounded-2xl shadow-lg shadow-blue-500/30 bg-gradient-to-br from-blue-500 to-cyan-500"
          >
            <Mail size={32} className="text-white" />
          </motion.div>
          <h2 className="text-2xl font-bold mb-2 text-[var(--text-color)]">
            Подтверждение по email
          </h2>
          <p className="text-sm opacity-70 text-[var(--hint-color)]">
            На вашу почту МИРЭА отправлен код подтверждения
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

        {/* Code Input */}
        <div className="p-6 pt-0">
          <div className="mb-6">
            <motion.input
              ref={inputRef}
              type="text"
              inputMode="numeric"
              placeholder="Введите код из письма"
              value={code}
              onChange={(e) => {
                setCode(e.target.value);
                setError('');
              }}
              onKeyPress={handleKeyPress}
              disabled={loading}
              className={`w-full h-14 text-center text-2xl font-bold rounded-xl border-2 transition-all outline-none
                ${error ? 'border-red-500/50 bg-red-500/5' : 'border-white/20 bg-white/5'}
                focus:border-blue-500 focus:ring-2 focus:ring-blue-500/20
                text-[var(--text-color)] placeholder-[var(--hint-color)] placeholder:text-base placeholder:font-normal
                ${loading ? 'opacity-50' : ''}`}
              initial={{ scale: 0.95 }}
              animate={{ scale: 1 }}
            />
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
                className="w-5 h-5 border-2 border-blue-500 border-t-transparent rounded-full"
              />
              <span className="text-sm">Проверка кода...</span>
            </motion.div>
          )}

          {/* Info text */}
          <p className="text-xs text-center opacity-60 text-[var(--text-color)] mb-6">
            Проверьте почту МИРЭА и введите код подтверждения из письма
          </p>
        </div>

        {/* Buttons */}
        <div className="p-6 pt-0 space-y-3">
          <motion.button
            whileHover={{ scale: 1.02 }}
            whileTap={{ scale: 0.98 }}
            className="w-full h-12 rounded-xl shadow-lg shadow-blue-500/20 flex items-center justify-center font-semibold text-white bg-gradient-to-r from-blue-500 to-cyan-500"
            style={{ opacity: !code.trim() ? 0.6 : 1 }}
            onClick={() => handleSubmit()}
            disabled={loading || !code.trim()}
          >
            Подтвердить
          </motion.button>

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
    </motion.div>
  );
};

export default EmailCodeForm;
