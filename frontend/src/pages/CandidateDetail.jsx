import {
  Activity,
  ArrowLeft,
  Award,
  Briefcase,
  CalendarDays,
  ClipboardList,
  FileText,
  Mail,
  MapPin,
  NotebookPen,
  ScrollText,
  Sparkles,
  TrendingUp,
  User,
} from 'lucide-react'
import { useState } from 'react'
import { Link, useParams } from 'react-router-dom'

import { getCandidate, getCandidateEvents, getRoles, updateCandidateStage } from '../api/quantumhire.js'
import EvaluationTab from '../components/candidate/EvaluationTab.jsx'
import ProfileForm from '../components/candidate/ProfileForm.jsx'
import SkillTestTab from '../components/candidate/SkillTestTab.jsx'
import { EmptyState, ErrorCard, LoadingCard, StageBadge } from '../components/ui/index.jsx'
import { PIPELINE_STAGES } from '../constants/pipeline.js'
import { useApiResource } from '../hooks/useApiResource.js'

const formatDateTime = (value) => {
  if (!value) return '—'
  const date = new Date(value)
  return Number.isNaN(date.getTime()) ? '—' : date.toLocaleString()
}

const TABS = [
  { key: 'overview', label: 'Overview', icon: User },
  { key: 'profile', label: 'Resume / Profile', icon: FileText },
  { key: 'evaluation', label: 'AI Evaluation', icon: Sparkles },
  { key: 'skilltest', label: 'Skill Test', icon: ClipboardList },
  { key: 'activity', label: 'Activity', icon: Activity },
]

