import '@testing-library/jest-dom'
import { vi, beforeEach, afterEach, expect } from 'vitest'

// Console error tracking for tests
let consoleErrors = []
let consoleWarns = []
const originalConsoleError = console.error
const originalConsoleWarn = console.warn

beforeEach(() => {
  consoleErrors = []
  consoleWarns = []

  console.error = (...args) => {
    consoleErrors.push(args)
    // Still log to console for debugging
    originalConsoleError.apply(console, args)
  }

  console.warn = (...args) => {
    consoleWarns.push(args)
    originalConsoleWarn.apply(console, args)
  }
})

afterEach(() => {
  console.error = originalConsoleError
  console.warn = originalConsoleWarn
})

// Export for use in tests
export const getConsoleErrors = () => consoleErrors
export const getConsoleWarns = () => consoleWarns
export const expectNoConsoleErrors = () => {
  const criticalErrors = consoleErrors.filter(args => {
    const msg = args.join(' ')
    // Ignore React strict mode warnings and known non-critical warnings
    if (msg.includes('Warning: ReactDOM.render is no longer supported')) return false
    if (msg.includes('Warning: An update to') && msg.includes('was not wrapped in act')) return false
    return true
  })

  if (criticalErrors.length > 0) {
    throw new Error(`Console errors detected:\n${criticalErrors.map(e => e.join(' ')).join('\n')}`)
  }
}

// Mock Telegram WebApp
global.Telegram = {
  WebApp: {
    initData: 'test_init_data',
    initDataUnsafe: {
      user: {
        id: 123456789,
        first_name: 'Test',
        last_name: 'User',
        username: 'testuser',
      },
    },
    ready: vi.fn(),
    expand: vi.fn(),
    close: vi.fn(),
    enableClosingConfirmation: vi.fn(),
    disableClosingConfirmation: vi.fn(),
    showScanQrPopup: vi.fn(),
    closeScanQrPopup: vi.fn(),
    showConfirm: vi.fn((text, callback) => callback && callback(true)),
    showAlert: vi.fn((text, callback) => callback && callback()),
    showPopup: vi.fn((params, callback) => callback && callback()),
    onEvent: vi.fn(),
    offEvent: vi.fn(),
    sendData: vi.fn(),
    openLink: vi.fn(),
    openTelegramLink: vi.fn(),
    MainButton: {
      show: vi.fn(),
      hide: vi.fn(),
      setText: vi.fn(),
      onClick: vi.fn(),
      offClick: vi.fn(),
      enable: vi.fn(),
      disable: vi.fn(),
      isVisible: false,
      isActive: true,
      text: '',
    },
    BackButton: {
      show: vi.fn(),
      hide: vi.fn(),
      onClick: vi.fn(),
      offClick: vi.fn(),
      isVisible: false,
    },
    HapticFeedback: {
      impactOccurred: vi.fn(),
      notificationOccurred: vi.fn(),
      selectionChanged: vi.fn(),
    },
    themeParams: {
      bg_color: '#ffffff',
      text_color: '#000000',
      hint_color: '#999999',
      link_color: '#2481cc',
      button_color: '#2481cc',
      button_text_color: '#ffffff',
      secondary_bg_color: '#f0f0f0',
      header_bg_color: '#ffffff',
      accent_text_color: '#000000',
      section_bg_color: '#f0f0f0',
      section_header_text_color: '#000000',
      subtitle_text_color: '#999999',
      destructive_text_color: '#ff3b30',
    },
    colorScheme: 'light',
    viewportHeight: 600,
    viewportStableHeight: 600,
    isExpanded: true,
    platform: 'web',
    safeAreaInset: {
      top: 0,
      bottom: 0,
      left: 0,
      right: 0,
    },
  },
}

// Mock fetch
global.fetch = vi.fn()

// Mock localStorage
const localStorageMock = {
  getItem: vi.fn(),
  setItem: vi.fn(),
  removeItem: vi.fn(),
  clear: vi.fn(),
}
global.localStorage = localStorageMock

// Reset mocks before each test
beforeEach(() => {
  vi.clearAllMocks()
  global.fetch.mockReset()

  // Reset Telegram WebApp mocks
  Object.keys(global.Telegram.WebApp).forEach(key => {
    if (typeof global.Telegram.WebApp[key]?.mockReset === 'function') {
      global.Telegram.WebApp[key].mockReset()
    }
  })
})
