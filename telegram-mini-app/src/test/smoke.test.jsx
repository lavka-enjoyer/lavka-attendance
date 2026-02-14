import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen } from '@testing-library/react'
import { getConsoleErrors } from './setup'

// Helper to check for critical errors only
const expectNoCriticalErrors = () => {
  const errors = getConsoleErrors()
  const criticalErrors = errors.filter(args => {
    const msg = args.join(' ')
    // Ignore mock-related and React dev warnings
    if (msg.includes('type is invalid')) return false
    if (msg.includes('whileHover')) return false
    if (msg.includes('whileTap')) return false
    if (msg.includes('was not wrapped in act')) return false
    if (msg.includes('Warning:')) return false
    // Real critical errors
    if (msg.includes('Uncaught')) return true
    if (msg.includes('TypeError:')) return true
    if (msg.includes('ReferenceError:')) return true
    if (msg.includes('SyntaxError:')) return true
    return false
  })

  if (criticalErrors.length > 0) {
    throw new Error(`Critical errors detected:\n${criticalErrors.map(e => e.join(' ')).join('\n')}`)
  }
}

describe('Smoke Tests - Components render without critical errors', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  describe('LoginForm', () => {
    it('renders without critical errors', async () => {
      const { default: LoginForm } = await import('../components/LoginForm')

      render(<LoginForm initData="test" onLoginSuccess={vi.fn()} />)

      expect(screen.getByText(/авторизация/i)).toBeInTheDocument()
      expectNoCriticalErrors()
    })
  })

  describe('AttendanceError', () => {
    it('renders without critical errors', async () => {
      const { default: AttendanceError } = await import('../components/AttendanceError')

      render(<AttendanceError message="Test error" onContinue={vi.fn()} onClose={vi.fn()} />)

      expect(screen.getByText(/test error/i)).toBeInTheDocument()
      expectNoCriticalErrors()
    })
  })

  describe('WarnPage', () => {
    it('renders without critical errors', async () => {
      const { default: WarnPage } = await import('../components/WarnPage')

      render(<WarnPage message="Test warning" />)

      expectNoCriticalErrors()
    })
  })

  describe('MarkingLoader', () => {
    it('renders without critical errors', async () => {
      const { default: MarkingLoader } = await import('../components/MarkingLoader')

      render(<MarkingLoader />)

      expectNoCriticalErrors()
    })
  })

  describe('PixelCheckbox', () => {
    it('renders without critical errors', async () => {
      const { PixelCheckbox } = await import('../components/PixelCheckbox')

      render(<PixelCheckbox checked={false} onChange={vi.fn()} label="Test" />)

      expectNoCriticalErrors()
    })
  })
})

describe('UI Components Smoke Tests', () => {
  describe('Button', () => {
    it('renders without critical errors', async () => {
      const { Button } = await import('../components/ui/button')

      render(<Button>Click me</Button>)

      expect(screen.getByRole('button')).toBeInTheDocument()
      expectNoCriticalErrors()
    })

    it('renders all variants without critical errors', async () => {
      const { Button } = await import('../components/ui/button')

      const variants = ['default', 'destructive', 'outline', 'secondary', 'ghost', 'link']

      for (const variant of variants) {
        const { unmount } = render(<Button variant={variant}>Button</Button>)
        expectNoCriticalErrors()
        unmount()
      }
    })
  })

  describe('Input', () => {
    it('renders without critical errors', async () => {
      const { Input } = await import('../components/ui/input')

      render(<Input placeholder="Test input" />)

      expect(screen.getByPlaceholderText('Test input')).toBeInTheDocument()
      expectNoCriticalErrors()
    })
  })

  describe('Card', () => {
    it('renders without critical errors', async () => {
      const { Card, CardHeader, CardContent } = await import('../components/ui/card')

      render(
        <Card>
          <CardHeader>
            <h3>Test Card</h3>
          </CardHeader>
          <CardContent>Content</CardContent>
        </Card>
      )

      expect(screen.getByText('Test Card')).toBeInTheDocument()
      expectNoCriticalErrors()
    })
  })
})

describe('JavaScript Error Detection', () => {
  it('catches TypeError', () => {
    console.error('TypeError: Cannot read property x of undefined')

    expect(() => expectNoCriticalErrors()).toThrow(/Critical errors detected/)
  })

  it('catches ReferenceError', () => {
    console.error('ReferenceError: x is not defined')

    expect(() => expectNoCriticalErrors()).toThrow(/Critical errors detected/)
  })

  it('ignores React warnings', () => {
    console.error('Warning: React does not recognize the prop')

    expect(() => expectNoCriticalErrors()).not.toThrow()
  })
})
