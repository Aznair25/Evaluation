'use client'

import Link from 'next/link'
import type { EvaluationListItem, EvaluationStatus } from '@/lib/types'

interface EvaluationListProps {
  evaluations: EvaluationListItem[]
}

const STATUS_COLORS: Record<EvaluationStatus, string> = {
  pending:           'bg-gray-100 text-gray-600',
  transcribing:      'bg-blue-100 text-blue-700',
  analyzing:         'bg-yellow-100 text-yellow-700',
  generating_report: 'bg-purple-100 text-purple-700',
  completed:         'bg-green-100 text-green-700',
  failed:            'bg-red-100 text-red-700',
}

const STATUS_LABELS: Record<EvaluationStatus, string> = {
  pending:           'Pending',
  transcribing:      'Transcribing',
  analyzing:         'Analyzing',
  generating_report: 'Generating Report',
  completed:         'Completed',
  failed:            'Failed',
}

export function EvaluationList({ evaluations }: EvaluationListProps) {
  if (evaluations.length === 0) {
    return (
      <div className="rounded-xl border border-dashed border-gray-300 py-16 text-center">
        <p className="text-gray-400 mb-4">No evaluations yet.</p>
        <Link
          href="/evaluations/new"
          className="inline-flex rounded-lg bg-brand-600 px-4 py-2 text-sm font-semibold text-white hover:bg-brand-700 transition-colors"
        >
          Start your first evaluation
        </Link>
      </div>
    )
  }

  return (
    <ul className="space-y-3">
      {evaluations.map((ev) => (
        <li key={ev.evaluation_id}>
          <Link
            href={`/evaluations/${ev.evaluation_id}`}
            className="flex items-center justify-between rounded-xl border border-gray-200 bg-white px-5 py-4 shadow-sm hover:border-brand-300 hover:shadow-md transition-all"
          >
            <div className="flex items-center gap-3">
              <span
                className={`rounded-full px-2.5 py-0.5 text-xs font-medium ${STATUS_COLORS[ev.status]}`}
              >
                {STATUS_LABELS[ev.status]}
              </span>
              <div>
                <p className="text-sm font-semibold text-gray-800">
                  {ev.student_name ?? 'Unknown Student'}
                </p>
                <p className="text-xs text-gray-400">
                  {new Date(ev.created_at).toLocaleDateString()}
                </p>
              </div>
            </div>
            <div className="text-right">
              {ev.cefr_level && (
                <span className="text-lg font-bold text-brand-700">{ev.cefr_level}</span>
              )}
              <p className="text-xs text-gray-400 font-mono">
                {ev.evaluation_id.slice(0, 8)}…
              </p>
            </div>
          </Link>
        </li>
      ))}
    </ul>
  )
}
