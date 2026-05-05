'use client'

import { useEffect, useRef, useState } from 'react'
import { getToken } from '@/lib/auth'
import { apiClient } from '@/lib/api'
import type { SSEEvent } from '@/lib/types'

interface SSEState {
  progress: SSEEvent | null
  completed: boolean
  failed: boolean
  error: string | null
}

export function useEvaluationSSE(evaluationId: string | null): SSEState {
  const [state, setState] = useState<SSEState>({
    progress: null,
    completed: false,
    failed: false,
    error: null,
  })
  const esRef = useRef<EventSource | null>(null)

  useEffect(() => {
    if (!evaluationId) return

    // SSE with auth: include token as query param (EventSource doesn't support headers)
    const token = getToken()
    const url = `${apiClient.getEventsUrl(evaluationId)}${token ? `?token=${encodeURIComponent(token)}` : ''}`
    const es = new EventSource(url)
    esRef.current = es

    es.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data) as SSEEvent
        setState((prev) => ({
          ...prev,
          progress: data,
          completed: data.status === 'completed',
          failed: data.status === 'failed',
        }))
        if (data.status === 'completed' || data.status === 'failed') {
          es.close()
        }
      } catch {
        // ignore parse errors
      }
    }

    es.onerror = () => {
      setState((prev) => ({ ...prev, error: 'Connection error' }))
      es.close()
    }

    return () => {
      es.close()
    }
  }, [evaluationId])

  return state
}
