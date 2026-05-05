'use client'

import React, { createContext, useCallback, useEffect, useState } from 'react'
import { apiClient } from '@/lib/api'
import { clearToken, getToken } from '@/lib/auth'
import type { UserOut } from '@/lib/types'

interface AuthContextValue {
  user: UserOut | null
  loading: boolean
  setUser: (user: UserOut | null) => void
  logout: () => Promise<void>
}

export const AuthContext = createContext<AuthContextValue>({
  user: null,
  loading: true,
  setUser: () => {},
  logout: async () => {},
})

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [user, setUserState] = useState<UserOut | null>(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    const token = getToken()
    if (!token) {
      setLoading(false)
      return
    }
    apiClient
      .getMe()
      .then(setUserState)
      .catch(() => clearToken())
      .finally(() => setLoading(false))
  }, [])

  const setUser = useCallback((u: UserOut | null) => setUserState(u), [])

  const logout = useCallback(async () => {
    await apiClient.logout().catch(() => {})
    clearToken()
    setUserState(null)
  }, [])

  return (
    <AuthContext.Provider value={{ user, loading, setUser, logout }}>
      {children}
    </AuthContext.Provider>
  )
}
