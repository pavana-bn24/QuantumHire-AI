import {
  Briefcase,
  LayoutDashboard,
  Sparkles,
  Users,
  Workflow,
} from 'lucide-react'
import { NavLink } from 'react-router-dom'

import { PIPELINE_STAGES } from '../../constants/pipeline.js'

const NAV_ITEMS = [
  { to: '/dashboard', label: 'Dashboard', icon: LayoutDashboard },
  { to: '/roles', label: 'Roles', icon: Briefcase },
  { to: '/candidates', label: 'Candidates', icon: Users },
]

const linkClasses = ({ isActive }) =>
  [
    'group flex items-center gap-3 rounded-xl px-3 py-2.5 text-sm font-medium transition',
    isActive
      ? 'bg-brand-600/20 text-white shadow-glow ring-1 ring-brand-500/40'
      : 'text-slate-400 hover:bg-white/5 hover:text-slate-100',
  ].join(' ')

export default function Sidebar() {
  return (
    <aside className="hidden w-64 shrink-0 flex-col border-r border-white/5 bg-ink-900/60 px-4 py-6 backdrop-blur lg:flex">
      <div className="flex items-center gap-3 px-1">
        <span className="grid h-10 w-10 place-items-center rounded-xl bg-gradient-to-br from-brand-500 to-accent-500 text-white shadow-glow">
          <Sparkles size={20} />
        </span>
        <div className="leading-tight">
          <p className="text-sm font-bold text-white">QuantumHire AI</p>
          <p className="text-xs text-slate-500">Recruiter cockpit</p>
        </div>
      </div>

      <nav className="mt-8 space-y-1">
        {NAV_ITEMS.map(({ to, label, icon: Icon }) => (
          <NavLink key={to} to={to} className={linkClasses}>
            <Icon size={18} />
            {label}
          </NavLink>
        ))}
      </nav>

      <div className="mt-8 rounded-2xl border border-white/5 bg-ink-850/70 p-4">
        <p className="flex items-center gap-2 text-xs font-semibold uppercase tracking-wider text-slate-400">
          <Workflow size={14} /> Pipeline
        </p>
        <ul className="mt-3 space-y-2">
          {PIPELINE_STAGES.map((stage, index) => (
            <li key={stage} className="flex items-center gap-2 text-xs text-slate-400">
              <span className="grid h-4 w-4 shrink-0 place-items-center rounded-full bg-white/5 text-[10px] font-semibold text-slate-500">
                {index + 1}
              </span>
              {stage}
            </li>
          ))}
        </ul>
      </div>

      <p className="mt-auto px-1 pt-6 text-[11px] leading-relaxed text-slate-600">
        One workflow: create a role, upload a resume, review the profile, run the AI evaluation,
        approve the recommendation, approve the skill test. Every step is recruiter-approved and
        recorded in Activity.
      </p>
    </aside>
  )
}
