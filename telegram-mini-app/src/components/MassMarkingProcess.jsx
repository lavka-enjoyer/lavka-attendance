import React, { useState, useEffect, useRef } from 'react';
import AttendanceComplete from './AttendanceComplete';
import AttendanceError from './AttendanceError';

const MassMarkingProcess = ({ markingData, onContinue, initData }) => {
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [sessionId, setSessionId] = useState(null);
  const [status, setStatus] = useState({
    processed: 0,
    total: markingData?.selectedStudents?.length || 0,
    successful: 0,
    failed: 0,
    remaining: [],
    user_results: [],  // [{tg_id, fio, success, error?}]
    discipline: '',
    group: '',
    status: 'initializing'
  });
  const [isTokenExpired, setIsTokenExpired] = useState(false);
  const [isCompleted, setIsCompleted] = useState(false);
  const pollingIntervalRef = useRef(null);

  // Start marking process on mount
  useEffect(() => {
    // Validate data
    if (!markingData || !markingData.selectedStudents || !markingData.url || !initData) {
      setError("Недостаточно данных для отметки");
      setLoading(false);
      return;
    }
    
    // Start marking process
    startMarkingProcess();
    
    return () => {
      if (pollingIntervalRef.current) {
        clearInterval(pollingIntervalRef.current);
      }
    };
  }, []);

  // Function to start marking process with given users and URL
  const startMarkingWithUsers = async (selectedUsers, qrUrl) => {
    try {
      // Reset state for new marking
      setLoading(true);
      setError(null);
      setIsCompleted(false);
      setIsTokenExpired(false);
      setStatus({
        processed: 0,
        total: selectedUsers.length,
        successful: 0,
        failed: 0,
        remaining: [],
        user_results: [],
        discipline: '',
        group: '',
        status: 'initializing'
      });

      const response = await fetch('/api/start_mass_marking', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          selectedUsers,
          url: qrUrl,
          initData
        })
      });

      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.detail || 'Ошибка при запуске процесса отметки');
      }

      const result = await response.json();

      setSessionId(result.session_id);
      startPolling(result.session_id);
    } catch (error) {
      setError(error.message || "Произошла ошибка при запуске процесса отметки");
      setLoading(false);
    }
  };

  // Function to start marking process (initial)
  const startMarkingProcess = async () => {
    try {
      const response = await fetch('/api/start_mass_marking', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          selectedUsers: markingData.selectedStudents,
          url: markingData.url,
          initData
        })
      });

      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.detail || 'Ошибка при запуске процесса отметки');
      }

      const result = await response.json();

      setSessionId(result.session_id);
      startPolling(result.session_id);
    } catch (error) {
      setError(error.message || "Произошла ошибка при запуске процесса отметки");
      setLoading(false);
    }
  };

  // Function to poll marking status
  const startPolling = (sid) => {
    // Poll status every 500ms
    pollingIntervalRef.current = setInterval(async () => {
      try {
        const response = await fetch(`/api/get_marking_status/${sid}?initData=${encodeURIComponent(initData)}`);
        
        if (!response.ok) {
          throw new Error('Не удалось получить статус отметки');
        }
        
        const statusData = await response.json();

        // Update state
        setStatus({
          processed: statusData.processed || 0,
          total: statusData.total || 0,
          successful: statusData.successful || 0,
          failed: statusData.failed || 0,
          remaining: statusData.remaining || [],
          user_results: statusData.user_results || [],
          discipline: statusData.discipline || '',
          group: statusData.group || '',
          status: statusData.status || 'processing'
        });
        
        // Check status
        if (statusData.status === 'completed') {
          setIsCompleted(true);
          setLoading(false);
          clearInterval(pollingIntervalRef.current);
        } else if (statusData.status === 'token_expired') {
          setIsTokenExpired(true);
          setLoading(false);
          clearInterval(pollingIntervalRef.current);
        } else if (statusData.status === 'error') {
          setError(statusData.error || "Ошибка при отметке");
          setLoading(false);
          clearInterval(pollingIntervalRef.current);
        }
      } catch (error) {
        setError(error.message || "Ошибка при получении статуса отметки");
        setLoading(false);
        clearInterval(pollingIntervalRef.current);
      }
    }, 500);
  };

  // Function to retry marking for failed students
  const handleRetryFailed = (failedStudentIds) => {
    if (!failedStudentIds || failedStudentIds.length === 0) {
      return;
    }

    if (window.Telegram?.WebApp) {
      window.Telegram.WebApp.showScanQrPopup(
        {
          text: 'Отсканируйте QR-код для повторной отметки'
        },
        async (text) => {
          // Close QR scanner
          window.Telegram.WebApp.closeScanQrPopup();

          if (!text) {
            setError("Ошибка сканирования QR-кода");
            return true;
          }

          // Start new marking session with failed students
          await startMarkingWithUsers(failedStudentIds, text);

          return true;
        }
      );
    } else {
      setError("Функция сканирования QR недоступна");
    }
  };

  // Function to rescan QR when current one expires
  const handleRescan = () => {
    if (window.Telegram?.WebApp) {
      window.Telegram.WebApp.showScanQrPopup(
        {
          text: 'Отсканируйте новый QR-код для продолжения отметки'
        },
        async (text) => {
          
          // Close QR scanner
          window.Telegram.WebApp.closeScanQrPopup();
          
          try {
            setLoading(true);
            setIsTokenExpired(false);
            setError(null);
            
            // Call API to continue marking with new QR
            const response = await fetch('/api/continue_marking', {
              method: 'POST',
              headers: {
                'Content-Type': 'application/json',
              },
              body: JSON.stringify({
                session_id: sessionId,
                url: text,
                initData
              })
            });

            if (!response.ok) {
              const errorData = await response.json();
              throw new Error(errorData.detail || 'Не удалось продолжить отметку');
            }
            
            // Restart status polling
            startPolling(sessionId);
          } catch (error) {
            setError(error.message || "Произошла ошибка при продолжении отметки");
            setLoading(false);
          }
          
          return true;
        }
      );
    } else {
      setError("Функция сканирования QR недоступна");
    }
  };

  // If there was an error
  if (error) {
    return (
      <AttendanceError
        message={error}
        onContinue={handleRescan}
        onClose={onContinue}
      />
    );
  }

  // If marking completed successfully
  if (isCompleted) {
    // Get failed student IDs for retry
    const failedStudentIds = status.user_results
      .filter(r => !r.success)
      .map(r => r.tg_id);

    return (
      <AttendanceComplete
        marked={status.successful}
        total={status.total}
        discipline={status.discipline}
        userResults={status.user_results}
        onRetryFailed={() => handleRetryFailed(failedStudentIds)}
        hasFailedStudents={failedStudentIds.length > 0}
        onClose={onContinue}
      />
    );
  }
  
  // If token expired
  if (isTokenExpired) {
    return (
      <AttendanceError
        message="Срок действия QR кода истек. Пожалуйста, отсканируйте снова."
        remaining={status.remaining ? status.remaining.length : 0}
        onContinue={handleRescan}
        onClose={onContinue}
        buttonText="Отсканировать QR заново"
      />
    );
  }

  // Marking process screen
  return (
    <div className="p-4 w-full max-w-md mx-auto min-h-screen flex flex-col justify-center" style={{backgroundColor: 'var(--bg-color)'}}>
      <div className="rounded-xl shadow-sm overflow-hidden relative" style={{backgroundColor: 'var(--secondary-bg-color)'}}>
        {/* Close button in top-right corner */}
        <button
          className="absolute top-4 right-4 w-8 h-8 flex items-center justify-center z-10"
          onClick={onContinue}
          style={{color: 'var(--text-color)'}}
        >
          <svg width="24" height="24" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
            <path d="M18 6L6 18" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" />
            <path d="M6 6L18 18" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" />
          </svg>
        </button>
        
        {/* Progress bar and information */}
        <div className="p-6 text-center">
          <div className="w-12 h-12 mb-6 mx-auto relative flex items-center justify-center">
            <svg
              className="animate-spin"
              width="48"
              height="48"
              viewBox="0 0 24 24"
              fill="none"
              xmlns="http://www.w3.org/2000/svg"
              style={{ color: 'var(--button-color)' }}
            >
              <circle
                cx="12"
                cy="12"
                r="10"
                stroke="currentColor"
                strokeWidth="2"
                strokeOpacity="0.2"
                fill="none"
              />
              <path
                d="M12 2C6.47715 2 2 6.47715 2 12"
                stroke="currentColor"
                strokeWidth="2.5"
                strokeLinecap="round"
              />
            </svg>
          </div>
          <h2 className="text-xl mb-2" style={{color: 'var(--text-color)'}}>
            Массовая отметка
          </h2>
          <p className="text-md mb-4" style={{color: 'var(--text-color)'}}>
            Обработано: {status.processed} из {status.total}
          </p>
          
          {status.discipline && (
            <p className="text-sm mb-2" style={{color: 'var(--hint-color)'}}>
              {status.discipline}
            </p>
          )}
        </div>
        
        {/* Progress bar */}
        <div className="px-6 pb-6">
          <div className="w-full h-6 overflow-hidden rounded-full" style={{backgroundColor: 'var(--bg-color)'}}>
            <div 
              className="h-full transition-all" 
              style={{
                width: `${status.total > 0 ? Math.round((status.processed / status.total) * 100) : 0}%`,
                backgroundColor: 'var(--button-color)'
              }}
            />
          </div>
          
          <div className="flex justify-between mt-2">
            <div style={{color: 'var(--text-color)'}}>
              <span className="text-xs">Успешно: {status.successful}</span>
            </div>
            <div style={{color: 'var(--text-color)'}}>
              <span className="text-xs">Ошибок: {status.failed}</span>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

export default MassMarkingProcess;