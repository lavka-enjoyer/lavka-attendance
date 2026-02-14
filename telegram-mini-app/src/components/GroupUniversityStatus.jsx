import React, { useState, useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { ArrowLeft, Building2, Users, Loader2, RefreshCw, Clock, AlertCircle, CheckCircle2, XCircle } from 'lucide-react';
import apiService from '../services/apiService';
import { Alert, AlertDescription } from './ui/alert';

const GroupUniversityStatus = ({ initData, onBack }) => {
  const [students, setStudents] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [refreshing, setRefreshing] = useState(false);

  useEffect(() => {
    loadGroupStatus();
  }, [initData]);

  const loadGroupStatus = async () => {
    setLoading(true);
    setError('');

    try {
      const result = await apiService.getGroupUniversityStatus(initData);

      if (result.error) {
        setError(result.error);
        setStudents([]);
      } else {
        setStudents(result.students || []);
      }
    } catch (err) {
      console.error('Ошибка при загрузке статусов группы:', err);
      setError(err.message || 'Не удалось загрузить статусы группы');
    } finally {
      setLoading(false);
    }
  };

  const handleRefresh = async () => {
    setRefreshing(true);
    await loadGroupStatus();
    setRefreshing(false);
  };

  // Подсчет статистики
  const stats = {
    total: students.length,
    inside: students.filter(s => s.is_inside_university && !s.not_activated && !s.needs_2fa).length,
    outside: students.filter(s => !s.is_inside_university && !s.not_activated && !s.needs_2fa).length,
    notActivated: students.filter(s => s.not_activated).length,
    needs2fa: students.filter(s => s.needs_2fa).length
  };

  return (
    <motion.div 
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        exit={{ opacity: 0 }}
        className="p-4 w-full max-w-md mx-auto min-h-screen flex flex-col bg-[var(--bg-color)]"
    >
      {/* Header */}
      <div className="flex items-center mb-6">
        <motion.button
          whileHover={{ scale: 1.1 }}
          whileTap={{ scale: 0.9 }}
          onClick={onBack}
          className="mr-3 p-2 rounded-full hover:bg-black/5 transition-colors text-[var(--text-color)]"
        >
          <ArrowLeft size={24} />
        </motion.button>
        <h1 className="text-2xl font-bold flex items-center text-[var(--text-color)]">
          <Building2 className="mr-2" size={28} />
          Кто в унике?
        </h1>
      </div>

      {/* Stats Card */}
      <motion.div 
        initial={{ y: -20, opacity: 0 }}
        animate={{ y: 0, opacity: 1 }}
        className="glass rounded-2xl p-5 mb-6 shadow-sm"
      >
        <div className="flex items-center justify-between mb-4">
            <h2 className="font-bold text-lg text-[var(--text-color)]">Статистика</h2>
            <motion.button
                whileHover={{ scale: 1.1, rotate: 180 }}
                whileTap={{ scale: 0.9 }}
                transition={{ duration: 0.3 }}
                onClick={handleRefresh}
                disabled={refreshing}
                className="p-2 rounded-full hover:bg-black/5 text-[var(--button-color)]"
            >
                <RefreshCw size={20} className={refreshing ? 'animate-spin' : ''} />
            </motion.button>
        </div>
        
        <div className="grid gap-3 grid-cols-3">
            <div className="flex flex-col items-center p-3 rounded-xl bg-[var(--tg-theme-bg-color)] border border-[var(--tg-theme-hint-color)]/20">
                <span className="text-2xl font-bold text-[var(--text-color)]">{stats.total}</span>
                <span className="text-xs text-[var(--hint-color)]">Всего</span>
            </div>
            <div className="flex flex-col items-center p-3 rounded-xl bg-gradient-to-br from-green-500/10 to-green-500/10 border border-green-500/20">
                <span className="text-2xl font-bold text-green-600">{stats.inside}</span>
                <span className="text-xs text-green-600/80">В вузе</span>
            </div>
            <div className="flex flex-col items-center p-3 rounded-xl bg-gray-500/10 border border-gray-500/20">
                <span className="text-2xl font-bold text-gray-600">{stats.outside}</span>
                <span className="text-xs text-gray-600/80">Нет</span>
            </div>
        </div>
        {(stats.notActivated > 0 || stats.needs2fa > 0) && (
            <div className="grid gap-3 grid-cols-2 mt-3">
                {stats.needs2fa > 0 && (
                    <div className="flex flex-col items-center p-3 rounded-xl bg-yellow-500/10 border border-yellow-500/20">
                        <span className="text-2xl font-bold text-yellow-600">{stats.needs2fa}</span>
                        <span className="text-xs text-yellow-600/80 text-center">2FA</span>
                    </div>
                )}
                {stats.notActivated > 0 && (
                    <div className="flex flex-col items-center p-3 rounded-xl bg-orange-500/10 border border-orange-500/20">
                        <span className="text-2xl font-bold text-orange-600">{stats.notActivated}</span>
                        <span className="text-xs text-orange-600/80 text-center">Не актив.</span>
                    </div>
                )}
            </div>
        )}
      </motion.div>

      {/* Loading */}
      {loading ? (
        <div className="space-y-3 pb-4">
          {[1, 2, 3, 4, 5].map((i) => (
            <div key={i} className="rounded-2xl p-4 glass shadow-sm flex items-center justify-between">
              <div className="h-5 w-32 bg-gray-200/20 rounded" />
              <div className="h-6 w-20 bg-gray-200/20 rounded-full" />
            </div>
          ))}
        </div>
      ) : error ? (
        <Alert className="shadow-lg mb-4 bg-red-500/10 border-red-500/20 text-red-500">
          <AlertDescription className="font-medium">
            {error}
          </AlertDescription>
        </Alert>
      ) : students.length === 0 ? (
        <motion.div 
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            className="text-center py-12"
        >
          <div className="w-20 h-20 mx-auto mb-4 rounded-full bg-black/5 flex items-center justify-center text-[var(--hint-color)]">
            <Users size={40} className="opacity-50" />
          </div>
          <p className="text-lg text-[var(--hint-color)]">
            Нет активированных студентов в группе
          </p>
        </motion.div>
      ) : (
        <div className="space-y-3 pb-4">
          {students.map((student, index) => {
            const isInside = student.is_inside_university;
            const hasError = student.error;
            const notActivated = student.not_activated;
            const needs2fa = student.needs_2fa;

            return (
              <motion.div
                key={student.tg_id || index}
                className={`rounded-2xl p-4 transition-all ${
                    notActivated
                    ? 'glass border-orange-500/30 bg-gradient-to-br from-orange-500/5 to-orange-500/5 shadow-sm opacity-70'
                    : needs2fa
                    ? 'glass border-yellow-500/30 bg-gradient-to-br from-yellow-500/5 to-yellow-500/5 shadow-sm opacity-80'
                    : isInside
                    ? 'glass border-green-500/30 bg-gradient-to-br from-green-500/5 to-green-500/5 shadow-sm'
                    : 'glass shadow-sm'
                }`}
              >
                {/* Student Name */}
                <div className="flex items-center justify-between mb-3">
                  <h3 className="font-bold text-base text-[var(--text-color)]">
                    {student.fio}
                  </h3>
                  {notActivated ? (
                      <div className="px-2.5 py-1 rounded-full bg-orange-500/10 text-orange-600 text-xs font-medium border border-orange-500/20">
                        Не активирован
                      </div>
                  ) : needs2fa ? (
                      <div className="px-2.5 py-1 rounded-full bg-yellow-500/10 text-yellow-600 text-xs font-medium border border-yellow-500/20">
                        Требуется 2FA
                      </div>
                  ) : isInside ? (
                      <div className="flex items-center gap-1.5 px-2.5 py-1 rounded-full bg-green-500/10 text-green-600 border border-green-500/20">
                        <div className="w-1.5 h-1.5 rounded-full bg-green-500 animate-pulse" />
                        <span className="text-xs font-bold">В вузе</span>
                      </div>
                  ) : (
                      <div className="px-2.5 py-1 rounded-full bg-gray-500/10 text-gray-500 text-xs font-medium border border-gray-500/10">
                        Не в вузе
                      </div>
                  )}
                </div>

                {/* Error Message */}
                {hasError && (
                  <div className="flex items-start gap-2 text-xs mb-3 p-2.5 rounded-xl bg-red-500/10 text-red-600 border border-red-500/10">
                    <AlertCircle size={14} className="mt-0.5 flex-shrink-0" />
                    <span>{student.error}</span>
                  </div>
                )}

                {/* Time Info */}
                {!hasError && !notActivated && !needs2fa && (
                  <div className="flex items-center gap-3 text-sm">
                    {isInside ? (
                        <div className="flex items-center gap-2 text-[var(--text-color)]">
                          <Clock size={16} className="text-green-500" />
                          <span>
                            В унике уже <span className="font-bold">{student.time_in_university}</span>
                          </span>
                        </div>
                      ) : (
                        <div className="flex items-center gap-2 text-[var(--hint-color)]">
                          <Clock size={16} />
                          <span>
                            {student.time_out_university === 'Не заходил сегодня' ? (
                              'Не заходил сегодня'
                            ) : (
                              <>
                                Не в унике уже <span className="font-bold text-[var(--text-color)]">{student.time_out_university}</span>
                              </>
                            )}
                          </span>
                        </div>
                      )}
                  </div>
                )}

                {/* Needs 2FA Message */}
                {needs2fa && (
                  <div className="flex items-center gap-2 text-sm text-yellow-600/80">
                    <AlertCircle size={16} />
                    <span>Нужно ввести код 2FA в Mini App</span>
                  </div>
                )}

                {/* Not Activated Message */}
                {notActivated && (
                  <div className="flex items-center gap-2 text-sm text-orange-600/80">
                    <AlertCircle size={16} />
                    <span>Студент не залогинен в боте</span>
                  </div>
                )}

                {/* Last Event Time */}
                {student.last_event_time && (
                  <div className="text-xs mt-2 pt-2 border-t border-black/5 text-[var(--hint-color)] flex justify-between">
                    <span>Последнее событие:</span>
                    <span className="font-medium">{student.last_event_time}</span>
                  </div>
                )}
              </motion.div>
            );
          })}
        </div>
      )}
    </motion.div>
  );
};

export default GroupUniversityStatus;
