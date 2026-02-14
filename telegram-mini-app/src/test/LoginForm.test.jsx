import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import LoginForm from '../components/LoginForm'

describe('LoginForm', () => {
  const mockOnSuccess = vi.fn()

  beforeEach(() => {
    mockOnSuccess.mockClear()
  })

  it('renders login form with login and password fields', () => {
    render(<LoginForm onSuccess={mockOnSuccess} />)

    expect(screen.getByPlaceholderText(/логин/i)).toBeInTheDocument()
    expect(screen.getByPlaceholderText(/пароль/i)).toBeInTheDocument()
  })

  it('renders submit button', () => {
    render(<LoginForm onSuccess={mockOnSuccess} />)

    const submitButton = screen.getByRole('button', { name: /войти/i })
    expect(submitButton).toBeInTheDocument()
  })

  it('renders authorization header', () => {
    render(<LoginForm onSuccess={mockOnSuccess} />)

    expect(screen.getByText(/авторизация/i)).toBeInTheDocument()
  })

  it('allows typing in login field', async () => {
    render(<LoginForm onSuccess={mockOnSuccess} />)

    const loginInput = screen.getByPlaceholderText(/логин/i)
    await userEvent.type(loginInput, 'test@mirea.ru')

    expect(loginInput).toHaveValue('test@mirea.ru')
  })

  it('allows typing in password field', async () => {
    render(<LoginForm onSuccess={mockOnSuccess} />)

    const passwordInput = screen.getByPlaceholderText(/пароль/i)
    await userEvent.type(passwordInput, 'password123')

    expect(passwordInput).toHaveValue('password123')
  })
})
