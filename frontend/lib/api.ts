import { getToken } from './auth'
import type {
  UserOut,
  EvaluationListItem,
  EvaluationStatusResponse,
  EvaluationResult,
  EvaluationStarted,
} from './types'

// NEXT_PUBLIC_API_URL must be set to an https:// URL in production.
// The http://localhost:8000 fallback is for local development only.
const BASE_URL = process.env.NEXT_PUBLIC_API_URL ?? 'http://localhost:8000'

function authHeaders(): Record<string, string> {
  const token = getToken()
  if (!token) return {}
  return { Authorization: `Bearer ${token}` }
}

async function handleResponse<T>(res: Response): Promise<T> {
  if (!res.ok) {
    const body = await res.text()
    throw new Error(`HTTP ${res.status}: ${body}`)
  }
  return res.json() as Promise<T>
}

export interface UploadEvaluationParams {
  audioFile: File
  studentName?: string
  evaluatorName?: string
  institution?: string
  date?: string
  language?: string
}

export const apiClient = {
  async getMe(): Promise<UserOut> {
    const res = await fetch(`${BASE_URL}/api/auth/me`, {
      headers: authHeaders(),
    })
    return handleResponse<UserOut>(res)
  },

  async logout(): Promise<void> {
    await fetch(`${BASE_URL}/api/auth/logout`, {
      method: 'POST',
      headers: authHeaders(),
    })
  },

  async uploadEvaluation(params: UploadEvaluationParams): Promise<EvaluationStarted> {
    const form = new FormData()
    form.append('audio_file', params.audioFile)
    if (params.studentName) form.append('student_name', params.studentName)
    if (params.evaluatorName) form.append('evaluator_name', params.evaluatorName)
    if (params.institution) form.append('institution', params.institution)
    if (params.date) form.append('date', params.date)
    form.append('language', params.language ?? 'fr')

    const res = await fetch(`${BASE_URL}/api/cefr-evaluator/evaluate`, {
      method: 'POST',
      headers: authHeaders(),
      body: form,
    })
    return handleResponse<EvaluationStarted>(res)
  },

  async listEvaluations(): Promise<EvaluationListItem[]> {
    const res = await fetch(`${BASE_URL}/api/cefr-evaluator/evaluations`, {
      headers: authHeaders(),
    })
    return handleResponse<EvaluationListItem[]>(res)
  },

  async getEvaluationStatus(id: string): Promise<EvaluationStatusResponse> {
    const res = await fetch(`${BASE_URL}/api/cefr-evaluator/evaluations/${id}/status`, {
      headers: authHeaders(),
    })
    return handleResponse<EvaluationStatusResponse>(res)
  },

  async getEvaluation(id: string): Promise<EvaluationResult> {
    const res = await fetch(`${BASE_URL}/api/cefr-evaluator/evaluations/${id}`, {
      headers: authHeaders(),
    })
    return handleResponse<EvaluationResult>(res)
  },

  getReportUrl(id: string): string {
    return `${BASE_URL}/api/cefr-evaluator/evaluations/${id}/report`
  },

  getEventsUrl(id: string): string {
    return `${BASE_URL}/api/cefr-evaluator/evaluations/${id}/events`
  },
}
