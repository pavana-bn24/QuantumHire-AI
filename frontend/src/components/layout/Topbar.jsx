import { Activity, LogOut, RefreshCw, Search } from 'lucide-react'
import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'

import { getHealth } from '../../api/quantumhire.js'
import { useAuth } from '../../context/AuthContext.jsx'

const STATUS_STYLES = {
  ok: 'border-emerald-500/30 bg-emerald-500/10 text-emerald-300',
  error: 'border-rose-500/30 bg-rose-500/10 text-rose-300',
  loading: 'border-slate-500/30 bg-slate-500/10 text-slate-300',
}

export default function Topbar() {
  const { session, logout } = useAuth()
  const navigate = useNavigate()
  const [status, setStatus] = useState('loading')
  const [term, setTerm] = useState('')

  useEffect(() => {
    let cancelled = false

    getHealth()
      .then((data) => {
        if (!cancelled) setStatus(data?.status === 'ok' ? 'ok' : 'error')
      })
      .catch(() => {
        if (!cancelled) setStatus('error')
      })

    return () => {
      cancelled = true
    }
  }, [])

  const label =
    status === 'ok' ? 'API online' : status === 'error' ? 'API offline' : 'Checking API...'

  return (
    <header className="sticky top-0 z-20 border-b border-white/5 bg-ink-950/80 px-5 py-3.5 backdrop-blur md:px-8">
      <div className="mx-auto flex w-full max-w-7xl items-center gap-3">
        <div className="relative hidden flex-1 md:block">
          <Search size={16} className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-500" />
          <form
            role="search"
            onSubmit={(event) => {
              event.preventDefault()
              const trimmed = term.trim()
              navigate(
                trimmed ? `/candidates?search=${encodeURIComponent(trimmed)}` : '/candidates',
              )
            }}
          >
            <input
              type="search"
              value={term}
              onChange={(event) => setTerm(event.target.value)}
              placeholder="Search candidates, skills or roles..."
              className="input pl-9"
              aria-label="Global search"
            />
          </form>
        </div>

        <span
          className={`chip ml-auto ${STATUS_STYLES[status]}`}
          title="Live check of GET /api/health"
        >
          {status === 'loading' ? (
            <RefreshCw size={12} className="animate-spin" />
          ) : (
            <Activity size={12} />
          )}
          {label}
        </span>

        <div className="flex items-center gap-3 border-l border-white/5 pl-3">
          <div className="hidden text-right leading-tight sm:block">
            <p className="text-sm font-semibold text-white">{session?.name}</p>
            <p className="text-xs text-slate-500">{session?.role}</p>
          </div>
          <span className="grid h-9 w-9 place-items-center rounded-full bg-gradient-to-br from-brand-500 to-accent-500 text-sm font-bold text-white">
            {session?.name?.charAt(0)?.toUpperCase() ?? 'Q'}
          </span>
          <button
            type="button"
            onClick={logout}
            className="rounded-lg border border-white/10 bg-white/5 p-2 text-slate-300 transition hover:border-rose-500/40 hover:text-rose-300"
            title="Sign out"
          >
            <LogOut size={16} />
          </button>
        </div>
      </div>
    </header>
  )
}
