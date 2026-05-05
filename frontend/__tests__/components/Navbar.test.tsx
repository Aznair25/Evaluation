import { render, screen, fireEvent, waitFor } from '@testing-library/react'
import { Navbar } from '@/components/Navbar'
import { AuthContext } from '@/context/AuthContext'
import type { UserOut } from '@/lib/types'

const mockPush = jest.fn()
jest.mock('next/navigation', () => ({
  useRouter: () => ({ push: mockPush }),
}))
jest.mock('next/link', () => {
  return function MockLink({ children, href }: { children: React.ReactNode; href: string }) {
    return <a href={href}>{children}</a>
  }
})

const mockUser: UserOut = {
  id: 'user-1',
  email: 'test@example.com',
  name: 'Test User',
  picture_url: null,
  created_at: '2024-01-01T00:00:00Z',
  last_login: '2024-01-01T00:00:00Z',
}

function renderWithAuth(user: UserOut | null, loading = false) {
  const logout = jest.fn().mockResolvedValue(undefined)
  render(
    <AuthContext.Provider value={{ user, loading, setUser: jest.fn(), logout }}>
      <Navbar />
    </AuthContext.Provider>,
  )
  return { logout }
}

describe('Navbar', () => {
  beforeEach(() => mockPush.mockClear())

  it('shows Sign in when not authenticated', () => {
    renderWithAuth(null, false)
    expect(screen.getByText('Sign in')).toBeInTheDocument()
  })

  it('shows user name when authenticated', () => {
    renderWithAuth(mockUser)
    expect(screen.getByText('Test User')).toBeInTheDocument()
  })

  it('shows Dashboard link when authenticated', () => {
    renderWithAuth(mockUser)
    expect(screen.getByRole('link', { name: /dashboard/i })).toBeInTheDocument()
  })

  it('shows New Evaluation link when authenticated', () => {
    renderWithAuth(mockUser)
    expect(screen.getByRole('link', { name: /new evaluation/i })).toBeInTheDocument()
  })

  it('calls logout and redirects on Sign out click', async () => {
    const { logout } = renderWithAuth(mockUser)
    fireEvent.click(screen.getByText('Sign out'))
    await waitFor(() => {
      expect(logout).toHaveBeenCalled()
      expect(mockPush).toHaveBeenCalledWith('/')
    })
  })

  it('renders brand logo link', () => {
    renderWithAuth(null)
    const logo = screen.getByText('CEFR Evaluator')
    expect(logo).toBeInTheDocument()
  })
})