export default function CandidateDetail() {
  const { candidateId } = useParams()
  const candidate = useApiResource(() => getCandidate(candidateId), [candidateId])
  const roles = useApiResource(getRoles, [])
  const [activeTab, setActiveTab] = useState('overview')
  const [stageSaving, setStageSaving] = useState(false)
  const [stageError, setStageError] = useState('')

  /** Recruiter stage change - persisted by the backend (+ workflow event). */
  const handleStageChange = async (nextStage) => {
    const current = candidate.data?.stage
    if (!nextStage || nextStage === current || stageSaving) return
    setStageSaving(true)
    setStageError('')
    try {
      await updateCandidateStage(candidateId, nextStage)
      await candidate.reload()
    } catch (err) {
      setStageError(err.message ?? 'Could not update the stage.')
    } finally {
      setStageSaving(false)
    }
  }

  if (candidate.loading) {
    return <LoadingCard label="Loading candidate..." />
  }

  if (candidate.error) {
    return (
      <div className="space-y-4">
        <BackLink />
        <ErrorCard message={candidate.error} onRetry={candidate.reload} />
      </div>
    )
  }

  const data = candidate.data
  const role = (roles.data ?? []).find((item) => item.id === data?.role_id) ?? null
  const currentIndex = PIPELINE_STAGES.indexOf(data?.stage)

  return (
    <div className="space-y-6">
      <BackLink />

      <div className="card animate-fade-up">
        <div className="flex flex-wrap items-start justify-between gap-4">
          <div className="flex items-start gap-4">
            <span className="grid h-14 w-14 place-items-center rounded-2xl bg-gradient-to-br from-brand-500 to-accent-500 text-lg font-bold text-white">
              {data?.name
                ?.split(' ')
                .slice(0, 2)
                .map((part) => part[0]?.toUpperCase())
                .join('')}
            </span>
            <div>
              <h1 className="text-xl font-bold text-white md:text-2xl">{data?.name}</h1>
              <p className="mt-1 text-sm text-slate-400">{data?.role_title ?? 'Unassigned role'}</p>
              <div className="mt-3 flex flex-wrap gap-2 text-xs text-slate-400">
                <span className="chip">
                  <Mail size={12} /> {data?.email}
                </span>
                {data?.location ? (
                  <span className="chip">
                    <MapPin size={12} /> {data.location}
                  </span>
                ) : null}
                {data?.experience_years != null ? (
                  <span className="chip">
                    <TrendingUp size={12} /> {data.experience_years} yrs experience
                  </span>
                ) : null}
                <span className="chip">
                  <CalendarDays size={12} /> Applied {formatDateTime(data?.created_at)}
                </span>
              </div>
            </div>
          </div>

          <div className="text-right">
            <p className="text-xs uppercase tracking-wider text-slate-500">Current stage</p>
            <div className="mt-2">
              <StageBadge stage={data?.stage} />
            </div>
            <label className="mt-2 block">
              <span className="sr-only">Change pipeline stage</span>
              <select
                className="input w-auto min-w-40 text-xs"
                aria-label="Change pipeline stage"
                value={data?.stage ?? ''}
                disabled={stageSaving}
                onChange={(event) => handleStageChange(event.target.value)}
              >
                {PIPELINE_STAGES.map((stage) => (
                  <option key={stage} value={stage}>
                    {stage}
                  </option>
                ))}
              </select>
            </label>
            {stageError ? (
              <p role="alert" className="mt-1 max-w-[220px] text-[11px] text-rose-300">
                {stageError}
              </p>
            ) : null}
            <p className="mt-2 text-xs text-slate-500">
              Step {(currentIndex >= 0 ? currentIndex : 0) + 1} of {PIPELINE_STAGES.length}
            </p>
          </div>
        </div>

        <div className="mt-6 grid gap-2 sm:grid-cols-3 xl:grid-cols-6">
          {PIPELINE_STAGES.map((stage, index) => {
            const reached = currentIndex >= index
            return (
              <div
                key={stage}
                className={`rounded-xl border px-3 py-2 text-xs font-medium ${
                  reached
                    ? 'border-brand-500/40 bg-brand-600/15 text-brand-100'
                    : 'border-white/5 bg-white/[0.02] text-slate-500'
                }`}
              >
                {stage}
              </div>
            )
          })}
        </div>
      </div>

      {/* Tabs: Overview / Resume & Profile / AI Evaluation / Skill Test / Activity */}
      <div className="flex flex-wrap gap-2 border-b border-white/5 pb-3">
        {TABS.map(({ key, label, icon: Icon }) => (
          <button
            key={key}
            type="button"
            onClick={() => setActiveTab(key)}
            className={
              activeTab === key
                ? 'inline-flex items-center gap-2 rounded-xl border border-brand-500/40 bg-brand-600/20 px-3.5 py-2 text-xs font-semibold text-white'
                : 'inline-flex items-center gap-2 rounded-xl border border-white/10 bg-white/5 px-3.5 py-2 text-xs font-medium text-slate-400 transition hover:border-brand-500/30 hover:text-slate-200'
            }
          >
            <Icon size={14} /> {label}
          </button>
        ))}
      </div>

      {activeTab === 'profile' ? <ProfileTab data={data} onSaved={candidate.reload} /> : null}
      {activeTab === 'evaluation' ? (
        <EvaluationTab candidate={data} onChanged={candidate.reload} />
      ) : null}
      {activeTab === 'skilltest' ? (
        <SkillTestTab candidate={data} onChanged={candidate.reload} />
      ) : null}
      {activeTab === 'activity' ? <ActivityTab data={data} /> : null}

      {activeTab === 'overview' ? (
      <div className="grid gap-6 lg:grid-cols-3">
        <div className="space-y-6 lg:col-span-2">
          <div className="card">
            <h2 className="text-sm font-semibold text-white">Skills</h2>
            {data?.skills?.length ? (
              <div className="mt-3 flex flex-wrap gap-2">
                {data.skills.map((skill) => (
                  <span key={skill} className="chip">
                    {skill}
                  </span>
                ))}
              </div>
            ) : (
              <p className="mt-2 text-xs text-slate-500">No skills recorded.</p>
            )}
          </div>

          <div className="card">
            <h2 className="flex items-center gap-2 text-sm font-semibold text-white">
              <NotebookPen size={15} /> Recruiter Notes
            </h2>
            <p className="mt-3 text-sm leading-relaxed text-slate-400">
              {data?.notes || 'No notes yet.'}
            </p>
          </div>

          <div className="card">
            <h2 className="flex items-center gap-2 text-sm font-semibold text-white">
              <ScrollText size={15} /> Resume Evidence
            </h2>

            {data?.has_resume ? (
              <>
                <p className="mt-3 truncate text-sm text-slate-200">{data.resume_filename}</p>
                <p className="mt-1 text-xs text-slate-500">
                  {data.resume_page_count} page(s) · {data.resume_word_count} words ·{' '}
                  {data.resume_char_count} characters
                </p>
                <div className="mt-3 flex flex-wrap gap-2">
                  {data.profile_reviewed ? (
                    <span className="chip border-emerald-500/30 bg-emerald-500/10 text-emerald-300">
                      Profile approved
                    </span>
                  ) : (
                    <span className="chip border-amber-500/30 bg-amber-500/10 text-amber-300">
                      Awaiting recruiter review
                    </span>
                  )}
                  <span className="chip">
                    {data.ai_provider}/{data.ai_model}
                  </span>
                </div>
                <p className="mt-3 text-xs text-slate-500">
                  Open the <strong className="font-semibold text-slate-300">Resume / Profile</strong>{' '}
                  tab to review and approve the extracted profile.
                </p>
              </>
            ) : (
              <p className="mt-2 text-xs text-slate-500">
                No resume uploaded for this candidate yet. Use “Upload Resume” on the Candidates
                page to extract a profile automatically.
              </p>
            )}
          </div>
        </div>

        <div className="space-y-6">
          <div className="card">
            <h2 className="flex items-center gap-2 text-sm font-semibold text-white">
              <Briefcase size={15} /> Role Context
            </h2>

            {roles.loading ? (
              <p className="mt-3 text-xs text-slate-500">Loading role...</p>
            ) : !role ? (
              <p className="mt-3 text-xs text-slate-500">
                This candidate is not linked to a configured role yet.
              </p>
            ) : (
              <>
                <p className="mt-3 text-sm font-semibold text-slate-100">{role.title}</p>
                <p className="text-xs text-slate-500">
                  {role.department} · {role.location}
                </p>
                <ul className="mt-4 space-y-2">
                  {role.requirements.slice(0, 8).map((requirement) => (
                    <li
                      key={requirement.key}
                      className="flex items-center justify-between gap-2 text-xs text-slate-400"
                    >
                      <span>{requirement.label}</span>
                      <span className="tabular-nums text-slate-600">{requirement.weight}</span>
                    </li>
                  ))}
                </ul>
                <Link to="/roles" className="btn-ghost mt-4 w-full">
                  View full requirement matrix
                </Link>
              </>
            )}
          </div>

          <div className="card">
            <h2 className="text-sm font-semibold text-white">Meta</h2>
            <dl className="mt-3 space-y-2 text-xs">
              {[
                ['Source', data?.source ?? '—'],
                ['Candidate ID', data?.id ?? '—'],
                ['Last updated', formatDateTime(data?.updated_at)],
              ].map(([label, value]) => (
                <div key={label} className="flex items-start justify-between gap-3">
                  <dt className="text-slate-500">{label}</dt>
                  <dd className="max-w-[60%] truncate text-right text-slate-300">{value}</dd>
                </div>
              ))}
            </dl>
          </div>

          <div className="card">
            <h2 className="flex items-center gap-2 text-sm font-semibold text-white">
              <Sparkles size={15} /> Hiring workflow
            </h2>
            <ol className="mt-3 space-y-2 text-xs text-slate-400">
              <li>{data?.profile_reviewed ? '✓' : '○'} Recruiter approves profile</li>
              <li>{data?.evaluation?.status === 'approved' ? '✓' : '○'} Recruiter approves evaluation</li>
              <li>{data?.skill_test?.status === 'approved' ? '✓' : '○'} Recruiter approves skill test</li>
            </ol>
            <p className="mt-3 text-[11px] text-slate-500">
              AI suggestions never change a candidate’s stage without recruiter approval.
            </p>
          </div>
        </div>
      </div>
      ) : null}
    </div>
  )
}

