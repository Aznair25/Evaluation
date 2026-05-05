'use client'

import { useEffect } from 'react'
import { useRouter } from 'next/navigation'
import { useAuth } from '@/hooks/useAuth'
import { EvaluationForm } from '@/components/EvaluationForm'

export default function NewEvaluationPage() {
  const { user, loading } = useAuth()
  const router = useRouter()

  useEffect(() => {
    if (!loading && !user) router.replace('/')
  }, [user, loading, router])

  if (loading) {
    return (
      <div className="flex justify-center mt-20">
        <p className="text-gray-400 animate-pulse">Loading…</p>
      </div>
    )
  }

  return (
    <div className="max-w-2xl mx-auto">
      <h1 className="text-2xl font-bold text-gray-800 mb-6">New Evaluation</h1>
      <EvaluationForm
        onSuccess={(id) => router.push(`/evaluations/${id}`)}
      />
    </div>
  )
}
