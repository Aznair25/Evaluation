'use client'

import { useEffect } from 'react'
import { useRouter, useSearchParams } from 'next/navigation'
import { saveToken } from '@/lib/auth'
import { apiClient } from '@/lib/api'
import { useAuth } from '@/hooks/useAuth'

export default function AuthCallbackPage() {
  const router = useRouter()
  const params = useSearchParams()
  const { setUser } = useAuth()

  useEffect(() => {
    const token = params.get('token')
    if (!token) {
      router.replace('/?error=auth_failed')
      return
    }
    saveToken(token)
    apiClient.getMe().then((user) => {
      setUser(user)
      router.replace('/dashboard')
    }).catch(() => {
      router.replace('/?error=auth_failed')
    })
  }, [params, router, setUser])

  return (
    <div className="flex items-center justify-center min-h-[60vh]">
      <p className="text-gray-500 animate-pulse">Signing you in…</p>
    </div>
  )
}
