'use client'

import { useRef, useState } from 'react'
import { apiClient } from '@/lib/api'

interface EvaluationFormProps {
  onSuccess: (evaluationId: string) => void
}

const ALLOWED_TYPES = ['.mp3', '.wav', '.ogg', '.flac', '.m4a', '.webm']

export function EvaluationForm({ onSuccess }: EvaluationFormProps) {
  const [file, setFile] = useState<File | null>(null)
  const [studentName, setStudentName] = useState('')
  const [evaluatorName, setEvaluatorName] = useState('')
  const [institution, setInstitution] = useState('')
  const [date, setDate] = useState('')
  const [language, setLanguage] = useState('fr')
  const [submitting, setSubmitting] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [fileError, setFileError] = useState<string | null>(null)
  const fileRef = useRef<HTMLInputElement>(null)

  function handleFileChange(e: React.ChangeEvent<HTMLInputElement>) {
    const selected = e.target.files?.[0] ?? null
    setFileError(null)
    if (!selected) {
      setFile(null)
      return
    }
    const lastDot = selected.name.lastIndexOf('.')
    // Handle edge case: file named '.mp3' (hidden file with no real extension)
    const ext = lastDot > 0 ? selected.name.slice(lastDot).toLowerCase() : ''
    if (!ALLOWED_TYPES.includes(ext)) {
      setFileError(`Unsupported file type. Allowed: ${ALLOWED_TYPES.join(', ')}`)
      setFile(null)
      return
    }
    const maxMb = 200
    if (selected.size > maxMb * 1024 * 1024) {
      setFileError(`File too large. Maximum size: ${maxMb} MB`)
      setFile(null)
      return
    }
    setFile(selected)
  }

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault()
    if (!file) {
      setFileError('Please select an audio file.')
      return
    }
    setSubmitting(true)
    setError(null)
    try {
      const result = await apiClient.uploadEvaluation({
        audioFile: file,
        studentName: studentName || undefined,
        evaluatorName: evaluatorName || undefined,
        institution: institution || undefined,
        date: date || undefined,
        language,
      })
      onSuccess(result.evaluation_id)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Upload failed.')
    } finally {
      setSubmitting(false)
    }
  }

  return (
    <form onSubmit={handleSubmit} className="space-y-5 rounded-xl border border-gray-200 bg-white p-6 shadow-sm">
      {/* Audio file */}
      <div>
        <label className="block text-sm font-medium text-gray-700 mb-1">
          Audio Recording <span className="text-red-500">*</span>
        </label>
        <input
          ref={fileRef}
          type="file"
          accept={ALLOWED_TYPES.join(',')}
          onChange={handleFileChange}
          className="block w-full text-sm text-gray-600 file:mr-4 file:rounded-md file:border-0 file:bg-brand-50 file:px-4 file:py-2 file:text-sm file:font-medium file:text-brand-700 hover:file:bg-brand-100 cursor-pointer"
          aria-label="Audio file upload"
          data-testid="audio-file-input"
        />
        {fileError && <p className="mt-1 text-xs text-red-600">{fileError}</p>}
        {file && (
          <p className="mt-1 text-xs text-gray-500">
            {file.name} ({(file.size / 1024 / 1024).toFixed(1)} MB)
          </p>
        )}
      </div>

      {/* Metadata */}
      <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
        <FormField label="Student Name" value={studentName} onChange={setStudentName} placeholder="Jane Dupont" />
        <FormField label="Evaluator Name" value={evaluatorName} onChange={setEvaluatorName} placeholder="Prof. Martin" />
        <FormField label="Institution" value={institution} onChange={setInstitution} placeholder="Université Paris" />
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">Date</label>
          <input
            type="date"
            value={date}
            onChange={(e) => setDate(e.target.value)}
            className="w-full rounded-md border border-gray-300 px-3 py-2 text-sm focus:border-brand-500 focus:ring-1 focus:ring-brand-500 outline-none"
          />
        </div>
      </div>

      {/* Language */}
      <div>
        <label className="block text-sm font-medium text-gray-700 mb-1">Language</label>
        <select
          value={language}
          onChange={(e) => setLanguage(e.target.value)}
          className="w-full rounded-md border border-gray-300 px-3 py-2 text-sm focus:border-brand-500 focus:ring-1 focus:ring-brand-500 outline-none"
        >
          <option value="fr">French (fr)</option>
          <option value="en">English (en)</option>
        </select>
      </div>

      {error && <p className="text-sm text-red-600">{error}</p>}

      <button
        type="submit"
        disabled={submitting || !file}
        className="w-full rounded-lg bg-brand-600 px-4 py-2.5 text-sm font-semibold text-white hover:bg-brand-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
      >
        {submitting ? 'Uploading…' : 'Start Evaluation'}
      </button>
    </form>
  )
}

function FormField({
  label,
  value,
  onChange,
  placeholder,
}: {
  label: string
  value: string
  onChange: (v: string) => void
  placeholder?: string
}) {
  return (
    <div>
      <label className="block text-sm font-medium text-gray-700 mb-1">{label}</label>
      <input
        type="text"
        value={value}
        onChange={(e) => onChange(e.target.value)}
        placeholder={placeholder}
        className="w-full rounded-md border border-gray-300 px-3 py-2 text-sm focus:border-brand-500 focus:ring-1 focus:ring-brand-500 outline-none"
      />
    </div>
  )
}
