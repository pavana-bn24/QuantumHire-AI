import {
  Briefcase,
  CalendarCheck,
  ClipboardList,
  FlaskConical,
  LayoutDashboard,
  Plus,
  RefreshCw,
  TrendingUp,
  Users,
  UserCheck,
  UserX,
} from 'lucide-react'
import { Link } from 'react-router-dom'

import { getCandidates, getDashboardSummary, getRoles } from '../api/quantumhire.js'
import PipelineBoard from '../components/ui/PipelineBoard.jsx'
import {
  EmptyState,
  ErrorCard,
  LoadingCard,
  PageHeader,
  StageBadge,
  StatCard,
} from '../components/ui/index.jsx'
import { useAuth } from '../context/AuthContext.jsx'
import { useApiResource } from '../hooks/useApiResource.js'

const formatDate = (value) => {
  if (!value) return '—'
  const date = new Date(value)
  return Number.isNaN(date.getTime())
    ? '—'
    : date.toLocaleDateString(undefined, { day: '2-digit', month: 'short' })
}

export default function Dashboard() {
  const { session } = useAuth()
  const summary = useApiResource(getDashboardSummary, [])
  const candidates = useApiResource(() => getCandidates({ limit: 50 }), [])
  const roles = useApiResource(getRoles, [])

  const stats = summary.data
  const loading = summary.loading
  const recent = (candidates.data ?? []).slice(0, 6)

  const reloadAll = () => {
    summary.reload()
    candidates.reload()
    roles.reload()
  }

  return (
    <div className="space-y-6">
      <PageHeader
        icon={LayoutDashboard}
        title={`Welcome back, ${session?.name ?? 'Recruiter'}`}
        subtitle="Live snapshot of your hiring pipeline and open engineering roles."
        actions={
          <>
            <Link to="/roles?create=1" className="btn-primary">
              <Plus size={15} /> Create Job Role
            </Link>
            <button type="button" onClick={reloadAll} className="btn-ghost">
              <RefreshCw size={15} className={loading ? 'animate-spin' : ''} /> Refresh
            </button>
          </>
        }
      />

      {summary.error ? (
        <ErrorCard message={summary.error} onRetry={summary.reload} />
      ) : (
        <>
          <section className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
            <StatCard
              label="Total Candidates"
              value={stats?.total_candidates}
              icon={Users}
              accent="brand"
              hint="Every candidate across all stages"
              loading={loading}
            />
            <StatCard
              label="Under Review"
              value={stats?.under_review}
              icon={ClipboardList}
              accent="amber"
              hint="Awaiting recruiter screening"
              loading={loading}
            />
            <StatCard
              label="Skill Tests"
              value={stats?.skill_tests}
              icon={TrendingUp}
              accent="violet"
              hint="In the skill assessment stage"
              loading={loading}
            />
            <StatCard
              label="Interviews"
              value={stats?.interviews}
              icon={CalendarCheck}
              accent="indigo"
              hint="Scheduled or in progress"
              loading={loading}
            />
          </section>

          <section className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
            <StatCard
              label="Selected"
              value={stats?.selected}
              icon={UserCheck}
              accent="emerald"
              hint="Offers approved"
              loading={loading}
            />
            <StatCard
              label="Rejected"
              value={stats?.rejected}
              icon={UserX}
              accent="rose"
              hint="Closed out of the pipeline"
              loading={loading}
            />
            <StatCard
              label="New Applicants"
              value={stats?.new}
              icon={Users}
              accent="brand"
              hint="Fresh applications awaiting triage"
              loading={loading}
            />
            <StatCard
              label="Active Roles"
              value={stats?.active_roles}
              icon={Briefcase}
              accent="indigo"
              hint={`${stats?.total_roles ?? 0} role(s) configured`}
              loading={loading}
            />
          </section>

          {/* Workflow queues - what the recruiter must action next (no ranking). */}
          <section className="grid gap-4 sm:grid-cols-2">
            <StatCard
              label="Awaiting Review"
              value={stats?.awaiting_review}
              icon={ClipboardList}
              accent="amber"
              hint="Uploaded profiles not yet approved by a recruiter"
              loading={loading}
            />
            <StatCard
              label="Awaiting Skill Test"
              value={stats?.awaiting_skill_test}
              icon={FlaskConical}
              accent="violet"
              hint="Approved evaluations whose skill test still needs approval"
              loading={loading}
            />
          </section>
        </>
      )}

      <PipelineBoard
        summary={summary.data}
        candidates={candidates.data ?? []}
        loading={summary.loading}
      />
      <DashboardLowerPanels candidates={candidates} roles={roles} recent={recent} />
    </div>
  )
}

