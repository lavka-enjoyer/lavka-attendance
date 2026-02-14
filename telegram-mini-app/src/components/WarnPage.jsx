import React from 'react';
import { AlertTriangle } from 'lucide-react';

const WarningPage = () => {
  return (
    <div 
      className="p-4 w-full max-w-md mx-auto min-h-screen flex flex-col justify-center items-center" 
      style={{backgroundColor: 'var(--bg-color)'}}
    >
      <div 
        className="bg-white rounded-xl shadow-md p-6 w-full flex flex-col items-center"
        style={{
          backgroundColor: 'var(--secondary-bg-color)', 
          border: '1px solid rgba(0, 0, 0, 0.1)'
        }}
      >
        <AlertTriangle size={64} className="mb-6" style={{color: 'var(--destructive-text-color)'}} />
        
        <h2 
          className="text-xl font-medium text-center mb-4"
          style={{color: 'var(--text-color)'}}
        >
          Приложение временно закрыто
        </h2>
        
        <p 
          className="text-center mb-8"
          style={{color: 'var(--hint-color)'}}
        >
          Проводятся технические работы
        </p>
        
        <a 
          href={import.meta.env.VITE_NEWS_CHANNEL_URL || '#'}
          target="_blank" 
          rel="noopener noreferrer"
          className="w-full rounded-xl shadow-md p-3 flex items-center justify-center"
          style={{
            backgroundColor: 'var(--button-color)',
            color: 'white',
            border: '1px solid rgba(0, 0, 0, 0.05)'
          }}
        >
          Подробнее
        </a>
      </div>
    </div>
  );
};

export default WarningPage;