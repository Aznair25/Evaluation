'use client'

import { useEffect, useState } from 'react'
import Link from 'next/link'
import { useRouter } from 'next/navigation'
import { apiClient } from '@/lib/api'
import { useAuth } from '@/hooks/useAuth'
import { EvaluationList } from '@/components/EvaluationList'
import type { EvaluationListItem } from '@/lib/types'

export default function DashboardPage() {
  const { user, loading } = useAuth()
  const router = useRouter()
  const [evaluations, setEvaluations] = useState<EvaluationListItem[]>([])
  const [fetching, setFetching] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    if (!loading && !user) {
      router.replace('/')
    }
  }, [user, loading, router])

  useEffect(() => {
    if (!user) return
    apiClient
      .listEvaluations()
      .then(setEvaluations)
      .catch(() => setError('Failed to load evaluations.'))
      .finally(() => setFetching(false))
  }, [user])

  if (loading || fetching) {
    return (
      <div className="flex justify-center mt-20">
        <p className="text-gray-400 animate-pulse">Loading…</p>
      </div>
    )
  }

  return (
    <div>
      <div className="flex items-center justify-between mb-6">
        <h1 className="text-2xl font-bold text-gray-800">My Evaluations</h1>
        <Link
          href="/evaluations/new"
          className="rounded-lg bg-brand-600 px-4 py-2 text-sm font-semibold text-white hover:bg-brand-700 transition-colors"
        >
          + New Evaluation
        </Link>
      </div>
      {error ? (
        <p className="text-red-500">{error}</p>
      ) : (
        <EvaluationList evaluations={evaluations} />
      )}
    </div>
  )
}
