import { render, screen } from '@testing-library/react'
import { ProgressTracker } from '@/components/ProgressTracker'

describe('ProgressTracker', () => {
  it('renders processing heading', () => {
    render(<ProgressTracker status="pending" currentStep="Queued for processing" />)
    expect(screen.getByText('Processing…')).toBeInTheDocument()
  })

  it('shows current step text', () => {
    render(<ProgressTracker status="transcribing" currentStep="Transcribing audio…" />)
    expect(screen.getByText('Transcribing audio…')).toBeInTheDocument()
  })

  it('renders progress bar with aria attributes', () => {
    render(<ProgressTracker status="analyzing" progressPercentage={60} currentStep={null} />)
    const bar = screen.getByRole('progressbar')
    expect(bar).toHaveAttribute('aria-valuenow', '60')
    expect(bar).toHaveAttribute('aria-valuemin', '0')
    expect(bar).toHaveAttribute('aria-valuemax', '100')
  })

  it('shows percentage', () => {
    render(<ProgressTracker status="analyzing" progressPercentage={75} currentStep={null} />)
    expect(screen.getByText('75%')).toBeInTheDocument()
  })

  it('has status role', () => {
    render(<ProgressTracker status="transcribing" currentStep="Working…" />)
    expect(screen.getByRole('status')).toBeInTheDocument()
  })
})
