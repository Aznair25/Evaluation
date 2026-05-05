'use client'

import { useEffect, useState } from 'react'
import { useParams, useRouter } from 'next/navigation'
import { useAuth } from '@/hooks/useAuth'
import { apiClient } from '@/lib/api'
import { useEvaluationSSE } from '@/hooks/useEvaluationSSE'
import { ProgressTracker } from '@/components/ProgressTracker'
import { ResultCard } from '@/components/ResultCard'
import type { EvaluationResult } from '@/lib/types'

export default function EvaluationDetailPage() {
  const { user, loading } = useAuth()
  const router = useRouter()
  const params = useParams()
  const id = params.id as string

  const [result, setResult] = useState<EvaluationResult | null>(null)
  const [fetching, setFetching] = useState(true)
  const { progress, completed, failed } = useEvaluationSSE(id)

  useEffect(() => {
    if (!loading && !user) router.replace('/')
  }, [user, loading, router])

  useEffect(() => {
    if (!id) return
    apiClient
      .getEvaluation(id)
      .then(setResult)
      .finally(() => setFetching(false))
  }, [id])

  // Refresh result once pipeline completes
  useEffect(() => {
    if (completed || failed) {
      apiClient.getEvaluation(id).then(setResult)
    }
  }, [completed, failed, id])

  if (loading || fetching) {
    return (
      <div className="flex justify-center mt-20">
        <p className="text-gray-400 animate-pulse">Loading…</p>
      </div>
    )
  }

  if (!result) return <p className="text-red-500">Evaluation not found.</p>

  const isProcessing = !['completed', 'failed'].includes(result.status)

  return (
    <div className="max-w-4xl mx-auto space-y-8">
      <div className="flex items-center gap-3">
        <h1 className="text-2xl font-bold text-gray-800">Evaluation</h1>
        <span className="font-mono text-xs text-gray-400">{id}</span>
      </div>

      {isProcessing && (
        <ProgressTracker
          status={progress?.status ?? result.status}
          progressPercentage={progress?.progress_percentage ?? (result.status === 'pending' ? 0 : undefined)}
          currentStep={progress?.current_step ?? result.status}
        />
      )}

      {(result.status === 'completed' || result.status === 'failed') && (
        <ResultCard result={result} />
      )}
    </div>
  )
}
