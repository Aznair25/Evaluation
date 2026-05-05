import { render, screen, fireEvent, waitFor } from '@testing-library/react'
import { EvaluationForm } from '@/components/EvaluationForm'
import * as apiModule from '@/lib/api'

jest.mock('@/lib/api', () => ({
  apiClient: {
    uploadEvaluation: jest.fn(),
  },
}))

function makeFile(name = 'test.mp3', type = 'audio/mpeg', size = 1024) {
  const file = new File([new ArrayBuffer(size)], name, { type })
  return file
}

describe('EvaluationForm', () => {
  const onSuccess = jest.fn()

  beforeEach(() => {
    jest.clearAllMocks()
  })

  it('renders the file input and submit button', () => {
    render(<EvaluationForm onSuccess={onSuccess} />)
    expect(screen.getByTestId('audio-file-input')).toBeInTheDocument()
    expect(screen.getByRole('button', { name: /start evaluation/i })).toBeInTheDocument()
  })

  it('submit button is disabled when no file is selected', () => {
    render(<EvaluationForm onSuccess={onSuccess} />)
    expect(screen.getByRole('button', { name: /start evaluation/i })).toBeDisabled()
  })

  it('shows error for unsupported file type', () => {
    render(<EvaluationForm onSuccess={onSuccess} />)
    const input = screen.getByTestId('audio-file-input')
    const file = makeFile('test.txt', 'text/plain')
    fireEvent.change(input, { target: { files: [file] } })
    expect(screen.getByText(/unsupported file type/i)).toBeInTheDocument()
  })

  it('shows file name after valid file is selected', () => {
    render(<EvaluationForm onSuccess={onSuccess} />)
    const input = screen.getByTestId('audio-file-input')
    const file = makeFile('audio.wav', 'audio/wav', 1024)
    fireEvent.change(input, { target: { files: [file] } })
    expect(screen.getByText(/audio\.wav/)).toBeInTheDocument()
  })

  it('calls onSuccess with evaluation_id after upload', async () => {
    const mockUpload = jest.spyOn(apiModule.apiClient, 'uploadEvaluation').mockResolvedValueOnce({
      evaluation_id: 'test-eval-id',
      status: 'processing',
      message: 'ok',
    })

    render(<EvaluationForm onSuccess={onSuccess} />)

    const input = screen.getByTestId('audio-file-input')
    const file = makeFile('audio.mp3', 'audio/mpeg', 1024)
    fireEvent.change(input, { target: { files: [file] } })

    fireEvent.click(screen.getByRole('button', { name: /start evaluation/i }))

    await waitFor(() => {
      expect(onSuccess).toHaveBeenCalledWith('test-eval-id')
    })
    mockUpload.mockRestore()
  })

  it('shows error message on upload failure', async () => {
    const mockUpload = jest.spyOn(apiModule.apiClient, 'uploadEvaluation').mockRejectedValueOnce(
      new Error('HTTP 500: Server error')
    )

    render(<EvaluationForm onSuccess={onSuccess} />)

    const input = screen.getByTestId('audio-file-input')
    const file = makeFile('audio.mp3', 'audio/mpeg', 1024)
    fireEvent.change(input, { target: { files: [file] } })

    fireEvent.click(screen.getByRole('button', { name: /start evaluation/i }))

    await waitFor(() => {
      expect(screen.getByText(/HTTP 500/)).toBeInTheDocument()
    })
    mockUpload.mockRestore()
  })
})
