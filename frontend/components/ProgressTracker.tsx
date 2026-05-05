'use client'

import type { EvaluationStatus } from '@/lib/types'

interface ProgressTrackerProps {
  status: EvaluationStatus
  progressPercentage?: number
  currentStep: string | null
}

const STATUS_STEPS: { key: EvaluationStatus; label: string }[] = [
  { key: 'pending',           label: 'Queued' },
  { key: 'transcribing',      label: 'Transcribing' },
  { key: 'analyzing',         label: 'Analyzing' },
  { key: 'generating_report', label: 'Generating Report' },
  { key: 'completed',         label: 'Completed' },
]

const STATUS_ORDER = STATUS_STEPS.map((s) => s.key)

function getStepIndex(status: EvaluationStatus): number {
  const idx = STATUS_ORDER.indexOf(status)
  return idx >= 0 ? idx : 0
}

export function ProgressTracker({ status, progressPercentage, currentStep }: ProgressTrackerProps) {
  const pct = progressPercentage ?? (getStepIndex(status) / (STATUS_STEPS.length - 1)) * 100

  return (
    <div className="rounded-xl border border-gray-200 bg-white p-6 shadow-sm space-y-4" role="status" aria-label="Evaluation progress">
      <div className="flex items-center justify-between">
        <h2 className="font-semibold text-gray-700">Processing…</h2>
        <span className="text-sm font-mono text-brand-600">{Math.round(pct)}%</span>
      </div>

      {/* Progress bar */}
      <div className="h-3 w-full rounded-full bg-gray-100 overflow-hidden">
        <div
          className="h-full rounded-full bg-brand-500 transition-all duration-500"
          style={{ width: `${pct}%` }}
          role="progressbar"
          aria-valuenow={Math.round(pct)}
          aria-valuemin={0}
          aria-valuemax={100}
        />
      </div>

      {/* Step indicators */}
      <div className="flex items-center gap-1 sm:gap-2 overflow-x-auto pb-1">
        {STATUS_STEPS.map((step, idx) => {
          const currentIdx = getStepIndex(status)
          const done = idx < currentIdx
          const active = idx === currentIdx
          return (
            <div key={step.key} className="flex items-center gap-1">
              <div
                className={`flex h-6 w-6 flex-shrink-0 items-center justify-center rounded-full text-xs font-bold transition-colors ${
                  done
                    ? 'bg-brand-600 text-white'
                    : active
                    ? 'bg-brand-100 text-brand-700 ring-2 ring-brand-500'
                    : 'bg-gray-100 text-gray-400'
                }`}
              >
                {done ? '✓' : idx + 1}
              </div>
              <span className={`text-xs hidden sm:block ${active ? 'font-semibold text-brand-700' : done ? 'text-gray-600' : 'text-gray-400'}`}>
                {step.label}
              </span>
              {idx < STATUS_STEPS.length - 1 && (
                <div className={`h-px w-4 sm:w-6 flex-shrink-0 ${done ? 'bg-brand-600' : 'bg-gray-200'}`} />
              )}
            </div>
          )
        })}
      </div>

      {currentStep && (
        <p className="text-sm text-gray-500 italic">{currentStep}</p>
      )}
    </div>
  )
}
