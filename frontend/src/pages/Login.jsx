import { ArrowRight, Lock, Mail, Sparkles, User } from 'lucide-react'
import { useState } from 'react'
import { Navigate, useNavigate } from 'react-router-dom'

import { useAuth } from '../context/AuthContext.jsx'

export default function Login() {
  const { isAuthenticated, login } = useAuth()
  const navigate = useNavigate()
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [error, setError] = useState('')
  const [submitting, setSubmitting] = useState(false)

  if (isAuthenticated) {
    return <Navigate to="/dashboard" replace />
  }

  const handleSubmit = async (event) => {
    event.preventDefault()

    if (!email.trim() || !password.trim()) {
      setError('Enter both an email address and a password.')
      return
    }

    setSubmitting(true)
    setError('')
    try {
      // Real JWT login: the API rejects unknown accounts with 401.
      await login({ email, password })
      navigate('/dashboard', { replace: true })
    } catch (loginError) {
      setError(loginError?.message ?? 'Sign in failed. Is the API running on port 8000?')
    } finally {
      setSubmitting(false)
    }
  }

  return (
    <div className="grid min-h-screen lg:grid-cols-2">
      {/* Brand panel */}
      <div className="relative hidden flex-col justify-between border-r border-white/5 bg-ink-900/50 p-12 lg:flex">
        <div className="flex items-center gap-3">
          <span className="grid h-11 w-11 place-items-center rounded-xl bg-gradient-to-br from-brand-500 to-accent-500 text-white shadow-glow">
            <Sparkles size={22} />
          </span>
          <div>
            <p className="font-bold text-white">QuantumHire AI</p>
            <p className="text-xs text-slate-500">Recruiter workflow automation</p>
          </div>
        </div>

        <div className="max-w-md">
          <h1 className="text-4xl font-extrabold leading-tight text-white">
            Hire AI full-stack engineers with a pipeline that runs itself.
          </h1>
          <p className="mt-4 text-sm leading-relaxed text-slate-400">
            Track every candidate from application to offer, keep requirement coverage visible and
            automate the repetitive recruiter work - all in one workspace.
          </p>

          <ul className="mt-8 space-y-3 text-sm text-slate-400">
            {[
              'Six-stage pipeline with live metrics',
              'Upload a PDF resume and get a structured profile',
              'AI evaluation and skill tests that stay recruiter-approved',
            ].map((item) => (
              <li key={item} className="flex items-center gap-2">
                <span className="h-1.5 w-1.5 rounded-full bg-accent-400" />
                {item}
              </li>
            ))}
          </ul>
        </div>

        <p className="text-xs text-slate-600">
          QuantumHire AI · resume intake, profile review, evaluation and skill tests
        </p>
      </div>

      {/* Form panel */}
      <div className="flex items-center justify-center px-6 py-12">
        <form onSubmit={handleSubmit} className="w-full max-w-sm">
          <div className="mb-8 lg:hidden">
            <span className="grid h-11 w-11 place-items-center rounded-xl bg-gradient-to-br from-brand-500 to-accent-500 text-white">
              <Sparkles size={22} />
            </span>
          </div>

          <h2 className="text-2xl font-bold text-white">Recruiter sign in</h2>
          <p className="mt-1.5 text-sm text-slate-400">
            Continue to your QuantumHire workspace.
          </p>

          <div className="mt-8 space-y-4">
            <div>
              <label className="label" htmlFor="email">
                Email
              </label>
              <div className="relative">
                <Mail
                  size={16}
                  className="pointer-events-none absolute left-3 top-1/2 -translate-y-1/2 text-slate-500"
                />
                <input
                  id="email"
                  type="email"
                  className="input pl-9"
                  value={email}
                  onChange={(event) => setEmail(event.target.value)}
                  placeholder="you@company.com"
                  autoComplete="email"
                />
              </div>
            </div>

            <div>
              <label className="label" htmlFor="password">
                Password
              </label>
              <div className="relative">
                <Lock
                  size={16}
                  className="pointer-events-none absolute left-3 top-1/2 -translate-y-1/2 text-slate-500"
                />
                <input
                  id="password"
                  type="password"
                  className="input pl-9"
                  value={password}
                  onChange={(event) => setPassword(event.target.value)}
                  placeholder="••••••••"
                  autoComplete="current-password"
                />
              </div>
            </div>
          </div>

          {error ? (
            <p className="mt-4 rounded-xl border border-rose-500/30 bg-rose-500/10 px-3 py-2 text-xs text-rose-300">
              {error}
            </p>
          ) : null}

          <button type="submit" className="btn-primary mt-6 w-full" disabled={submitting}>
            {submitting ? 'Signing in...' : 'Sign in'} {!submitting ? <ArrowRight size={16} /> : null}
          </button>

          <p className="mt-4 flex items-center gap-2 rounded-xl border border-white/5 bg-white/[0.03] px-3 py-2 text-xs text-slate-400">
            <User size={14} className="shrink-0 text-slate-500" />
            Accounts are seeded by the backend from SEED_ADMIN_EMAIL / SEED_ADMIN_PASSWORD.
            Credentials are verified by the API (JWT, PBKDF2-hashed passwords).
          </p>
        </form>
      </div>
    </div>
  )
}
