import React, { useState } from 'react';
import { Check, X, ChevronDown, ChevronUp, RefreshCw } from 'lucide-react';

const AttendanceComplete = ({
  marked,
  total,
  discipline,
  userResults = [],
  onRetryFailed,
  hasFailedStudents = false,
  onClose
}) => {
  const [showDetails, setShowDetails] = useState(false);

  // Сортируем результаты: сначала успешные, потом неуспешные
  const sortedResults = [...userResults].sort((a, b) => {
    if (a.success === b.success) return 0;
    return a.success ? -1 : 1;
  });

  const successfulResults = sortedResults.filter(r => r.success);
  const failedResults = sortedResults.filter(r => !r.success);

  return (
    <div className="p-4 w-full max-w-md mx-auto min-h-screen flex flex-col" style={{backgroundColor: 'var(--bg-color)'}}>
      <div
        className="rounded-xl shadow-sm p-6 flex flex-col items-center justify-center text-center relative"
        style={{backgroundColor: 'var(--secondary-bg-color)'}}
      >
        {/* Close button in top-right corner */}
        <button
          className="absolute top-4 right-4 w-8 h-8 flex items-center justify-center"
          onClick={onClose}
          style={{color: 'var(--text-color)'}}
        >
          <svg width="24" height="24" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
            <path d="M18 6L6 18" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" />
            <path d="M6 6L18 18" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" />
          </svg>
        </button>

        <div className="mb-4">
          <div className="w-16 h-16 flex items-center justify-center rounded-full" style={{backgroundColor: 'var(--button-color)'}}>
            <svg width="32" height="32" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
              <path d="M5 13L9 17L19 7" stroke="white" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" />
            </svg>
          </div>
        </div>
        <h2
          className="text-2xl mb-2"
          style={{color: 'var(--text-color)'}}
        >
          Отмечено {marked} / {total}
        </h2>
        {discipline ? (
          <p
            className="mb-4"
            style={{color: 'var(--text-color)'}}
          >
            {discipline}
          </p>
        ) : (
          <p
            className="mb-4 font-medium"
            style={{color: '#ef4444'}}
          >
            QR-код истёк или недействителен
          </p>
        )}

        {/* Toggle details button */}
        {userResults.length > 0 && (
          <button
            className="flex items-center justify-center gap-2 mb-4 py-2 px-4 rounded-full border-2 font-medium"
            style={{
              color: 'var(--button-color)',
              borderColor: 'var(--button-color)',
              backgroundColor: showDetails ? 'var(--button-color)' : 'transparent'
            }}
            onClick={() => setShowDetails(!showDetails)}
          >
            <span style={{ color: showDetails ? 'var(--button-text-color)' : 'var(--button-color)' }}>
              {showDetails ? 'Скрыть детали' : 'Показать детали'}
            </span>
            {showDetails
              ? <ChevronUp size={18} style={{ color: 'var(--button-text-color)' }} />
              : <ChevronDown size={18} style={{ color: 'var(--button-color)' }} />
            }
          </button>
        )}

        {/* User results list */}
        {showDetails && userResults.length > 0 && (
          <div className="w-full mb-4 max-h-60 overflow-y-auto rounded-lg" style={{backgroundColor: 'var(--bg-color)'}}>
            {/* Успешные */}
            {successfulResults.length > 0 && (
              <div className="p-2">
                <div className="text-xs font-semibold mb-2 text-left" style={{color: 'var(--hint-color)'}}>
                  Успешно ({successfulResults.length})
                </div>
                {successfulResults.map((result, index) => (
                  <div
                    key={result.tg_id || index}
                    className="flex items-center justify-between py-2 px-3 rounded-lg mb-1"
                    style={{backgroundColor: 'var(--secondary-bg-color)'}}
                  >
                    <span className="text-sm truncate mr-2" style={{color: 'var(--text-color)'}}>
                      {result.fio || `ID: ${result.tg_id}`}
                    </span>
                    <Check size={18} className="flex-shrink-0 text-green-500" />
                  </div>
                ))}
              </div>
            )}

            {/* Неуспешные */}
            {failedResults.length > 0 && (
              <div className="p-2">
                <div className="text-xs font-semibold mb-2 text-left" style={{color: 'var(--hint-color)'}}>
                  Не отмечены ({failedResults.length})
                </div>
                {failedResults.map((result, index) => (
                  <div
                    key={result.tg_id || index}
                    className="flex items-center justify-between py-2 px-3 rounded-lg mb-1"
                    style={{backgroundColor: 'var(--secondary-bg-color)'}}
                  >
                    <div className="flex flex-col items-start truncate mr-2">
                      <span className="text-sm" style={{color: 'var(--text-color)'}}>
                        {result.fio || `ID: ${result.tg_id}`}
                      </span>
                      {result.error && (
                        <span className="text-xs" style={{color: 'var(--hint-color)'}}>
                          {result.error}
                        </span>
                      )}
                    </div>
                    <X size={18} className="flex-shrink-0 text-red-500" />
                  </div>
                ))}
              </div>
            )}
          </div>
        )}

        {/* Кнопка повторной отметки - только если есть неуспешные */}
        {hasFailedStudents && (
          <button
            className="rounded-full shadow-sm p-3 px-6 flex items-center justify-center w-full"
            style={{backgroundColor: 'var(--button-color)', color: 'var(--button-text-color)'}}
            onClick={onRetryFailed}
          >
            <span className="flex items-center justify-center">
              <RefreshCw size={18} className="mr-2" />
              Повторить для неотмеченных ({failedResults.length})
            </span>
          </button>
        )}
      </div>

      {/* Кнопка внизу экрана */}
      <div className="mt-auto pt-4">
        <button
          className="rounded-full p-3 px-6 flex items-center justify-center border w-full"
          style={{
            backgroundColor: 'transparent',
            color: 'var(--text-color)',
            borderColor: 'var(--text-color)'
          }}
          onClick={onClose}
        >
          <span>Вернуться на главную</span>
        </button>
      </div>
    </div>
  );
};

export default AttendanceComplete;