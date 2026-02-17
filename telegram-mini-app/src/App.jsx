import React, { useEffect, useState } from 'react';
import { AlertTriangle } from 'lucide-react';
import { AnimatePresence } from 'framer-motion';
import './styles/telegram-theme.css';
import PageTransition from './components/PageTransition';
import MainScreen from './components/MainScreen';
import LoginForm from './components/LoginForm';
import EmailCodeForm from './components/EmailCodeForm';
import MarkMultipleScreen from './components/MarkMultipleScreen';
import MassMarkingProcess from './components/MassMarkingProcess';
import PointsScreen from './components/PointsScreen';
import AdminPanel from './components/AdminPanel';
import ScheduleScreen from './components/ScheduleScreen';
import GroupUniversityStatus from './components/GroupUniversityStatus';
import { Toaster } from './components/ui/toaster';
import apiService, { ERROR_TYPES, determineErrorType } from './services/apiService';
import { telegramUtils } from './utils';
import { isDemoMode, DEMO_USER } from './demo/mockData';

const App = () => {
  const [userData, setUserData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [screen, setScreen] = useState('main'); // 'main', 'login', 'emailCode', 'markMultiple', 'marking', 'unauthorized', 'points', 'admin', 'schedule', 'groupStatus'
  const [initData, setInitData] = useState('');
  const [markingData, setMarkingData] = useState(null);

  // Добавляем обработчик глобальных ошибок для предотвращения белого экрана
  useEffect(() => {
    const handleError = (event) => {
      setError("Произошла критическая ошибка. Попробуйте обновить страницу.");
      setLoading(false);

      // Логируем ошибку для диагностики
      console.error("Global error caught:", event.reason || event.error || event.message || event);
    };

    // Перехватываем все ошибки JavaScript
    window.addEventListener('error', handleError);
    window.addEventListener('unhandledrejection', handleError);

    return () => {
      window.removeEventListener('error', handleError);
      window.removeEventListener('unhandledrejection', handleError);
    };
  }, []);

  useEffect(() => {
    try {
      // Инициализируем Telegram WebApp
      telegramUtils.initTelegramWebApp();

      // Проверяем демо-режим
      if (isDemoMode()) {
        console.log('🎭 Demo mode активен');
        setUserData({
          FIO: DEMO_USER.fio,
          group: DEMO_USER.group,
          allowConfirm: DEMO_USER.allowConfirm,
          admin_lvl: DEMO_USER.admin_lvl,
        });
        setInitData('demo_mode');
        setScreen('main');
        setLoading(false);
        return;
      }

      // Получаем данные инициализации
      const webAppInitData = telegramUtils.getInitData();
      setInitData(webAppInitData);

      // Проверяем авторизацию пользователя
      if (webAppInitData) {
        checkUserAuth(webAppInitData);
      }
    } catch (e) {
      setError("Ошибка инициализации приложения: " + (e.message || "неизвестная ошибка"));
      setLoading(false);
    }
  }, []);

  // Function to check user authentication
  const checkUserAuth = async (webappInitData) => {
    try {
      setLoading(true);

      // Используем переработанный метод checkUserAuth
      const data = await apiService.checkUserAuth(webappInitData);

      // User exists and authenticated
      setUserData(data);
      setScreen('main');

    } catch (error) {
      // Преобразуем объект ошибки в строку для более надежной проверки
      const errorStr = String(error);

      // Проверяем требование email кода
      if (errorStr.includes("Требуется ввод кода из email") ||
          errorStr.includes("email code required")) {
        setScreen('emailCode');
      }
      // Проверяем все возможные варианты текста ошибки авторизации
      else if (errorStr.includes("Введите Логин и Пароль") ||
          errorStr.includes("login required") ||
          errorStr.includes("password required")) {
        setScreen('login');
      }
      // Проверяем все возможные варианты текста ошибки доступа
      else if (errorStr.includes("Доступ запрещен") ||
          errorStr.includes("Пользователь не существует") ||
          errorStr.includes("access denied") ||
          errorStr.includes("user not found") ||
          errorStr.includes("unauthorized")) {
        setScreen('unauthorized');
      }
      // Прочие ошибки
      else {
        setError(errorStr || "Ошибка проверки пользователя");
      }
    } finally {
      setLoading(false);
    }
  };

  // Function to handle successful login
  const handleLoginSuccess = (userData) => {
    setUserData(userData);
    setScreen('main');
  };

  // Function to handle successful email code - refetch user data
  const handleEmailCodeSuccess = async () => {
    setLoading(true);
    try {
      const data = await apiService.checkUserAuth(initData);
      setUserData(data);
      setScreen('main');
    } catch (error) {
      const errorStr = String(error);
      if (errorStr.includes("Требуется ввод кода из email") || errorStr.includes("email code required")) {
        setScreen('emailCode');
      } else {
        setError(errorStr || "Ошибка загрузки данных после подтверждения email");
      }
    } finally {
      setLoading(false);
    }
  };

  // Function to update user data (e.g. after toggling allowConfirm)
  const handleUpdateUserData = (newUserData) => {
    setUserData(newUserData);
  };

  // Function to handle mark multiple screen
  const handleMarkMultiple = () => {
    setScreen('markMultiple');
  };

  // Function to handle mark submission
  const handleMarkSubmit = (data) => {
    setMarkingData(data);
    setScreen('marking');
  };

  // Function to handle viewing BRS points
  const handleViewPoints = () => {
    setScreen('points');
  };

  // Function to handle admin panel
  const handleShowAdminPanel = () => {
    setScreen('admin');
  };

  // Function to handle schedule screen
  const handleViewSchedule = () => {
    setScreen('schedule');
  };

  // Function to handle group university status screen
  const handleViewGroupStatus = () => {
    setScreen('groupStatus');
  };

  // Function to return to main screen
  const handleBackToMain = () => {
    setScreen('main');
  };


  // Show loading indicator
  if (loading) {
    return (
        <div
            className="p-4 w-full max-w-md mx-auto min-h-screen flex flex-col justify-center items-center"
            style={{backgroundColor: 'var(--bg-color)'}}
        >
          <div className="animate-spin mb-4">
            <svg width="48" height="48" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
              <path d="M12 2C6.47715 2 2 6.47715 2 12C2 17.5228 6.47715 22 12 22C17.5228 22 22 17.5228 22 12C22 9.27455 20.9097 6.80375 19.1414 5" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"/>
            </svg>
          </div>
          <p style={{color: 'var(--text-color)'}}>Загрузка...</p>
        </div>
    );
  }

  // Show error message
  if (error && screen !== 'unauthorized' && screen !== 'login') {
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
              Ошибка
            </h2>

            <p
                className="text-center mb-8"
                style={{color: 'var(--hint-color)'}}
            >
              {error}
            </p>

            <button
                className="w-full rounded-xl shadow-md p-3 flex items-center justify-center"
                style={{
                  backgroundColor: 'var(--button-color)',
                  color: 'white',
                  border: '1px solid rgba(0, 0, 0, 0.05)'
                }}
                onClick={() => window.location.reload()}
            >
              Попробовать снова
            </button>
          </div>
        </div>
    );
  }

  // Render different screens based on the current state
  const renderScreen = () => {
    try {
      switch (screen) {
        case 'login':
          return (
            <PageTransition key="login">
              <LoginForm initData={initData} onLoginSuccess={handleLoginSuccess} />
            </PageTransition>
          );

        case 'emailCode':
          return (
            <PageTransition key="emailCode">
              <EmailCodeForm
                initData={initData}
                onSuccess={handleEmailCodeSuccess}
                onBack={handleBackToMain}
              />
            </PageTransition>
          );

        case 'unauthorized':
          return (
            <PageTransition key="unauthorized">
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
                    Доступ запрещен
                  </h2>

                  <p
                      className="text-center mb-8"
                      style={{color: 'var(--hint-color)'}}
                  >
                    Для использования приложения необходим доступ.
                    Пожалуйста, напишите @{import.meta.env.VITE_SUPPORT_USERNAME || 'support'} для получения доступа.
                  </p>

                  <a
                      href={`https://t.me/${import.meta.env.VITE_SUPPORT_USERNAME || 'support'}`}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="w-full rounded-xl shadow-md p-3 flex items-center justify-center"
                      style={{
                        backgroundColor: 'var(--button-color)',
                        color: 'white',
                        border: '1px solid rgba(0, 0, 0, 0.05)'
                      }}
                  >
                    Написать в поддержку
                  </a>
                </div>
              </div>
            </PageTransition>
          );

        case 'markMultiple':
          return (
            <PageTransition key="markMultiple">
              <MarkMultipleScreen
                  onBack={handleBackToMain}
                  onSubmit={handleMarkSubmit}
                  initData={initData}
              />
            </PageTransition>
          );

        case 'marking':
          return (
            <PageTransition key="marking">
              <MassMarkingProcess
                  markingData={markingData}
                  onContinue={handleBackToMain}
                  initData={initData}
              />
            </PageTransition>
          );

        case 'points':
          return (
            <PageTransition key="points">
              <PointsScreen
                  initData={initData}
                  onBack={handleBackToMain}
              />
            </PageTransition>
          );

        case 'admin':
          return (
            <PageTransition key="admin">
              <AdminPanel
                  initData={initData}
                  onBack={handleBackToMain}
                  adminLevel={userData?.admin_lvl || 1}
              />
            </PageTransition>
          );

        case 'schedule':
          return (
            <PageTransition key="schedule">
              <ScheduleScreen
                  initData={initData}
                  onBack={handleBackToMain}
              />
            </PageTransition>
          );

        case 'groupStatus':
          return (
            <PageTransition key="groupStatus">
              <GroupUniversityStatus
                  initData={initData}
                  onBack={handleBackToMain}
              />
            </PageTransition>
          );

        case 'main':
        default:
          return (
            <MainScreen
                key="main"
                initData={initData}
                userData={userData || { FIO: "Нет данных", group: "Нет данных" }}
                onMarkMultiple={handleMarkMultiple}
                onUpdateUserData={handleUpdateUserData}
                onViewPoints={handleViewPoints}
                onShowAdminPanel={handleShowAdminPanel}
                onViewSchedule={handleViewSchedule}
                onViewGroupStatus={handleViewGroupStatus}
            />
          );
      }
    } catch (renderError) {
      // Перехватываем ошибки рендеринга
      return (
          <div className="p-4 text-center">
            <h2>Ошибка отображения</h2>
            <p>{renderError.message || "Неизвестная ошибка"}</p>
            <button
                className="mt-4 px-4 py-2 bg-blue-500 text-white rounded"
                onClick={() => window.location.reload()}
            >
              Перезагрузить приложение
            </button>
          </div>
      );
    }
  };

  return (
    <>
      <AnimatePresence mode="sync">
        {renderScreen()}
      </AnimatePresence>
      <Toaster />
    </>
  );
};

export default App;