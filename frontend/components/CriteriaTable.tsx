'use client'

import type { CriterionResult } from '@/lib/types'

const CRITERION_LABELS: Record<string, { fr: string; en: string }> = {
  interaction:   { fr: 'Interaction',               en: 'Interaction' },
  clarity:       { fr: 'Clarté du message',         en: 'Message Clarity' },
  strategies:    { fr: 'Stratégies de communication', en: 'Communication Strategies' },
  vocabulary:    { fr: 'Vocabulaire et structures',  en: 'Vocabulary & Structures' },
  fluency:       { fr: 'Fluidité et aisance',        en: 'Fluency & Ease' },
  pronunciation: { fr: 'Prononciation',              en: 'Pronunciation' },
}

interface CriteriaTableProps {
  criteria: Record<string, CriterionResult>
  lang?: 'fr' | 'en'
}

export function CriteriaTable({ criteria, lang = 'fr' }: CriteriaTableProps) {
  const entries = Object.entries(CRITERION_LABELS).map(([key, labels]) => ({
    key,
    label: lang === 'fr' ? labels.fr : labels.en,
    result: criteria[key] ?? null,
  }))

  return (
    <div className="overflow-x-auto rounded-xl border border-gray-200">
      <table className="w-full text-sm">
        <thead className="bg-brand-600 text-white">
          <tr>
            <th className="px-4 py-3 text-left font-semibold">
              {lang === 'fr' ? 'Critère' : 'Criterion'}
            </th>
            <th className="px-4 py-3 text-center font-semibold w-20">
              {lang === 'fr' ? 'Atteint' : 'Achieved'}
            </th>
            <th className="px-4 py-3 text-left font-semibold">
              {lang === 'fr' ? 'Commentaire' : 'Comment'}
            </th>
          </tr>
        </thead>
        <tbody>
          {entries.map(({ key, label, result }, idx) => (
            <tr key={key} className={idx % 2 === 0 ? 'bg-white' : 'bg-gray-50'}>
              <td className="px-4 py-3 font-medium text-gray-800">{label}</td>
              <td className="px-4 py-3 text-center">
                <AchievedBadge achieved={result?.achieved ?? null} error={result?.error} lang={lang} />
              </td>
              <td className="px-4 py-3 text-gray-600">
                {result?.error ? (
                  <span className="text-red-500 text-xs">{result.error}</span>
                ) : (
                  (lang === 'fr' ? result?.comment_fr : result?.comment_en) ?? '—'
                )}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}

function AchievedBadge({
  achieved,
  error,
  lang,
}: {
  achieved: boolean | null
  error?: string
  lang: 'fr' | 'en'
}) {
  if (error) return <span className="inline-block rounded px-2 py-0.5 text-xs bg-red-100 text-red-700">Error</span>
  if (achieved === true)
    return (
      <span className="inline-block rounded px-2 py-0.5 text-xs font-semibold bg-green-100 text-green-700">
        {lang === 'fr' ? 'Oui' : 'Yes'}
      </span>
    )
  if (achieved === false)
    return (
      <span className="inline-block rounded px-2 py-0.5 text-xs font-semibold bg-red-100 text-red-700">
        {lang === 'fr' ? 'Non' : 'No'}
      </span>
    )
  return <span className="text-gray-400 text-xs">—</span>
}
