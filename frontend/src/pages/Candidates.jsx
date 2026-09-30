import { CheckCircle2, Clock, FileUp, RefreshCw, Search, Users } from 'lucide-react'
import { useEffect, useMemo, useRef, useState } from 'react'
import { Link, useNavigate, useSearchParams } from 'react-router-dom'

import { getCandidates } from '../api/quantumhire.js'
import ResumeUploadDialog from '../components/upload/ResumeUploadDialog.jsx'
import { EmptyState, ErrorCard, LoadingCard, PageHeader, StageBadge } from '../components/ui/index.jsx'
import { PIPELINE_STAGES } from '../constants/pipeline.js'
import { useApiResource } from '../hooks/useApiResource.js'

const formatDate = (value) => {
  if (!value) return '—'
  const date = new Date(value)
  return Number.isNaN(date.getTime()) ? '—' : date.toLocaleDateString(undefined, {
    day: '2-digit',
    month: 'short',
    year: 'numeric',
  })
}

const FILTERS = ['All', ...PIPELINE_STAGES]

export default function Candidates() {
  // The Topbar global search lands here as ?search=...; keep the box in sync.
  // ?upload=1&role=<id> opens the upload dialog for a role selected on /roles.
  const [searchParams] = useSearchParams()
  const [stageFilter, setStageFilter] = useState('All')
  const [search, setSearch] = useState(() => searchParams.get('search') ?? '')
  const presetRole = searchParams.get('role') ?? ''
  const [uploadOpen, setUploadOpen] = useState(() => searchParams.get('upload') === '1')
  const navigate = useNavigate()
  const redirectTimer = useRef(null)

  useEffect(() => {
    setSearch(searchParams.get('search') ?? '')
  }, [searchParams])

  useEffect(() => {
    if (searchParams.get('upload') === '1') setUploadOpen(true)
  }, [searchParams])

  const query = useMemo(() => {
    const params = { limit: 200 }
    if (stageFilter !== 'All') params.stage = stageFilter
    if (search.trim()) params.search = search.trim()
    return params
  }, [stageFilter, search])

  const candidates = useApiResource(
    () => getCandidates(query),
    [query.stage, query.search, query.limit],
  )

  useEffect(() => () => clearTimeout(redirectTimer.current), [])

  /** Land on the new candidate so the recruiter can review the extraction. */
  const handleUploaded = ({ candidate_id: candidateId }) => {
    redirectTimer.current = setTimeout(() => navigate(`/candidates/${candidateId}`), 1200)
  }

  const rows = candidates.data ?? []

  return (
    <div className="space-y-6">
      <PageHeader
        icon={Users}
        title="Candidates"
        subtitle="Every applicant with their live position in the recruitment pipeline."
        actions={
          <>
            <button type="button" onClick={candidates.reload} className="btn-ghost">
              <RefreshCw size={15} className={candidates.loading ? 'animate-spin' : ''} /> Refresh
            </button>
            <button type="button" onClick={() => setUploadOpen(true)} className="btn-primary">
              <FileUp size={15} /> Upload Resume
            </button>
          </>
        }
      />

      <ResumeUploadDialog
        open={uploadOpen}
        roleId={presetRole}
        onClose={() => {
          setUploadOpen(false)
          candidates.reload()
        }}
        onUploaded={handleUploaded}
      />

      <div className="card space-y-4">
        <div className="flex flex-wrap gap-2">
          {FILTERS.map((filter) => (
            <button
              key={filter}
              type="button"
              onClick={() => setStageFilter(filter)}
              className={
                stageFilter === filter
                  ? 'rounded-full border border-brand-500/40 bg-brand-600/20 px-3.5 py-1.5 text-xs font-semibold text-white'
                  : 'rounded-full border border-white/10 bg-white/5 px-3.5 py-1.5 text-xs font-medium text-slate-400 transition hover:border-brand-500/30 hover:text-slate-200'
              }
            >
              {filter}
            </button>
          ))}
        </div>

        <div className="relative">
          <Search size={16} className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-500" />
          <input
            type="search"
            value={search}
            onChange={(event) => setSearch(event.target.value)}
            placeholder="Search by name, email or skill..."
            className="input pl-9"
            aria-label="Search candidates"
          />
        </div>
      </div>

      {candidates.loading ? (
        <LoadingCard label="Loading candidates..." />
      ) : candidates.error ? (
        <ErrorCard message={candidates.error} onRetry={candidates.reload} />
      ) : rows.length === 0 ? (
        <EmptyState
          icon={Users}
          title="No candidates match this view"
          description="Try a different stage filter or clear the search box."
        />
      ) : (
        <div className="card overflow-x-auto p-0">
          <table className="w-full min-w-[720px] text-left text-sm">
            <thead className="border-b border-white/5 bg-white/[0.02]">
              <tr className="text-xs uppercase tracking-wider text-slate-500">
                <th className="px-5 py-3 font-semibold">Candidate</th>
                <th className="px-5 py-3 font-semibold">Stage</th>
                <th className="px-5 py-3 font-semibold">Resume</th>
                <th className="px-5 py-3 font-semibold">Skills</th>
                <th className="px-5 py-3 font-semibold">Experience</th>
                <th className="px-5 py-3 font-semibold">Added</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-white/5">
              {rows.map((candidate) => (
                <tr key={candidate.id} className="transition hover:bg-white/[0.03]">
                  <td className="px-5 py-3">
                    <Link
                      to={`/candidates/${candidate.id}`}
                      className="font-medium text-slate-100 hover:text-brand-300"
                    >
                      {candidate.name}
                    </Link>
                    <p className="text-xs text-slate-500">{candidate.email}</p>
                  </td>
                  <td className="px-5 py-3">
                    <StageBadge stage={candidate.stage} />
                  </td>
                  <td className="px-5 py-3">
                    {candidate.has_resume ? (
                      <div className="space-y-1">
                        {candidate.profile_reviewed ? (
                          <span className="chip border-emerald-500/30 bg-emerald-500/10 text-emerald-300">
                            <CheckCircle2 size={11} /> Approved
                          </span>
                        ) : (
                          <span className="chip border-amber-500/30 bg-amber-500/10 text-amber-300">
                            <Clock size={11} /> Needs review
                          </span>
                        )}
                        <p className="max-w-[160px] truncate text-[11px] text-slate-500">
                          {candidate.resume_filename}
                        </p>
                      </div>
                    ) : (
                      <span className="text-[11px] text-slate-600">No resume</span>
                    )}
                  </td>
                  <td className="px-5 py-3">
                    <div className="flex flex-wrap gap-1">
                      {candidate.skills.slice(0, 4).map((skill) => (
                        <span key={skill} className="chip px-2 py-0.5 text-[11px]">
                          {skill}
                        </span>
                      ))}
                      {candidate.skills.length > 4 ? (
                        <span className="chip px-2 py-0.5 text-[11px]">
                          +{candidate.skills.length - 4}
                        </span>
                      ) : null}
                    </div>
                  </td>
                  <td className="px-5 py-3 text-slate-400">
                    {candidate.experience_years != null ? `${candidate.experience_years} yrs` : '—'}
                  </td>
                  <td className="px-5 py-3 text-slate-400">{formatDate(candidate.created_at)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      <p className="text-xs text-slate-600">
        Showing {rows.length} candidate{rows.length === 1 ? '' : 's'}
        {stageFilter !== 'All' ? ` in "${stageFilter}"` : ''}.
      </p>
    </div>
  )
}
