import { saveToken, getToken, clearToken, isAuthenticated } from '@/lib/auth'

function makeJwt(payload: Record<string, unknown>): string {
  const header = btoa(JSON.stringify({ alg: 'HS256', typ: 'JWT' }))
  const body = btoa(JSON.stringify(payload))
  return `${header}.${body}.signature`
}

describe('auth lib', () => {
  beforeEach(() => {
    localStorage.clear()
  })

  it('saves and retrieves a token', () => {
    saveToken('test-token')
    expect(getToken()).toBe('test-token')
  })

  it('returns null when no token is stored', () => {
    expect(getToken()).toBeNull()
  })

  it('clears the token', () => {
    saveToken('test-token')
    clearToken()
    expect(getToken()).toBeNull()
  })

  it('isAuthenticated returns false when no token', () => {
    expect(isAuthenticated()).toBe(false)
  })

  it('isAuthenticated returns true for a valid non-expired token', () => {
    const exp = Math.floor(Date.now() / 1000) + 3600
    const token = makeJwt({ sub: 'user-id', exp })
    saveToken(token)
    expect(isAuthenticated()).toBe(true)
  })

  it('isAuthenticated returns false for an expired token', () => {
    const exp = Math.floor(Date.now() / 1000) - 10
    const token = makeJwt({ sub: 'user-id', exp })
    saveToken(token)
    expect(isAuthenticated()).toBe(false)
  })

  it('isAuthenticated returns false for a malformed token', () => {
    saveToken('not.a.jwt')
    expect(isAuthenticated()).toBe(false)
  })
})
