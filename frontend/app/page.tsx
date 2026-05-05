import Link from 'next/link'

export default function HomePage() {
  return (
    <div className="flex flex-col items-center justify-center min-h-[70vh] text-center gap-8">
      <div>
        <h1 className="text-4xl font-extrabold text-brand-700 mb-3">
          CEFR Oral Expression Evaluator
        </h1>
        <p className="text-lg text-gray-600 max-w-xl">
          Upload a French oral exam recording and receive a detailed CEFR level
          assessment with bilingual feedback across 6 criteria.
        </p>
      </div>
      <div className="flex gap-4">
        <a
          href="/api/auth/google"
          className="inline-flex items-center rounded-lg bg-brand-600 px-6 py-3 text-white font-semibold hover:bg-brand-700 transition-colors"
        >
          Sign in with Google
        </a>
        <Link
          href="/dashboard"
          className="inline-flex items-center rounded-lg border border-brand-600 px-6 py-3 text-brand-600 font-semibold hover:bg-brand-50 transition-colors"
        >
          My Evaluations
        </Link>
      </div>
      <div className="grid grid-cols-1 sm:grid-cols-3 gap-6 mt-8 w-full max-w-3xl">
        {[
          { icon: '🎙️', title: 'Upload Audio', desc: 'MP3, WAV, OGG, FLAC, M4A or WebM — up to 200 MB' },
          { icon: '🤖', title: 'AI Analysis', desc: 'Deepgram transcription + GPT-4o + Azure Speech scoring' },
          { icon: '📄', title: 'Bilingual Report', desc: 'Download a detailed FR/EN PDF with CEFR level and criteria' },
        ].map((f) => (
          <div key={f.title} className="rounded-xl border border-gray-200 bg-white p-6 shadow-sm">
            <div className="text-3xl mb-2">{f.icon}</div>
            <h3 className="font-semibold text-gray-800 mb-1">{f.title}</h3>
            <p className="text-sm text-gray-500">{f.desc}</p>
          </div>
        ))}
      </div>
    </div>
  )
}