/** Recent candidates + open roles + roadmap hints. */
function DashboardLowerPanels({ candidates, roles, recent }) {
  return (
    <div className="grid gap-6 lg:grid-cols-3">
      <div className="card lg:col-span-2">
        <div className="mb-4 flex items-center justify-between">
          <h2 className="text-sm font-semibold text-white">Recent Candidates</h2>
          <Link to="/candidates" className="text-xs font-semibold text-brand-300 hover:text-brand-200">
            View all →
          </Link>
        </div>

        {candidates.loading ? (
          <LoadingCard label="Loading candidates..." />
        ) : candidates.error ? (
          <ErrorCard message={candidates.error} onRetry={candidates.reload} />
        ) : recent.length === 0 ? (
          <EmptyState
            icon={Users}
            title="No candidates yet"
            description="Candidates added to a role appear here with their current pipeline stage."
          />
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-left text-sm">
              <thead>
                <tr className="text-xs uppercase tracking-wider text-slate-500">
                  <th className="pb-2 font-semibold">Candidate</th>
                  <th className="pb-2 font-semibold">Stage</th>
                  <th className="pb-2 font-semibold">Experience</th>
                  <th className="pb-2 font-semibold">Added</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-white/5">
                {recent.map((candidate) => (
                  <tr key={candidate.id} className="transition hover:bg-white/[0.03]">
                    <td className="py-2.5">
                      <Link
                        to={`/candidates/${candidate.id}`}
                        className="font-medium text-slate-100 hover:text-brand-300"
                      >
                        {candidate.name}
                      </Link>
                      <p className="text-xs text-slate-500">{candidate.role_title ?? '—'}</p>
                    </td>
                    <td className="py-2.5">
                      <StageBadge stage={candidate.stage} />
                    </td>
                    <td className="py-2.5 text-slate-400">
                      {candidate.experience_years != null
                        ? `${candidate.experience_years} yrs`
                        : '—'}
                    </td>
                    <td className="py-2.5 text-slate-400">{formatDate(candidate.created_at)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>

      <div className="space-y-6">
        <div className="card">
          <div className="mb-4 flex items-center justify-between">
            <h2 className="text-sm font-semibold text-white">Open Roles</h2>
            <Link to="/roles" className="text-xs font-semibold text-brand-300 hover:text-brand-200">
              Manage →
            </Link>
          </div>

          {roles.loading ? (
            <LoadingCard label="Loading roles..." />
          ) : (roles.data ?? []).length === 0 ? (
            <p className="text-xs text-slate-500">No roles configured yet.</p>
          ) : (
            <ul className="space-y-3">
              {(roles.data ?? []).slice(0, 4).map((role) => (
                <li key={role.id} className="rounded-xl border border-white/5 bg-white/[0.03] p-3">
                  <p className="text-sm font-semibold text-slate-100">{role.title}</p>
                  <p className="mt-0.5 text-xs text-slate-500">
                    {role.department} · {role.location}
                  </p>
                  <p className="mt-2 text-xs text-slate-400">
                    {role.requirements.length} requirement areas
                  </p>
                </li>
              ))}
            </ul>
          )}
        </div>

        <div className="card border-dashed border-white/10 bg-ink-900/40">
          <h2 className="section-title">How automation helps</h2>
          <ul className="mt-3 space-y-2 text-xs text-slate-400">
            <li>· Resume uploaded → profile queued for your review</li>
            <li>· Profile approved → AI evaluation (evidence only, no scores)</li>
            <li>· Evaluation approved → skill test drafted automatically</li>
            <li>· Skill test approved → stage move + outbound webhook</li>
          </ul>
          <p className="mt-3 text-[11px] text-slate-600">
            Every step is recorded on the candidate&apos;s Activity timeline. Automation drafts -
            you decide.
          </p>
        </div>
      </div>
    </div>
  )
}
