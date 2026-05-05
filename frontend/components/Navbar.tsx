'use client'

import Link from 'next/link'
import { useAuth } from '@/hooks/useAuth'
import { useRouter } from 'next/navigation'

export function Navbar() {
  const { user, loading, logout } = useAuth()
  const router = useRouter()

  async function handleLogout() {
    await logout()
    router.push('/')
  }

  return (
    <nav className="border-b border-gray-200 bg-white shadow-sm">
      <div className="mx-auto flex max-w-5xl items-center justify-between px-4 py-3">
        <Link href="/" className="font-bold text-brand-700 text-lg">
          CEFR Evaluator
        </Link>

        <div className="flex items-center gap-4">
          {!loading && user ? (
            <>
              <Link
                href="/dashboard"
                className="text-sm text-gray-600 hover:text-brand-700 transition-colors"
              >
                Dashboard
              </Link>
              <Link
                href="/evaluations/new"
                className="rounded-md bg-brand-600 px-3 py-1.5 text-sm font-medium text-white hover:bg-brand-700 transition-colors"
              >
                New Evaluation
              </Link>
              <div className="flex items-center gap-2">
                {user.picture_url && (
                  // eslint-disable-next-line @next/next/no-img-element
                  <img
                    src={user.picture_url}
                    alt={user.name}
                    className="h-8 w-8 rounded-full object-cover"
                  />
                )}
                <span className="text-sm text-gray-700 hidden sm:block">{user.name}</span>
              </div>
              <button
                onClick={handleLogout}
                className="text-sm text-gray-500 hover:text-red-600 transition-colors"
              >
                Sign out
              </button>
            </>
          ) : !loading ? (
            <a
              href="/api/auth/google"
              className="rounded-md bg-brand-600 px-3 py-1.5 text-sm font-medium text-white hover:bg-brand-700 transition-colors"
            >
              Sign in
            </a>
          ) : null}
        </div>
      </div>
    </nav>
  )
}
