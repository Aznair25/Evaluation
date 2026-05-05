import { apiClient } from '@/lib/api'

jest.mock('@/lib/auth', () => ({
  getToken: jest.fn().mockReturnValue('test-token'),
  clearToken: jest.fn(),
  saveToken: jest.fn(),
  isAuthenticated: jest.fn(),
}))

const mockFetch = jest.fn()
global.fetch = mockFetch

describe('apiClient', () => {
  beforeEach(() => {
    mockFetch.mockClear()
  })

  afterEach(() => {
    jest.clearAllMocks()
  })

  it('getMe calls correct endpoint with auth header', async () => {
    const user = { id: '1', email: 'a@b.com', name: 'A', picture_url: null, created_at: '', last_login: '' }
    mockFetch.mockResolvedValueOnce({ ok: true, json: async () => user })

    const result = await apiClient.getMe()

    expect(mockFetch).toHaveBeenCalledWith(
      expect.stringContaining('/api/auth/me'),
      expect.objectContaining({ headers: expect.objectContaining({ Authorization: 'Bearer test-token' }) }),
    )
    expect(result).toEqual(user)
  })

  it('listEvaluations returns array', async () => {
    const items = [{ evaluation_id: 'abc', status: 'completed', cefr_level: 'B1', student_name: 'Jane', created_at: '' }]
    mockFetch.mockResolvedValueOnce({ ok: true, json: async () => items })

    const result = await apiClient.listEvaluations()
    expect(result).toEqual(items)
  })

  it('throws on non-ok response', async () => {
    mockFetch.mockResolvedValueOnce({ ok: false, status: 401, text: async () => 'Unauthorized' })
    await expect(apiClient.getMe()).rejects.toThrow('HTTP 401')
  })

  it('uploadEvaluation sends FormData', async () => {
    mockFetch.mockResolvedValueOnce({
      ok: true,
      json: async () => ({ evaluation_id: 'xyz', status: 'processing', message: 'ok' }),
    })

    const file = new File(['audio'], 'test.mp3', { type: 'audio/mpeg' })
    const result = await apiClient.uploadEvaluation({
      audioFile: file,
      studentName: 'Jane',
      language: 'fr',
    })

    expect(mockFetch).toHaveBeenCalledWith(
      expect.stringContaining('/api/cefr-evaluator/evaluate'),
      expect.objectContaining({ method: 'POST' }),
    )
    expect(result.evaluation_id).toBe('xyz')
  })

  it('getReportUrl returns correct URL', () => {
    const url = apiClient.getReportUrl('eval-123')
    expect(url).toContain('/api/cefr-evaluator/evaluations/eval-123/report')
  })

  it('getEventsUrl returns correct URL', () => {
    const url = apiClient.getEventsUrl('eval-123')
    expect(url).toContain('/api/cefr-evaluator/evaluations/eval-123/events')
  })
})
