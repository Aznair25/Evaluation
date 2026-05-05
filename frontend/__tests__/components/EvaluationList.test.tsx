import { render, screen } from '@testing-library/react'
import { EvaluationList } from '@/components/EvaluationList'
import type { EvaluationListItem } from '@/lib/types'

jest.mock('next/link', () => {
  return function MockLink({ children, href }: { children: React.ReactNode; href: string }) {
    return <a href={href}>{children}</a>
  }
})

const items: EvaluationListItem[] = [
  {
    evaluation_id: 'abc-123',
    status: 'completed',
    cefr_level: 'B1.2',
    student_name: 'Jane Dupont',
    created_at: '2024-01-15T10:00:00Z',
  },
  {
    evaluation_id: 'def-456',
    status: 'failed',
    cefr_level: null,
    student_name: null,
    created_at: '2024-01-16T11:00:00Z',
  },
]

describe('EvaluationList', () => {
  it('renders empty state with link', () => {
    render(<EvaluationList evaluations={[]} />)
    expect(screen.getByText('No evaluations yet.')).toBeInTheDocument()
    expect(screen.getByText('Start your first evaluation')).toBeInTheDocument()
  })

  it('renders evaluation items', () => {
    render(<EvaluationList evaluations={items} />)
    expect(screen.getByText('Jane Dupont')).toBeInTheDocument()
    expect(screen.getByText('B1.2')).toBeInTheDocument()
  })

  it('shows "Unknown Student" for null student_name', () => {
    render(<EvaluationList evaluations={items} />)
    expect(screen.getByText('Unknown Student')).toBeInTheDocument()
  })

  it('shows Completed badge for completed status', () => {
    render(<EvaluationList evaluations={items} />)
    expect(screen.getByText('Completed')).toBeInTheDocument()
  })

  it('shows Failed badge for failed status', () => {
    render(<EvaluationList evaluations={items} />)
    expect(screen.getByText('Failed')).toBeInTheDocument()
  })

  it('links to evaluation detail page', () => {
    render(<EvaluationList evaluations={items} />)
    const links = screen.getAllByRole('link')
    expect(links[0]).toHaveAttribute('href', '/evaluations/abc-123')
  })
})
