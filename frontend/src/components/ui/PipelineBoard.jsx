import { ArrowRight, Inbox } from 'lucide-react'

import { PIPELINE_STAGES, getStageStyle } from '../../constants/pipeline.js'
import { EmptyState } from './index.jsx'

const initials = (name = '') =>
  name
    .split(' ')
    .filter(Boolean)
    .slice(0, 2)
    .map((part) => part[0]?.toUpperCase())
    .join('') || '?'

/**
 * Read-only pipeline board: one column per stage, candidates shown as cards.
 * Column counts come straight from the dashboard summary so the board matches
 * the headline metrics even when only a subset of candidates is loaded.
 */
export default function PipelineBoard({ summary, candidates = [], loading }) {
  const countsByStage = Object.fromEntries(
    (summary?.pipeline ?? []).map((entry) => [entry.stage, entry.count]),
  )

  const totalCandidates = summary?.total_candidates ?? candidates.length
  const total = totalCandidates > 0 ? totalCandidates : 1

  return (
    <div className="card">
      <div className="mb-4 flex flex-wrap items-center justify-between gap-2">
        <div>
          <h2 className="text-sm font-semibold text-white">Recruitment Pipeline</h2>
          <p className="text-xs text-slate-500">
            Candidate flow across all six workflow stages
          </p>
        </div>
        <span className="chip">
          <Inbox size={12} /> {summary?.total_candidates ?? candidates.length} in pipeline
        </span>
      </div>

      <div className="grid gap-3 md:grid-cols-3 xl:grid-cols-6">
        {PIPELINE_STAGES.map((stage) => {
          const style = getStageStyle(stage)
          const count = countsByStage[stage] ?? 0
          const share = Math.round((count / total) * 100)
          const stageCandidates = candidates.filter((item) => item.stage === stage).slice(0, 3)

          return (
            <div
              key={stage}
              className="flex flex-col rounded-xl border border-white/5 bg-ink-950/50 p-3"
            >
              <div className="flex items-center justify-between gap-2">
                <span className="flex items-center gap-1.5 text-xs font-semibold text-slate-200">
                  <span className={`h-1.5 w-1.5 rounded-full ${style.dot}`} />
                  {stage}
                </span>
                <span className="text-sm font-bold tabular-nums text-white">
                  {loading ? '–' : count}
                </span>
              </div>

              <div className="mt-2 h-1.5 overflow-hidden rounded-full bg-white/5">
                <div
                  className={`h-full rounded-full ${style.bar} transition-all`}
                  style={{ width: loading ? '0%' : `${share}%` }}
                />
              </div>

              <div className="mt-3 space-y-2">
                {stageCandidates.map((candidate) => (
                  <div
                    key={candidate.id}
                    className="flex items-center gap-2 rounded-lg border border-white/5 bg-white/[0.03] px-2 py-1.5"
                  >
                    <span className="grid h-6 w-6 shrink-0 place-items-center rounded-full bg-brand-600/25 text-[10px] font-bold text-brand-200">
                      {initials(candidate.name)}
                    </span>
                    <span className="truncate text-[11px] text-slate-300">{candidate.name}</span>
                  </div>
                ))}

                {!loading && stageCandidates.length === 0 ? (
                  <p className="rounded-lg border border-dashed border-white/5 px-2 py-3 text-center text-[11px] text-slate-600">
                    No candidates
                  </p>
                ) : null}
              </div>
            </div>
          )
        })}
      </div>

      {!loading && (summary?.total_candidates ?? 0) === 0 ? (
        <div className="mt-4">
          <EmptyState
            icon={ArrowRight}
            title="Pipeline is empty"
            description="Add a candidate to see it move through New → Under Review → Skill Test → Interview → Selected."
          />
        </div>
      ) : null}
    </div>
  )
}
