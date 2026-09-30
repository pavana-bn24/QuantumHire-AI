import { AlertTriangle, RefreshCw } from 'lucide-react'

import { getStageStyle } from '../../constants/pipeline.js'

/** Small presentational building blocks reused across pages. */

export function PageHeader({ title, subtitle, actions, icon: Icon }) {
  return (
    <div className="mb-6 flex flex-wrap items-end justify-between gap-4">
      <div className="flex items-start gap-3">
        {Icon ? (
          <span className="grid h-11 w-11 place-items-center rounded-xl bg-brand-600/20 text-brand-300 ring-1 ring-brand-500/30">
            <Icon size={20} />
          </span>
        ) : null}
        <div>
          <h1 className="text-xl font-bold text-white md:text-2xl">{title}</h1>
          {subtitle ? <p className="mt-1 text-sm text-slate-400">{subtitle}</p> : null}
        </div>
      </div>
      {actions ? <div className="flex items-center gap-2">{actions}</div> : null}
    </div>
  )
}

export function StatCard({ label, value, icon: Icon, hint, accent = 'brand', loading }) {
  const accents = {
    brand: 'from-brand-500/25 to-brand-600/5 text-brand-300 ring-brand-500/30',
    amber: 'from-amber-500/25 to-amber-600/5 text-amber-300 ring-amber-500/30',
    violet: 'from-violet-500/25 to-violet-600/5 text-violet-300 ring-violet-500/30',
    indigo: 'from-indigo-500/25 to-indigo-600/5 text-indigo-300 ring-indigo-500/30',
    emerald: 'from-emerald-500/25 to-emerald-600/5 text-emerald-300 ring-emerald-500/30',
    rose: 'from-rose-500/25 to-rose-600/5 text-rose-300 ring-rose-500/30',
  }
  const accentClasses = accents[accent] ?? accents.brand

  return (
    <div className="card card-hover animate-fade-up">
      <div className="flex items-start justify-between gap-3">
        <p className="text-xs font-semibold uppercase tracking-wider text-slate-400">{label}</p>
        {Icon ? (
          <span
            className={`grid h-9 w-9 place-items-center rounded-lg bg-gradient-to-br ring-1 ${accentClasses}`}
          >
            <Icon size={17} />
          </span>
        ) : null}
      </div>
      <p className="mt-3 text-3xl font-bold tabular-nums text-white">
        {loading ? <span className="inline-block h-8 w-12 animate-pulse rounded bg-white/10" /> : (value ?? 0)}
      </p>
      {hint ? <p className="mt-1.5 text-xs text-slate-500">{hint}</p> : null}
    </div>
  )
}

export function StageBadge({ stage, className = '' }) {
  const style = getStageStyle(stage)
  return (
    <span
      className={`inline-flex items-center gap-1.5 rounded-full border px-2.5 py-1 text-xs font-semibold ${style.badge} ${className}`}
    >
      <span className={`h-1.5 w-1.5 rounded-full ${style.dot}`} />
      {stage}
    </span>
  )
}

export function LoadingCard({ label = 'Loading...' }) {
  return (
    <div className="card flex items-center gap-3 text-sm text-slate-400">
      <RefreshCw size={16} className="animate-spin text-brand-400" />
      {label}
    </div>
  )
}

export function ErrorCard({ message, onRetry }) {
  return (
    <div className="card border-rose-500/20 bg-rose-500/5">
      <p className="flex items-center gap-2 text-sm font-semibold text-rose-300">
        <AlertTriangle size={16} /> {message}
      </p>
      <p className="mt-1 text-xs text-slate-400">
        Make sure the FastAPI backend is running and the MongoDB service is started.
      </p>
      {onRetry ? (
        <button type="button" onClick={onRetry} className="btn-ghost mt-3">
          <RefreshCw size={14} /> Retry
        </button>
      ) : null}
    </div>
  )
}

export function EmptyState({ title, description, icon: Icon }) {
  return (
    <div className="card flex flex-col items-center gap-2 py-10 text-center">
      {Icon ? <Icon size={22} className="text-slate-500" /> : null}
      <p className="text-sm font-semibold text-slate-200">{title}</p>
      {description ? <p className="max-w-sm text-xs text-slate-500">{description}</p> : null}
    </div>
  )
}