/** Resume evidence + the editable, approvable profile. */
function ProfileTab({ data, onSaved }) {
  if (!data?.has_resume && !data?.extracted_profile) {
    return (
      <EmptyState
        icon={FileText}
        title="No resume on this candidate"
        description="This candidate was created manually. Upload a PDF resume from the Candidates page to extract a structured profile, or fill the profile in and save it."
      />
    )
  }

  return (
    <div className="space-y-6">
      <div className="card">
        <div className="flex flex-wrap items-start justify-between gap-3">
          <div className="flex items-start gap-3">
            <span className="grid h-10 w-10 place-items-center rounded-xl bg-brand-600/20 text-brand-300 ring-1 ring-brand-500/30">
              <FileText size={18} />
            </span>
            <div>
              <h2 className="text-sm font-semibold text-white">
                {data.resume_filename ?? 'Resume'}
              </h2>
              <p className="mt-0.5 text-xs text-slate-500">
                Uploaded {formatDateTime(data.uploaded_at)} · extracted {formatDateTime(data.extracted_at)}
              </p>
            </div>
          </div>
          <div className="flex flex-wrap gap-2 text-xs">
            <span className="chip">{data.resume_page_count ?? '—'} page(s)</span>
            <span className="chip">{data.resume_word_count ?? '—'} words</span>
            <span className="chip">
              {data.ai_provider ?? 'n/a'}/{data.ai_model ?? 'n/a'}
            </span>
          </div>
        </div>

        {data.extraction_warnings?.length ? (
          <ul className="mt-3 space-y-1 rounded-xl border border-amber-500/25 bg-amber-500/5 p-3">
            {data.extraction_warnings.map((warning) => (
              <li key={warning} className="flex items-start gap-2 text-[11px] text-amber-300">
                <Award size={12} className="mt-0.5 shrink-0" />
                {warning}
              </li>
            ))}
          </ul>
        ) : null}

        {data.profile_reviewed ? (
          <p className="mt-3 text-xs text-emerald-300">
            Approved by a recruiter on {formatDateTime(data.profile_reviewed_at)}.
          </p>
        ) : (
          <p className="mt-3 text-xs text-amber-300">
            Extracted automatically - not yet approved. Review every field below before saving.
          </p>
        )}
      </div>

      <ProfileForm candidate={data} onSaved={onSaved} />

      <details className="card">
        <summary className="cursor-pointer text-sm font-semibold text-white">
          Original extracted resume text ({data.resume_char_count ?? 0} characters)
        </summary>
        <p className="mt-2 text-[11px] text-slate-500">
          This is the evidence the profile above was derived from. Stored with the candidate and
          never published publicly.
        </p>
        <pre className="mt-3 max-h-80 overflow-auto whitespace-pre-wrap rounded-xl border border-white/5 bg-ink-950/60 p-3 text-[11px] leading-relaxed text-slate-400">
          {data.resume_text || 'No extracted text stored.'}
        </pre>
      </details>
    </div>
  )
}

