import React from 'react';

const MarkingLoader = ({ status, message, progress }) => {
  return (
    <div className="w-full max-w-md mx-auto p-6">
      <div 
        className="rounded-xl shadow-sm p-8 flex flex-col items-center justify-center"
        style={{backgroundColor: 'var(--secondary-bg-color)'}}
      >
        <div className="mb-6">
          <div className="animate-spin">
            {status === 'checking' && (
              <svg width="48" height="48" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
                <path d="M12 2C6.47715 2 2 6.47715 2 12C2 17.5228 6.47715 22 12 22C17.5228 22 22 17.5228 22 12C22 9.27455 20.9097 6.80375 19.1414 5" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"/>
              </svg>
            )}
          </div>
        </div>
        <div className="text-center">
          <h2 
            className="text-xl mb-2"
            style={{color: 'var(--text-color)'}}
          >
            {status === 'checking' ? 'Подготовка' : 'Обработка'}
          </h2>
          <p 
            className="text-sm mb-4"
            style={{color: 'var(--hint-color)'}}
          >
            {message || 'Проверяю данные авторизации'}
          </p>
          
          {/* Progress bar for loading students */}
          {typeof progress === 'number' && progress > 0 && (
            <div className="w-full mt-2">
              <div className="w-full h-6 overflow-hidden rounded-full bg-gray-200">
                <div 
                  className="h-full transition-all" 
                  style={{
                    width: `${Math.min(progress, 100)}%`,
                    backgroundColor: 'var(--button-color)'
                  }}
                />
              </div>
              <p className="text-xs mt-1" style={{color: 'var(--hint-color)'}}>
                {Math.round(progress)}%
              </p>
            </div>
          )}
        </div>
      </div>
    </div>
  );
};

export default MarkingLoader;