import React from 'react';

const AttendanceError = ({ message, remaining, onContinue, onClose, buttonText = "Отсканировать QR заново" }) => {
  return (
    <div className="p-4 w-full max-w-md mx-auto" style={{backgroundColor: 'var(--bg-color)'}}>
      <div 
        className="rounded-xl shadow-sm p-8 flex flex-col items-center justify-center text-center relative"
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
        
        <div className="mb-6">
          <div className="w-16 h-16 flex items-center justify-center rounded-full" style={{backgroundColor: 'var(--destructive-text-color)'}}>
            <svg width="32" height="32" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
              <path d="M12 8V12" stroke="white" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" />
              <path d="M12 16H12.01" stroke="white" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" />
              <path d="M12 21C16.9706 21 21 16.9706 21 12C21 7.02944 16.9706 3 12 3C7.02944 3 3 7.02944 3 12C3 16.9706 7.02944 21 12 21Z" stroke="white" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" />
            </svg>
          </div>
        </div>
        <h2 
          className="text-xl mb-2"
          style={{color: 'var(--text-color)'}}
        >
          Не все были отмечены!
        </h2>
        <p 
          className="mb-4"
          style={{color: 'var(--text-color)'}}
        >
          {message || "Срок действия QR кода истек"}
        </p>
        
        {remaining > 0 && (
          <p 
            className="mb-6"
            style={{color: 'var(--hint-color)'}}
          >
            Осталось отметить: {remaining} чел.
          </p>
        )}
        
        <button
          className="rounded-full shadow-sm p-3 px-6 flex items-center justify-center w-full mb-3"
          style={{backgroundColor: 'var(--button-color)', color: 'var(--button-text-color)'}}
          onClick={onContinue}
        >
          <span className="flex items-center justify-center">
            {buttonText}
            <svg className="w-5 h-5 ml-2" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
              <rect x="5" y="5" width="14" height="14" stroke="currentColor" strokeWidth="2" fill="none" />
              <rect x="8" y="8" width="8" height="8" stroke="currentColor" strokeWidth="2" fill="none" />
            </svg>
          </span>
        </button>
        
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

export default AttendanceError;