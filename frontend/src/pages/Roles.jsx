import { Briefcase, Layers, MapPin, Plus, RefreshCw, Upload, Users, X } from 'lucide-react'
import { useMemo, useState } from 'react'
import { useNavigate, useSearchParams } from 'react-router-dom'

import { createRole, getCandidates, getRoles } from '../api/quantumhire.js'
import { EmptyState, ErrorCard, LoadingCard, PageHeader } from '../components/ui/index.jsx'
import { useApiResource } from '../hooks/useApiResource.js'

/**
 * Skill areas a recruiter can require for a role. Mirrors the seeded
 * 'AI Full-Stack Developer' requirement matrix (backend/app/db/seed_data.py).
 */
const SKILL_CATALOG = [
  { key: 'frontend', label: 'Frontend', category: 'Engineering', weight: 7, description: 'Component-driven UI work with React and modern state/data patterns.' },
  { key: 'backend', label: 'Backend', category: 'Engineering', weight: 7, description: 'Python service design, request handling and clean domain layering.' },
  { key: 'apis', label: 'APIs', category: 'Engineering', weight: 7, description: 'Designing, documenting and versioning REST endpoints.' },
  { key: 'databases', label: 'Databases', category: 'Data', weight: 6, description: 'Schema design and querying across document and relational stores.' },
  { key: 'authentication', label: 'Authentication', category: 'Security', weight: 6, description: 'Sessions, tokens, role-based access control and secure credential handling.' },
  { key: 'ai_llm_apis', label: 'AI / LLM APIs', category: 'AI', weight: 7, description: 'Prompting, structured outputs and streaming against hosted LLM providers.' },
  { key: 'rag', label: 'RAG', category: 'AI', weight: 7, description: 'Chunking, embeddings, vector search and grounded answer synthesis.' },
  { key: 'agents_tool_calling', label: 'Agents / Tool Calling', category: 'AI', weight: 7, description: 'Tool schemas, planner/executor loops and safe function invocation.' },
  { key: 'automation', label: 'Automation', category: 'Platform', weight: 5, description: 'Removing manual recruiter steps through scheduled and event-driven jobs.' },
  { key: 'integrations', label: 'Integrations', category: 'Platform', weight: 5, description: 'Third-party ATS, email, calendar and webhook connectivity.' },
  { key: 'saas_concepts', label: 'SaaS', category: 'Product', weight: 5, description: 'Multi-tenancy, plans, onboarding and product analytics thinking.' },
  { key: 'deployment_devops', label: 'Deployment / DevOps', category: 'Platform', weight: 6, description: 'Containers, CI/CD pipelines, environment configuration and observability.' },
  { key: 'testing', label: 'Testing', category: 'Quality', weight: 6, description: 'Unit, integration and end-to-end coverage with reproducible fixtures.' },
  { key: 'security', label: 'Security', category: 'Security', weight: 6, description: 'OWASP awareness, input validation, secrets management and data privacy.' },
  { key: 'learning_research', label: 'Learning / Research', category: 'Product', weight: 5, description: 'Independently evaluating new tooling and communicating trade-offs.' },
]

