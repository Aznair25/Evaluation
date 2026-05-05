'use client'

import { useState } from 'react'
import type { EvaluationResult } from '@/lib/types'
import { CriteriaTable } from './CriteriaTable'
import { apiClient } from '@/lib/api'

interface ResultCardProps {
  result: EvaluationResult
}

export function ResultCard({ result }: ResultCardProps) {
  const [lang, setLang] = useState<'fr' | 'en'>('fr')

  if (result.status === 'failed') {
    return (
      <div className="rounded-xl border border-red-200 bg-red-50 p-6">
        <h2 className="font-semibold text-red-700 mb-2">Evaluation Failed</h2>
        <p className="text-sm text-red-600">
          {result.global_comment_fr ?? 'An error occurred during processing.'}
        </p>
      </div>
    )
  }

  const isFr = lang === 'fr'

  return (
    <div className="space-y-6">
      {/* Language toggle */}
      <div className="flex gap-2">
        <button
          onClick={() => setLang('fr')}
          className={`px-4 py-1.5 rounded-full text-sm font-medium transition-colors ${
            isFr ? 'bg-brand-600 text-white' : 'bg-gray-100 text-gray-600 hover:bg-gray-200'
          }`}
        >
          Français
        </button>
        <button
          onClick={() => setLang('en')}
          className={`px-4 py-1.5 rounded-full text-sm font-medium transition-colors ${
            !isFr ? 'bg-brand-600 text-white' : 'bg-gray-100 text-gray-600 hover:bg-gray-200'
          }`}
        >
          English
        </button>
      </div>

      {/* CEFR Level */}
      <div className="rounded-xl border border-brand-200 bg-brand-50 p-6 flex flex-col sm:flex-row items-start sm:items-center gap-4">
        <div>
          <p className="text-xs font-semibold uppercase tracking-wider text-brand-600 mb-1">
            {isFr ? 'Niveau CECR' : 'CEFR Level'}
          </p>
          <p className="text-5xl font-extrabold text-brand-700">{result.cefr_level ?? '—'}</p>
        </div>
        <div className="flex-1">
          <p className="text-sm font-semibold text-gray-700 mb-0.5">
            {isFr ? 'Profil communicatif' : 'Communicative Profile'}
          </p>
          <p className="text-gray-600">
            {isFr ? result.communicative_profile_fr : result.communicative_profile_en}
          </p>
          {result.audio_duration_seconds && (
            <p className="text-xs text-gray-400 mt-1">
              {isFr ? 'Durée audio' : 'Audio duration'}:{' '}
              {Math.round(result.audio_duration_seconds / 60)} min
              {result.student_speaking_duration_seconds != null && (
                <>
                  {' '}·{' '}
                  {isFr ? 'Prise de parole' : 'Student speech'}:{' '}
                  {Math.round(result.student_speaking_duration_seconds / 60)} min
                </>
              )}
            </p>
          )}
        </div>
      </div>

      {/* Criteria table */}
      {result.criteria && (
        <div>
          <h3 className="font-semibold text-gray-800 mb-3">
            {isFr ? 'Tableau des critères' : 'Criteria Table'}
          </h3>
          <CriteriaTable criteria={result.criteria} lang={lang} />
        </div>
      )}

      {/* Global comment */}
      {(isFr ? result.global_comment_fr : result.global_comment_en) && (
        <div className="rounded-xl border border-gray-200 bg-white p-5">
          <h3 className="font-semibold text-gray-800 mb-2">
            {isFr ? 'Commentaire global' : 'Global Comment'}
          </h3>
          <p className="text-sm text-gray-600 leading-relaxed">
            {isFr ? result.global_comment_fr : result.global_comment_en}
          </p>
        </div>
      )}

      {/* Download report */}
      {result.report_url && (
        <a
          href={apiClient.getReportUrl(result.evaluation_id)}
          target="_blank"
          rel="noopener noreferrer"
          className="inline-flex items-center gap-2 rounded-lg bg-brand-600 px-5 py-2.5 text-sm font-semibold text-white hover:bg-brand-700 transition-colors"
        >
          📄 {isFr ? 'Télécharger le rapport PDF' : 'Download PDF Report'}
        </a>
      )}
    </div>
  )
}
