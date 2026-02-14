import React from 'react';
import { createPortal } from 'react-dom';
import { motion, AnimatePresence } from 'framer-motion';
import { X, Users, CheckCircle, XCircle, AlertCircle } from 'lucide-react';

const AttendanceModal = ({ isOpen, onClose, attendanceData, loading, error }) => {
  // Группируем студентов по статусам
  const groupedStudents = {
    present: [],
    absent: [],
    excused: []
  };

  if (attendanceData && attendanceData.students) {
    attendanceData.students.forEach(student => {
      if (student.status === '+') {
        groupedStudents.present.push(student);
      } else if (student.status === 'Н') {
        groupedStudents.absent.push(student);
      } else if (student.status === 'У') {
        groupedStudents.excused.push(student);
      }
    });
  }

  const modalContent = (
    <AnimatePresence>
      {isOpen && (
        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          exit={{ opacity: 0 }}
          className="fixed inset-0 z-[9999] flex items-center justify-center p-4 bg-black/60 backdrop-blur-sm"
          onClick={onClose}
        >
          <motion.div
            initial={{ scale: 0.9, opacity: 0, y: 20 }}
            animate={{ scale: 1, opacity: 1, y: 0 }}
            exit={{ scale: 0.9, opacity: 0, y: 20 }}
            transition={{ type: "spring", stiffness: 300, damping: 30 }}
            className="w-full max-w-2xl max-h-[90vh] rounded-3xl shadow-2xl flex flex-col glass border border-white/10 overflow-hidden"
            onClick={(e) => e.stopPropagation()}
          >
            {/* Header */}
            <div className="flex items-center justify-between p-6 border-b border-white/10">
              <div className="flex items-center">
                <div className="p-2 rounded-xl bg-[var(--button-color)]/10 mr-3">
                    <Users size={24} className="text-[var(--button-color)]" />
                </div>
                <h2 className="text-xl font-bold text-[var(--text-color)]">
                  Кто был на паре?
                </h2>
              </div>
              <motion.button
                whileHover={{ scale: 1.1 }}
                whileTap={{ scale: 0.9 }}
                onClick={onClose}
                className="p-2 rounded-full hover:bg-white/10 transition-colors text-[var(--text-color)]"
              >
                <X size={24} />
              </motion.button>
            </div>

            {/* Content */}
            <div className="flex-1 overflow-y-auto p-6">
              {loading ? (
                <div className="flex items-center justify-center py-12">
                  <motion.div 
                    animate={{ rotate: 360 }}
                    transition={{ duration: 1, repeat: Infinity, ease: "linear" }}
                    className="w-10 h-10 border-4 border-[var(--button-color)] border-t-transparent rounded-full"
                  />
                </div>
              ) : error ? (
                <div className="text-center py-12">
                  <div className="w-20 h-20 mx-auto mb-4 rounded-full bg-red-500/10 flex items-center justify-center">
                    <AlertCircle size={40} className="text-red-500" />
                  </div>
                  <p className="text-lg font-medium text-[var(--text-color)]">
                    {error}
                  </p>
                </div>
              ) : !attendanceData ? (
                <div className="text-center py-12">
                  <div className="w-20 h-20 mx-auto mb-4 rounded-full bg-white/5 flex items-center justify-center">
                    <Users size={40} className="text-[var(--hint-color)] opacity-50" />
                  </div>
                  <p className="text-lg text-[var(--hint-color)]">
                    Нет данных о посещаемости
                  </p>
                </div>
              ) : (
                <div className="space-y-6">
                  {/* Статистика */}
                  <div className="grid grid-cols-3 gap-4">
                    <div className="p-4 rounded-2xl bg-green-500/10 border border-green-500/20 text-center">
                      <div className="text-3xl font-bold text-green-500 mb-1">
                        {groupedStudents.present.length}
                      </div>
                      <div className="text-xs font-bold text-green-500/80">
                        Были
                      </div>
                    </div>
                    <div className="p-4 rounded-2xl bg-red-500/10 border border-red-500/20 text-center">
                      <div className="text-3xl font-bold text-red-500 mb-1">
                        {groupedStudents.absent.length}
                      </div>
                      <div className="text-xs font-bold text-red-500/80">
                        Не были
                      </div>
                    </div>
                    <div className="p-4 rounded-2xl bg-yellow-500/10 border border-yellow-500/20 text-center">
                      <div className="text-3xl font-bold text-yellow-500 mb-1">
                        {groupedStudents.excused.length}
                      </div>
                      <div className="text-xs font-bold text-yellow-500/80">
                        Уважит.
                      </div>
                    </div>
                  </div>

                  {/* Присутствовали */}
                  {groupedStudents.present.length > 0 && (
                    <motion.div
                        initial={{ opacity: 0, y: 10 }}
                        animate={{ opacity: 1, y: 0 }}
                        transition={{ delay: 0.1 }}
                    >
                      <h3 className="flex items-center text-lg font-bold mb-3 text-green-500">
                        <CheckCircle size={20} className="mr-2" />
                        Присутствовали ({groupedStudents.present.length})
                      </h3>
                      <div className="grid grid-cols-1 sm:grid-cols-2 gap-2">
                        {groupedStudents.present.map((student, index) => (
                          <div
                            key={index}
                            className="p-3 rounded-xl bg-green-500/5 border border-green-500/10 flex items-center"
                          >
                            <div className="w-2 h-2 rounded-full bg-green-500 mr-3" />
                            <span className="text-[var(--text-color)] font-medium">
                              {student.fio}
                            </span>
                          </div>
                        ))}
                      </div>
                    </motion.div>
                  )}

                  {/* Отсутствовали */}
                  {groupedStudents.absent.length > 0 && (
                    <motion.div
                        initial={{ opacity: 0, y: 10 }}
                        animate={{ opacity: 1, y: 0 }}
                        transition={{ delay: 0.2 }}
                    >
                      <h3 className="flex items-center text-lg font-bold mb-3 text-red-500">
                        <XCircle size={20} className="mr-2" />
                        Отсутствовали ({groupedStudents.absent.length})
                      </h3>
                      <div className="grid grid-cols-1 sm:grid-cols-2 gap-2">
                        {groupedStudents.absent.map((student, index) => (
                          <div
                            key={index}
                            className="p-3 rounded-xl bg-red-500/5 border border-red-500/10 flex items-center"
                          >
                            <div className="w-2 h-2 rounded-full bg-red-500 mr-3" />
                            <span className="text-[var(--text-color)] font-medium">
                              {student.fio}
                            </span>
                          </div>
                        ))}
                      </div>
                    </motion.div>
                  )}

                  {/* Уважительная причина */}
                  {groupedStudents.excused.length > 0 && (
                    <motion.div
                        initial={{ opacity: 0, y: 10 }}
                        animate={{ opacity: 1, y: 0 }}
                        transition={{ delay: 0.3 }}
                    >
                      <h3 className="flex items-center text-lg font-bold mb-3 text-yellow-500">
                        <AlertCircle size={20} className="mr-2" />
                        Уважительная причина ({groupedStudents.excused.length})
                      </h3>
                      <div className="grid grid-cols-1 sm:grid-cols-2 gap-2">
                        {groupedStudents.excused.map((student, index) => (
                          <div
                            key={index}
                            className="p-3 rounded-xl bg-yellow-500/5 border border-yellow-500/10 flex items-center"
                          >
                            <div className="w-2 h-2 rounded-full bg-yellow-500 mr-3" />
                            <span className="text-[var(--text-color)] font-medium">
                              {student.fio}
                            </span>
                          </div>
                        ))}
                      </div>
                    </motion.div>
                  )}
                </div>
              )}
            </div>

            {/* Footer */}
            <div className="p-6 border-t border-white/10 bg-white/5">
              <motion.button
                whileHover={{ scale: 1.02 }}
                whileTap={{ scale: 0.98 }}
                onClick={onClose}
                className="w-full py-3.5 px-4 rounded-xl font-bold transition-colors bg-[var(--button-color)] text-white shadow-lg shadow-blue-500/20"
              >
                Закрыть
              </motion.button>
            </div>
          </motion.div>
        </motion.div>
      )}
    </AnimatePresence>
  );

  return createPortal(modalContent, document.body);
};

export default AttendanceModal;