export default function Roles() {
  const roles = useApiResource(getRoles, [])
  const candidates = useApiResource(() => getCandidates({ limit: 200 }), [])
  const [expandedRoleId, setExpandedRoleId] = useState(null)
  const [searchParams, setSearchParams] = useSearchParams()
  const navigate = useNavigate()

  // Create form state - opened by the "Create Job Role" button or ?create=1.
  const [createOpen, setCreateOpen] = useState(() => searchParams.get('create') === '1')
  const [title, setTitle] = useState('')
  const [description, setDescription] = useState('')
  const [selected, setSelected] = useState(() => new Set(SKILL_CATALOG.map((s) => s.key)))
  const [creating, setCreating] = useState(false)
  const [formError, setFormError] = useState('')
  const [flash, setFlash] = useState('')

  const candidateCounts = useMemo(() => {
    const counts = {}
    for (const candidate of candidates.data ?? []) {
      if (!candidate.role_id) continue
      counts[candidate.role_id] = (counts[candidate.role_id] ?? 0) + 1
    }
    return counts
  }, [candidates.data])

  const toggle = (roleId) => setExpandedRoleId((current) => (current === roleId ? null : roleId))

  const toggleSkill = (key) =>
    setSelected((current) => {
      const next = new Set(current)
      if (next.has(key)) next.delete(key)
      else next.add(key)
      return next
    })

  const openCreate = () => {
    setFormError('')
    setCreateOpen(true)
    if (searchParams.get('create')) setSearchParams({}, { replace: true })
  }

  /** POST /api/roles -> backend validates, persists to MongoDB, returns the role. */
  const handleCreate = async (event) => {
    event.preventDefault()
    const trimmedTitle = title.trim()
    if (trimmedTitle.length < 2) {
      setFormError('Enter a job title with at least 2 characters.')
      return
    }
    if (selected.size === 0) {
      setFormError('Select at least one required skill area.')
      return
    }

    setCreating(true)
    setFormError('')
    try {
      const payload = {
        title: trimmedTitle,
        description: description.trim(),
        requirements: SKILL_CATALOG.filter((skill) => selected.has(skill.key)).map(
          ({ key, label, category, weight, description: text }) => ({
            key,
            label,
            category,
            weight,
            description: text,
          }),
        ),
      }
      const created = await createRole(payload)
      setTitle('')
      setDescription('')
      setSelected(new Set(SKILL_CATALOG.map((s) => s.key)))
      setCreateOpen(false)
      setFlash(`Role "${created.title}" created and saved.`)
      setExpandedRoleId(created.id)
      await roles.reload()
    } catch (err) {
      setFormError(err.message ?? 'Could not create the role.')
    } finally {
      setCreating(false)
    }
  }

  /** Role -> Upload Candidate Resume (Candidates page opens the dialog for this role). */
  const uploadForRole = (roleId) => navigate(`/candidates?upload=1&role=${roleId}`)

  return (
    <div className="space-y-6">
      <PageHeader
        icon={Briefcase}
        title="Roles"
        subtitle="Hiring requirements that drive candidate assessment and skill tests."
        actions={
          <>
            <button type="button" onClick={roles.reload} className="btn-ghost">
              <RefreshCw size={15} className={roles.loading ? 'animate-spin' : ''} /> Refresh
            </button>
            <button
              type="button"
              onClick={createOpen ? () => setCreateOpen(false) : openCreate}
              className="btn-primary"
            >
              {createOpen ? <X size={15} /> : <Plus size={15} />}{' '}
              {createOpen ? 'Close' : 'Create Job Role'}
            </button>
          </>
        }
      />

      {flash ? (
        <p className="rounded-xl border border-emerald-500/30 bg-emerald-500/10 px-3 py-2 text-xs text-emerald-300">
          {flash}
        </p>
      ) : null}

      {createOpen ? (
        <form onSubmit={handleCreate} className="card space-y-4">
          <div>
            <h2 className="text-sm font-semibold text-white">Create Job Role</h2>
            <p className="mt-1 text-xs text-slate-500">
              Saved to MongoDB via POST /api/roles. The role is immediately selectable when
              uploading candidate resumes.
            </p>
          </div>

          <div>
            <label className="label" htmlFor="role-title">
              Job Title
            </label>
            <input
              id="role-title"
              className="input"
              value={title}
              onChange={(event) => setTitle(event.target.value)}
              placeholder="e.g. Senior AI Full-Stack Engineer"
              autoComplete="off"
            />
          </div>

          <div>
            <label className="label" htmlFor="role-description">
              Job Description
            </label>
            <textarea
              id="role-description"
              className="input resize-y"
              rows={3}
              value={description}
              onChange={(event) => setDescription(event.target.value)}
              placeholder="What this role owns day to day..."
            />
          </div>

          <div>
            <p className="label">Required Skills</p>
            <div className="grid gap-2 sm:grid-cols-2 xl:grid-cols-3">
              {SKILL_CATALOG.map((skill) => {
                const checked = selected.has(skill.key)
                return (
                  <label
                    key={skill.key}
                    className={`flex cursor-pointer items-start gap-2 rounded-xl border p-3 text-xs transition ${
                      checked
                        ? 'border-brand-500/40 bg-brand-600/15 text-brand-100'
                        : 'border-white/10 bg-white/[0.03] text-slate-400 hover:border-brand-500/30'
                    }`}
                  >
                    <input
                      type="checkbox"
                      className="mt-0.5"
                      checked={checked}
                      onChange={() => toggleSkill(skill.key)}
                    />
                    <span>
                      <span className="font-semibold">{skill.label}</span>
                      <span className="mt-0.5 block text-[10px] uppercase tracking-wider text-slate-500">
                        {skill.category} · weight {skill.weight}
                      </span>
                    </span>
                  </label>
                )
              })}
            </div>
          </div>

          {formError ? (
            <p role="alert" className="rounded-xl border border-rose-500/30 bg-rose-500/10 px-3 py-2 text-xs text-rose-300">
              {formError}
            </p>
          ) : null}

          <div className="flex gap-2">
            <button type="submit" className="btn-primary" disabled={creating}>
              {creating ? 'Creating...' : 'Create Role'}
            </button>
            <button
              type="button"
              className="btn-ghost"
              onClick={() => {
                setCreateOpen(false)
                setFormError('')
              }}
            >
              Cancel
            </button>
          </div>
        </form>
      ) : null}

      {roles.loading ? (
        <LoadingCard label="Loading roles..." />
      ) : roles.error ? (
        <ErrorCard message={roles.error} onRetry={roles.reload} />
      ) : (roles.data ?? []).length === 0 ? (
        <EmptyState
          icon={Briefcase}
          title="No roles yet"
          description="The default 'AI Full-Stack Developer' role is seeded automatically on backend startup."
        />
      ) : (
        <div className="space-y-4">
          {(roles.data ?? []).map((role) => {
            const isOpen = expandedRoleId === role.id
            const totalWeight = role.requirements.reduce((sum, req) => sum + (req.weight ?? 0), 0)

            return (
              <article key={role.id} className="card card-hover animate-fade-up">
                <div className="flex flex-wrap items-start justify-between gap-4">
                  <div className="min-w-0">
                    <div className="flex items-center gap-2">
                      <h2 className="text-lg font-bold text-white">{role.title}</h2>
                      <span className="chip border-emerald-500/30 bg-emerald-500/10 text-emerald-300">
                        {role.status}
                      </span>
                    </div>
                    <p className="mt-1.5 max-w-3xl text-sm leading-relaxed text-slate-400">
                      {role.description}
                    </p>
                    <div className="mt-3 flex flex-wrap gap-2 text-xs text-slate-400">
                      <span className="chip">
                        <Layers size={12} /> {role.department}
                      </span>
                      <span className="chip">
                        <MapPin size={12} /> {role.location}
                      </span>
                      <span className="chip">{role.employment_type}</span>
                      <span className="chip">{role.seniority}</span>
                      <span className="chip">
                        <Users size={12} /> {candidateCounts[role.id] ?? 0} candidates
                      </span>
                    </div>
                  </div>

                  <div className="text-right">
                    <p className="text-xs uppercase tracking-wider text-slate-500">Requirements</p>
                    <p className="text-2xl font-bold text-white">{role.requirements.length}</p>
                    <p className="text-xs text-slate-500">total weight {totalWeight}</p>
                    <div className="mt-3 flex justify-end gap-2">
                      <button
                        type="button"
                        onClick={() => uploadForRole(role.id)}
                        className="btn-ghost"
                        title="Upload a candidate resume for this role"
                      >
                        <Upload size={14} /> Upload resume
                      </button>
                      <button type="button" onClick={() => toggle(role.id)} className="btn-ghost">
                        {isOpen ? 'Hide matrix' : 'View matrix'}
                      </button>
                    </div>
                  </div>
                </div>

                {isOpen ? (
                  <div className="mt-5 grid gap-3 border-t border-white/5 pt-5 md:grid-cols-2 xl:grid-cols-3">
                    {role.requirements.map((requirement) => (
                      <div
                        key={requirement.key}
                        className="rounded-xl border border-white/5 bg-ink-950/50 p-3"
                      >
                        <div className="flex items-center justify-between gap-2">
                          <p className="text-sm font-semibold text-slate-100">
                            {requirement.label}
                          </p>
                          <span className="text-xs font-semibold tabular-nums text-brand-300">
                            {requirement.weight}
                          </span>
                        </div>
                        <p className="mt-1 text-[11px] uppercase tracking-wider text-slate-500">
                          {requirement.category}
                        </p>
                        <p className="mt-2 text-xs leading-relaxed text-slate-400">
                          {requirement.description}
                        </p>
                        <div className="mt-3 h-1.5 overflow-hidden rounded-full bg-white/5">
                          <div
                            className="h-full rounded-full bg-brand-500"
                            style={{ width: `${(requirement.weight / 10) * 100}%` }}
                          />
                        </div>
                      </div>
                    ))}
                  </div>
                ) : null}
              </article>
            )
          })}
        </div>
      )}

      <p className="text-xs text-slate-600">
        Requirements here drive AI evaluation and skill-test generation - both stay editable and
        are approved by a recruiter before anything is sent.
      </p>
    </div>
  )
}
