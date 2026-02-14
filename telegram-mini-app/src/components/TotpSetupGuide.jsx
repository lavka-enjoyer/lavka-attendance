import React from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { X, Smartphone, QrCode, Send, CheckCircle, ExternalLink } from 'lucide-react';

const TotpSetupGuide = ({ isOpen, onClose }) => {
  const botUsername = import.meta.env.VITE_BOT_USERNAME;

  const handleOpenBot = () => {
    // Открываем бота в Telegram
    window.open(`https://t.me/${botUsername}`, '_blank');
  };

  const steps = [
    {
      icon: Smartphone,
      title: 'Откройте ваш аутентификатор',
      description: (
        <>
          <span className="block">Google Authenticator, Aegis, Bitwarden, 1Password или другой</span>
        </>
      ),
    },
    {
      icon: QrCode,
      title: 'Экспортируйте ключ MIREA',
      description: (
        <>
          <span className="block mb-2">
            <strong>Google Authenticator:</strong> меню (⋮) → Экспорт аккаунтов
          </span>
          <span className="block mb-2">
            <strong>Другие:</strong> найдите функцию экспорта или показа QR-кода
          </span>
          <span className="block text-xs opacity-70">
            Выберите только аккаунт MIREA/РТУ и сделайте скриншот QR-кода
          </span>
        </>
      ),
    },
    {
      icon: Send,
      title: 'Отправьте QR-код боту',
      description: 'Отправьте скриншот с QR-кодом в чат с ботом',
    },
    {
      icon: CheckCircle,
      title: 'Готово!',
      description: 'Код будет вводиться автоматически при каждом входе',
    },
  ];

  return (
    <AnimatePresence>
      {isOpen && (
        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          exit={{ opacity: 0 }}
          className="fixed inset-0 z-50 flex items-end justify-center bg-black/60 backdrop-blur-sm"
          onClick={onClose}
        >
          <motion.div
            initial={{ y: '100%' }}
            animate={{ y: 0 }}
            exit={{ y: '100%' }}
            transition={{ type: 'spring', damping: 30, stiffness: 300 }}
            className="w-full max-w-md max-h-[90vh] overflow-y-auto rounded-t-3xl bg-[var(--bg-color)] shadow-2xl"
            onClick={(e) => e.stopPropagation()}
          >
            {/* Header */}
            <div className="sticky top-0 z-10 bg-[var(--bg-color)] p-4 pb-2 border-b border-white/10">
              <div className="flex items-center justify-between">
                <h2 className="text-xl font-bold text-[var(--text-color)]">
                  Автоматический ввод кода
                </h2>
                <button
                  onClick={onClose}
                  className="p-2 rounded-full hover:bg-white/10 transition-colors"
                >
                  <X size={20} className="text-[var(--hint-color)]" />
                </button>
              </div>
              <p className="text-sm text-[var(--hint-color)] mt-1">
                Настройте один раз — забудьте о ручном вводе
              </p>
            </div>

            {/* Content */}
            <div className="p-4">
              {/* Steps */}
              <div className="space-y-4">
                {steps.map((step, index) => (
                  <motion.div
                    key={index}
                    initial={{ opacity: 0, x: -20 }}
                    animate={{ opacity: 1, x: 0 }}
                    transition={{ delay: index * 0.1 }}
                    className="flex gap-4"
                  >
                    <div className="flex-shrink-0">
                      <div className="w-10 h-10 rounded-xl bg-purple-500/20 flex items-center justify-center">
                        <step.icon size={20} className="text-purple-400" />
                      </div>
                    </div>
                    <div className="flex-1 pt-1">
                      <h4 className="font-semibold text-[var(--text-color)] mb-1">
                        {index + 1}. {step.title}
                      </h4>
                      <div className="text-sm text-[var(--hint-color)]">
                        {step.description}
                      </div>
                    </div>
                  </motion.div>
                ))}
              </div>

              {/* Important note */}
              <motion.div
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                transition={{ delay: 0.4 }}
                className="mt-6 p-4 rounded-xl bg-yellow-500/10 border border-yellow-500/20"
              >
                <h4 className="font-semibold text-yellow-400 text-sm mb-2">
                  Важно
                </h4>
                <ul className="text-xs text-[var(--hint-color)] space-y-1">
                  <li>• Экспортируйте только ключ от MIREA/РТУ</li>
                  <li>• Если в экспорте несколько ключей — бот сам найдёт MIREA</li>
                  <li>• Ваш ключ хранится в зашифрованном виде</li>
                </ul>
              </motion.div>

              {/* Supported apps */}
              <motion.div
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                transition={{ delay: 0.45 }}
                className="mt-4 p-4 rounded-xl bg-green-500/10 border border-green-500/20"
              >
                <h4 className="font-semibold text-green-400 text-sm mb-2">
                  Поддерживаемые приложения
                </h4>
                <p className="text-xs text-[var(--hint-color)]">
                  Google Authenticator, Aegis, Bitwarden, 1Password, FreeOTP и другие приложения с функцией экспорта QR-кода.
                </p>
              </motion.div>

              {/* Security note */}
              <motion.div
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                transition={{ delay: 0.5 }}
                className="mt-4 p-4 rounded-xl bg-blue-500/10 border border-blue-500/20"
              >
                <h4 className="font-semibold text-blue-400 text-sm mb-2">
                  Безопасность
                </h4>
                <p className="text-xs text-[var(--hint-color)]">
                  Вы можете удалить сохранённый ключ в любой момент, отправив команду <code className="bg-white/10 px-1 rounded">/delete_totp</code> боту.
                </p>
              </motion.div>

              {/* Action button */}
              <motion.button
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: 0.6 }}
                whileHover={{ scale: 1.02 }}
                whileTap={{ scale: 0.98 }}
                onClick={handleOpenBot}
                className="w-full mt-6 h-14 rounded-xl bg-gradient-to-r from-purple-500 to-blue-500 text-white font-semibold flex items-center justify-center gap-2 shadow-lg shadow-purple-500/30"
              >
                <Send size={20} />
                Перейти в бота
                <ExternalLink size={16} className="opacity-70" />
              </motion.button>

              {/* Close button */}
              <button
                onClick={onClose}
                className="w-full mt-3 h-12 rounded-xl border border-white/20 text-[var(--text-color)] font-medium"
              >
                Позже
              </button>
            </div>
          </motion.div>
        </motion.div>
      )}
    </AnimatePresence>
  );
};

export default TotpSetupGuide;