/** Chronological activity from the append-only backend workflow event log. */
function ActivityTab({ data }) {
  const activity = useApiResource(() => getCandidateEvents(data.id), [data.id])
  const events = [...(activity.data ?? [])].sort(
    (left, right) => new Date(left.timestamp ?? left.created_at) - new Date(right.timestamp ?? right.created_at),
  )

  if (activity.loading) return <LoadingCard label="Loading candidate activity..." />
  if (activity.error) return <ErrorCard message={activity.error} onRetry={activity.reload} />

  if (!events.length) {
    return (
      <EmptyState
        icon={Activity}
        title="No activity recorded"
        description="Recruiter approvals, AI drafts, stage changes and integrations will appear here."
      />
    )
  }

  return (
    <div className="card">
      <h2 className="text-sm font-semibold text-white">Activity</h2>
      <ol className="mt-4 space-y-4">
        {events.map((event) => (
          <li key={event.id ?? `${event.event}-${event.timestamp}`} className="flex items-start gap-3">
            <span className="grid h-8 w-8 shrink-0 place-items-center rounded-full border border-white/10 bg-white/5 text-brand-300">
              <Activity size={14} />
            </span>
            <div>
              <p className="text-sm text-slate-200">
                {(event.event ?? 'workflow_event').replaceAll('_', ' ')}
              </p>
              <p className="text-xs text-slate-500">
                {formatDateTime(event.timestamp ?? event.created_at)} · {event.actor ?? 'system'}
              </p>
              {event.metadata && Object.keys(event.metadata).length ? (
                <pre className="mt-2 max-w-3xl overflow-auto whitespace-pre-wrap rounded-lg bg-white/[0.03] p-2 text-[10px] text-slate-500">
                  {JSON.stringify(event.metadata, null, 2)}
                </pre>
              ) : null}
            </div>
          </li>
        ))}
      </ol>
    </div>
  )
}

function BackLink() {
  return (
    <Link
      to="/candidates"
      className="inline-flex items-center gap-1.5 text-xs font-semibold text-slate-400 transition hover:text-brand-300"
    >
      <ArrowLeft size={14} /> Back to candidates
    </Link>
  )
}
