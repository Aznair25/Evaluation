import { render, screen, fireEvent } from '@testing-library/react'
import { ResultCard } from '@/components/ResultCard'
import type { EvaluationResult } from '@/lib/types'

jest.mock('@/lib/api', () => ({
  apiClient: {
    getReportUrl: (id: string) => `http://localhost:8000/api/cefr-evaluator/evaluations/${id}/report`,
  },
}))

jest.mock('@/components/CriteriaTable', () => ({
  CriteriaTable: () => <table><tbody><tr><td>mocked criteria</td></tr></tbody></table>,
}))

const completedResult: EvaluationResult = {
  evaluation_id: 'eval-001',
  status: 'completed',
  cefr_level: 'B2.1',
  sub_level_rule: '.1',
  communicative_profile_fr: 'Communicateur avancé',
  communicative_profile_en: 'Advanced Communicator',
  criteria: {
    interaction: { achieved: true, evidence: [], comment_fr: 'Bon.', comment_en: 'Good.' },
  },
  global_comment_fr: 'Très bon travail.',
  global_comment_en: 'Very good work.',
  report_url: 'https://s3.example.com/report.pdf',
  transcript: null,
  audio_duration_seconds: 1200,
  student_speaking_duration_seconds: 600,
  created_at: '2024-01-15T10:00:00Z',
}

const failedResult: EvaluationResult = {
  ...completedResult,
  status: 'failed',
  cefr_level: null,
  global_comment_fr: 'Processing error occurred.',
}

describe('ResultCard', () => {
  it('shows CEFR level for completed evaluation', () => {
    render(<ResultCard result={completedResult} />)
    expect(screen.getByText('B2.1')).toBeInTheDocument()
  })

  it('shows communicative profile in French by default', () => {
    render(<ResultCard result={completedResult} />)
    expect(screen.getByText('Communicateur avancé')).toBeInTheDocument()
  })

  it('toggles to English on button click', () => {
    render(<ResultCard result={completedResult} />)
    fireEvent.click(screen.getByRole('button', { name: 'English' }))
    expect(screen.getByText('Advanced Communicator')).toBeInTheDocument()
  })

  it('shows French global comment by default', () => {
    render(<ResultCard result={completedResult} />)
    expect(screen.getByText('Très bon travail.')).toBeInTheDocument()
  })

  it('shows English global comment after toggle', () => {
    render(<ResultCard result={completedResult} />)
    fireEvent.click(screen.getByRole('button', { name: 'English' }))
    expect(screen.getByText('Very good work.')).toBeInTheDocument()
  })

  it('shows PDF download link', () => {
    render(<ResultCard result={completedResult} />)
    const link = screen.getByRole('link', { name: /télécharger le rapport/i })
    expect(link).toBeInTheDocument()
    expect(link).toHaveAttribute('href', expect.stringContaining('/report'))
  })

  it('shows failed state for failed evaluation', () => {
    render(<ResultCard result={failedResult} />)
    expect(screen.getByText('Evaluation Failed')).toBeInTheDocument()
    expect(screen.getByText('Processing error occurred.')).toBeInTheDocument()
  })

  it('shows audio duration', () => {
    render(<ResultCard result={completedResult} />)
    expect(screen.getByText(/20 min/)).toBeInTheDocument()
  })
})
