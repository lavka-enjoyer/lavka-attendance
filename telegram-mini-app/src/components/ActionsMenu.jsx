import React, { useState, useEffect, useRef } from 'react';
import { MoreVertical, ShieldCheck, TrendingUp, X } from 'lucide-react';
import { motion, AnimatePresence } from 'framer-motion';

const ActionsMenu = ({ isAdmin, onViewPoints, onShowAdminPanel }) => {
  const [isOpen, setIsOpen] = useState(false);
  const menuRef = useRef(null);

  // Закрытие меню при клике вне его
  useEffect(() => {
    const handleClickOutside = (event) => {
      if (menuRef.current && !menuRef.current.contains(event.target)) {
        setIsOpen(false);
      }
    };

    if (isOpen) {
      document.addEventListener('mousedown', handleClickOutside);
      document.addEventListener('touchstart', handleClickOutside);
    }

    return () => {
      document.removeEventListener('mousedown', handleClickOutside);
      document.removeEventListener('touchstart', handleClickOutside);
    };
  }, [isOpen]);

  const handleMenuClick = () => {
    // Haptic feedback для Telegram
    if (window.Telegram?.WebApp?.HapticFeedback) {
      window.Telegram.WebApp.HapticFeedback.impactOccurred('light');
    }
    setIsOpen(!isOpen);
  };

  const handleActionClick = (action) => {
    // Haptic feedback для Telegram
    if (window.Telegram?.WebApp?.HapticFeedback) {
      window.Telegram.WebApp.HapticFeedback.impactOccurred('medium');
    }
    setIsOpen(false);
    action();
  };

  // Если не админ - показываем кнопку сразу без меню
  if (!isAdmin) {
    return (
      <motion.button
        whileHover={{ scale: 1.05 }}
        whileTap={{ scale: 0.95 }}
        onClick={() => handleActionClick(onViewPoints)}
        className="glass flex items-center gap-2 px-3 py-2 rounded-xl shadow-sm hover:shadow-md transition-all text-[var(--text-color)]"
      >
        <TrendingUp size={18} className="text-blue-500" />
        <span className="text-sm font-medium">БРС</span>
      </motion.button>
    );
  }

  // Если админ - показываем меню с двумя пунктами
  return (
    <div className="relative" ref={menuRef}>
      {/* Кнопка меню */}
      <motion.button
        whileHover={{ scale: 1.05 }}
        whileTap={{ scale: 0.95 }}
        onClick={handleMenuClick}
        className="glass p-2 rounded-xl shadow-sm hover:shadow-md transition-all text-[var(--text-color)]"
      >
        <AnimatePresence mode="wait">
            <motion.div
                key={isOpen ? "close" : "open"}
                initial={{ rotate: -90, opacity: 0 }}
                animate={{ rotate: 0, opacity: 1 }}
                exit={{ rotate: 90, opacity: 0 }}
                transition={{ duration: 0.2 }}
            >
                {isOpen ? <X size={20} /> : <MoreVertical size={20} />}
            </motion.div>
        </AnimatePresence>
      </motion.button>

      {/* Выпадающее меню */}
      <AnimatePresence>
        {isOpen && (
          <motion.div
            initial={{ opacity: 0, y: -10, scale: 0.95 }}
            animate={{ opacity: 1, y: 0, scale: 1 }}
            exit={{ opacity: 0, y: -10, scale: 0.95 }}
            transition={{ duration: 0.2 }}
            className="absolute right-0 mt-2 w-56 glass rounded-xl shadow-lg z-50 overflow-hidden border border-white/20"
          >
            {/* Мои баллы БРС */}
            <button
              onClick={() => handleActionClick(onViewPoints)}
              className="w-full flex items-center p-3 hover:bg-black/5 transition-colors text-[var(--text-color)] border-b border-gray-100/10"
            >
              <TrendingUp size={18} className="mr-3 text-blue-500" />
              <span className="text-sm font-medium">Мои баллы (БРС)</span>
            </button>

            {/* Админ панель */}
            <button
              onClick={() => handleActionClick(onShowAdminPanel)}
              className="w-full flex items-center p-3 hover:bg-black/5 transition-colors text-[var(--text-color)]"
            >
              <ShieldCheck size={18} className="mr-3 text-purple-500" />
              <span className="text-sm font-medium">Админ панель</span>
            </button>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
};

export default ActionsMenu;
