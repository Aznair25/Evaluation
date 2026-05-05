import { render, screen } from '@testing-library/react'
import { CriteriaTable } from '@/components/CriteriaTable'
import type { CriterionResult } from '@/lib/types'

const criteria: Record<string, CriterionResult> = {
  interaction: {
    achieved: true,
    evidence: ['Asked follow-up questions'],
    comment_fr: 'Bonne interaction.',
    comment_en: 'Good interaction.',
  },
  clarity: {
    achieved: false,
    evidence: [],
    comment_fr: 'Idées parfois floues.',
    comment_en: 'Ideas sometimes unclear.',
  },
  strategies: {
    achieved: null,
    evidence: [],
    comment_fr: null,
    comment_en: null,
  },
  vocabulary: {
    achieved: true,
    evidence: [],
    comment_fr: 'Bon vocabulaire.',
    comment_en: 'Good vocabulary.',
  },
  fluency: {
    achieved: false,
    evidence: [],
    comment_fr: 'Quelques hésitations.',
    comment_en: 'Some hesitations.',
    azure_scores: { fluency_score: 65.0 },
  },
  pronunciation: {
    achieved: true,
    evidence: [],
    comment_fr: 'Prononciation correcte.',
    comment_en: 'Correct pronunciation.',
  },
}

describe('CriteriaTable (French)', () => {
  it('renders all 6 criteria rows', () => {
    render(<CriteriaTable criteria={criteria} lang="fr" />)
    expect(screen.getByText('Interaction')).toBeInTheDocument()
    expect(screen.getByText('Clarté du message')).toBeInTheDocument()
    expect(screen.getByText('Stratégies de communication')).toBeInTheDocument()
    expect(screen.getByText('Vocabulaire et structures')).toBeInTheDocument()
    expect(screen.getByText('Fluidité et aisance')).toBeInTheDocument()
    expect(screen.getByText('Prononciation')).toBeInTheDocument()
  })

  it('shows "Oui" for achieved=true in French', () => {
    render(<CriteriaTable criteria={criteria} lang="fr" />)
    const badges = screen.getAllByText('Oui')
    expect(badges.length).toBeGreaterThan(0)
  })

  it('shows "Non" for achieved=false in French', () => {
    render(<CriteriaTable criteria={criteria} lang="fr" />)
    const badges = screen.getAllByText('Non')
    expect(badges.length).toBeGreaterThan(0)
  })

  it('shows French comments', () => {
    render(<CriteriaTable criteria={criteria} lang="fr" />)
    expect(screen.getByText('Bonne interaction.')).toBeInTheDocument()
  })
})

describe('CriteriaTable (English)', () => {
  it('shows "Yes" for achieved=true in English', () => {
    render(<CriteriaTable criteria={criteria} lang="en" />)
    const badges = screen.getAllByText('Yes')
    expect(badges.length).toBeGreaterThan(0)
  })

  it('shows "No" for achieved=false in English', () => {
    render(<CriteriaTable criteria={criteria} lang="en" />)
    const badges = screen.getAllByText('No')
    expect(badges.length).toBeGreaterThan(0)
  })

  it('shows English comments', () => {
    render(<CriteriaTable criteria={criteria} lang="en" />)
    expect(screen.getByText('Good interaction.')).toBeInTheDocument()
  })

  it('shows English column header', () => {
    render(<CriteriaTable criteria={criteria} lang="en" />)
    expect(screen.getByText('Achieved')).toBeInTheDocument()
  })
})

describe('CriteriaTable error state', () => {
  it('shows error badge for criteria with error', () => {
    const withError: Record<string, CriterionResult> = {
      ...criteria,
      interaction: {
        achieved: null,
        evidence: [],
        comment_fr: null,
        comment_en: null,
        error: 'API timeout',
      },
    }
    render(<CriteriaTable criteria={withError} lang="en" />)
    expect(screen.getByText('Error')).toBeInTheDocument()
    expect(screen.getByText('API timeout')).toBeInTheDocument()
  })
})
