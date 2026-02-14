import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, waitFor } from '@testing-library/react'
import { getConsoleErrors } from './setup'

// Mock apiService
vi.mock('../services/apiService', () => ({
  default: {
    checkUserAuth: vi.fn(),
  },
  ERROR_TYPES: {
    AUTH_ERROR: 'AUTH_ERROR',
    NETWORK_ERROR: 'NETWORK_ERROR',
  },
  determineErrorType: vi.fn(() => 'UNKNOWN'),
}))

describe('App Component', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  describe('Rendering without critical errors', () => {
    it('renders loading state initially', async () => {
      const apiService = await import('../services/apiService')
      apiService.default.checkUserAuth.mockImplementation(() => new Promise(() => {}))

      const { default: App } = await import('../App')
      render(<App />)

      expect(screen.getByText(/загрузка/i)).toBeInTheDocument()

      // Check for critical errors (ignore React warnings about undefined types from mocks)
      const errors = getConsoleErrors()
      const criticalErrors = errors.filter(args => {
        const msg = args.join(' ')
        // Ignore mock-related warnings
        if (msg.includes('type is invalid')) return false
        if (msg.includes('whileHover')) return false
        if (msg.includes('whileTap')) return false
        // Real critical errors
        if (msg.includes('Uncaught')) return true
        if (msg.includes('TypeError')) return true
        if (msg.includes('ReferenceError')) return true
        return false
      })

      expect(criticalErrors).toHaveLength(0)
    })

    it('handles auth error gracefully', async () => {
      const apiService = await import('../services/apiService')
      apiService.default.checkUserAuth.mockRejectedValue(new Error('Введите Логин и Пароль'))

      const { default: App } = await import('../App')
      render(<App />)

      await waitFor(() => {
        expect(screen.queryByText(/загрузка/i)).not.toBeInTheDocument()
      }, { timeout: 3000 })

      // Should not throw unhandled errors
      const errors = getConsoleErrors()
      const unhandledErrors = errors.filter(args => {
        const msg = args.join(' ')
        return msg.includes('Uncaught') || msg.includes('Unhandled')
      })
      expect(unhandledErrors).toHaveLength(0)
    })
  })
})

describe('Console Error Detection', () => {
  it('detects when console.error is called', () => {
    console.error('Test error message')

    const errors = getConsoleErrors()
    expect(errors.length).toBeGreaterThan(0)
    expect(errors[0][0]).toBe('Test error message')
  })
})
