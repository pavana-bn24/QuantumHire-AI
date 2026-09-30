/**
 * Recruitment pipeline definition.
 * Mirrors backend/app/core/constants.py - keep both in sync.
 */
export const PIPELINE_STAGES = [
  'New',
  'Under Review',
  'Skill Test',
  'Interview',
  'Selected',
  'Rejected',
]

/** Tailwind classes per stage so badges and columns stay consistent. */
export const STAGE_STYLES = {
  New: {
    badge: 'border-sky-500/30 bg-sky-500/10 text-sky-300',
    bar: 'bg-sky-400',
    dot: 'bg-sky-400',
  },
  'Under Review': {
    badge: 'border-amber-500/30 bg-amber-500/10 text-amber-300',
    bar: 'bg-amber-400',
    dot: 'bg-amber-400',
  },
  'Skill Test': {
    badge: 'border-violet-500/30 bg-violet-500/10 text-violet-300',
    bar: 'bg-violet-400',
    dot: 'bg-violet-400',
  },
  Interview: {
    badge: 'border-indigo-500/30 bg-indigo-500/10 text-indigo-300',
    bar: 'bg-indigo-400',
    dot: 'bg-indigo-400',
  },
  Selected: {
    badge: 'border-emerald-500/30 bg-emerald-500/10 text-emerald-300',
    bar: 'bg-emerald-400',
    dot: 'bg-emerald-400',
  },
  Rejected: {
    badge: 'border-rose-500/30 bg-rose-500/10 text-rose-300',
    bar: 'bg-rose-400',
    dot: 'bg-rose-400',
  },
}

export const DEFAULT_STAGE_STYLE = {
  badge: 'border-slate-500/30 bg-slate-500/10 text-slate-300',
  bar: 'bg-slate-400',
  dot: 'bg-slate-400',
}

/** Stages that only accept candidates as a terminal state. */
export const TERMINAL_STAGES = ['Selected', 'Rejected']

export const getStageStyle = (stage) => STAGE_STYLES[stage] ?? DEFAULT_STAGE_STYLE
