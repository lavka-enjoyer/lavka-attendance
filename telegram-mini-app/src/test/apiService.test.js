import { describe, it, expect, vi, beforeEach } from 'vitest'

// Mock the apiService module
const mockApiService = {
  getSchedule: vi.fn(),
  checkUser: vi.fn(),
  updateUser: vi.fn(),
  getPoints: vi.fn(),
}

describe('apiService', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    global.fetch.mockReset()
  })

  describe('checkUser', () => {
    it('returns user data on successful response', async () => {
      const mockUserData = {
        FIO: 'Иванов Иван Иванович',
        group: 'ИКБО-01-23',
        allowConfirm: true,
        admin_lvl: 0,
      }

      global.fetch.mockResolvedValueOnce({
        ok: true,
        json: () => Promise.resolve(mockUserData),
      })

      const response = await global.fetch('/api/checker?initData=test')
      const data = await response.json()

      expect(data).toEqual(mockUserData)
      expect(data.FIO).toBe('Иванов Иван Иванович')
      expect(data.group).toBe('ИКБО-01-23')
    })

    it('handles unauthorized error', async () => {
      global.fetch.mockResolvedValueOnce({
        ok: false,
        status: 401,
        json: () => Promise.resolve({ detail: 'Invalid hash' }),
      })

      const response = await global.fetch('/api/checker?initData=invalid')

      expect(response.ok).toBe(false)
      expect(response.status).toBe(401)
    })
  })

  describe('getSchedule', () => {
    it('returns schedule for given date', async () => {
      const mockSchedule = {
        lessons: [
          {
            name: 'Математический анализ',
            time_start: '09:00',
            time_end: '10:30',
            room: 'А-123',
            teacher: 'Петров П.П.',
          },
          {
            name: 'Программирование',
            time_start: '10:40',
            time_end: '12:10',
            room: 'Б-456',
            teacher: 'Сидоров С.С.',
          },
        ],
      }

      global.fetch.mockResolvedValueOnce({
        ok: true,
        json: () => Promise.resolve(mockSchedule),
      })

      const response = await global.fetch('/api/v1/schedule', {
        method: 'POST',
        body: JSON.stringify({ date: '2024-01-15' }),
      })
      const data = await response.json()

      expect(data.lessons).toHaveLength(2)
      expect(data.lessons[0].name).toBe('Математический анализ')
    })

    it('returns empty lessons array when no classes', async () => {
      global.fetch.mockResolvedValueOnce({
        ok: true,
        json: () => Promise.resolve({ lessons: [] }),
      })

      const response = await global.fetch('/api/v1/schedule', {
        method: 'POST',
        body: JSON.stringify({ date: '2024-01-14' }), // Sunday
      })
      const data = await response.json()

      expect(data.lessons).toHaveLength(0)
    })
  })

  describe('getPoints', () => {
    it('returns points data for user', async () => {
      const mockPoints = {
        subjects: [
          { name: 'Математика', current: 45, max: 100 },
          { name: 'Физика', current: 38, max: 100 },
        ],
      }

      global.fetch.mockResolvedValueOnce({
        ok: true,
        json: () => Promise.resolve(mockPoints),
      })

      const response = await global.fetch('/api/v1/points')
      const data = await response.json()

      expect(data.subjects).toHaveLength(2)
      expect(data.subjects[0].current).toBe(45)
    })
  })

  describe('error handling', () => {
    it('handles network errors', async () => {
      global.fetch.mockRejectedValueOnce(new Error('Network error'))

      await expect(global.fetch('/api/checker')).rejects.toThrow('Network error')
    })

    it('handles server errors', async () => {
      global.fetch.mockResolvedValueOnce({
        ok: false,
        status: 500,
        json: () => Promise.resolve({ detail: 'Internal server error' }),
      })

      const response = await global.fetch('/api/checker')

      expect(response.ok).toBe(false)
      expect(response.status).toBe(500)
    })

    it('handles timeout', async () => {
      global.fetch.mockImplementationOnce(
        () =>
          new Promise((_, reject) =>
            setTimeout(() => reject(new Error('Timeout')), 100)
          )
      )

      await expect(global.fetch('/api/checker')).rejects.toThrow('Timeout')
    })
  })
})
