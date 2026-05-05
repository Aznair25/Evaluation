export type EvaluationStatus =
  | 'pending'
  | 'transcribing'
  | 'analyzing'
  | 'generating_report'
  | 'completed'
  | 'failed'

export interface UserOut {
  id: string
  email: string
  name: string
  picture_url: string | null
  created_at: string
  last_login: string
}

export interface EvaluationListItem {
  evaluation_id: string
  status: EvaluationStatus
  cefr_level: string | null
  student_name: string | null
  created_at: string
}

export interface EvaluationStatusResponse {
  evaluation_id: string
  status: EvaluationStatus
  progress_percentage: number
  current_step: string | null
}

export interface SSEEvent {
  status: EvaluationStatus
  progress_percentage: number
  current_step: string | null
  cefr_level?: string
}

export interface CriterionResult {
  achieved: boolean | null
  evidence: string[]
  comment_fr: string | null
  comment_en: string | null
  azure_scores?: Record<string, number>
  error?: string
}

export interface EvaluationResult {
  evaluation_id: string
  status: EvaluationStatus
  cefr_level: string | null
  sub_level_rule: string | null
  communicative_profile_fr: string | null
  communicative_profile_en: string | null
  criteria: Record<string, CriterionResult> | null
  global_comment_fr: string | null
  global_comment_en: string | null
  report_url: string | null
  transcript: string | null
  audio_duration_seconds: number | null
  student_speaking_duration_seconds: number | null
  created_at: string
}

export interface EvaluationStarted {
  evaluation_id: string
  status: string
  message: string
}
