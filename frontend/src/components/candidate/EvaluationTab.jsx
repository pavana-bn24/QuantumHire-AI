import { AlertTriangle, Award, CheckCircle2, Loader2, Pencil, RefreshCw, Sparkles } from 'lucide-react'
import { useEffect, useState } from 'react'

import {
  approveEvaluation,
  runEvaluation,
  updateEvaluation,
} from '../../api/quantumhire.js'
import { ListField, TextAreaField } from './fields.jsx'

const RATING_STYLES = {
  Demonstrated: 'border-emerald-500/30 bg-emerald-500/10 text-emerald-300',
  'Partially Demonstrated': 'border-amber-500/30 bg-amber-500/10 text-amber-300',
  'Not Demonstrated': 'border-slate-500/30 bg-white/5 text-slate-300',
  'Needs Verification': 'border-violet-500/30 bg-violet-500/10 text-violet-300',
}
const CAPABILITY_RATINGS = Object.keys(RATING_STYLES)

const asList = (value) => (Array.isArray(value) ? value : value ? [value] : [])
const asStatus = (value) =>
  typeof value === 'string' ? value : value?.rating ?? value?.status ?? 'Not provided'
const cleanList = (value) => asList(value).filter((item) => item.trim())

export default function EvaluationTab({ candidate, onChanged }) {
  const [evaluation, setEvaluation] = useState(candidate?.evaluation ?? null)
  const [action, setAction] = useState('')
  const [error, setError] = useState('')
  const [editing, setEditing] = useState(false)
  const [draft, setDraft] = useState({
    executive_summary: '',
    relevant_experience: [],
    demonstrated_strengths: [],
    skill_gaps: [],
    ai_first_readiness: '',
    implementation_capability: '',
    learning_research_readiness: '',
    evidence_gaps: [],
    recommended_next_step: '',
    assessments: [],
  })

  useEffect(() => {
    setEvaluation(candidate?.evaluation ?? null)
    setEditing(false)
    setError('')
  }, [candidate?.id, candidate?.evaluation])

  const approved = evaluation?.status === 'approved'
  const profileApproved = Boolean(candidate?.profile_reviewed)

  const handleGenerate = async () => {
    setAction('generate')
    setError('')
    try {
      const result = await runEvaluation(candidate.id)
      setEvaluation(result)
      onChanged?.()
    } catch (err) {
      setError(err.message ?? 'Could not generate the evaluation.')
    } finally {
      setAction('')
    }
  }

  const startEditing = () => {
    setDraft({
      executive_summary: evaluation?.executive_summary ?? evaluation?.summary ?? '',
      relevant_experience: asList(evaluation?.relevant_experience),
      demonstrated_strengths: asList(evaluation?.demonstrated_strengths ?? evaluation?.strengths),
      skill_gaps: asList(evaluation?.skill_gaps ?? evaluation?.gaps),
      ai_first_readiness: asStatus(evaluation?.ai_first_readiness) === 'Not provided' ? '' : asStatus(evaluation?.ai_first_readiness),
      implementation_capability: asStatus(evaluation?.implementation_capability) === 'Not provided' ? '' : asStatus(evaluation?.implementation_capability),
      learning_research_readiness: asStatus(evaluation?.learning_research_readiness) === 'Not provided' ? '' : asStatus(evaluation?.learning_research_readiness),
      evidence_gaps: asList(evaluation?.evidence_gaps),
      recommended_next_step: evaluation?.recommended_next_step ?? evaluation?.follow_up_questions?.join('\n') ?? '',
      assessments: (evaluation?.assessments ?? []).map((assessment) => ({ ...assessment })),
    })
    setEditing(true)
  }

  const updateAssessment = (index, key, value) => {
    setDraft((previous) => ({
      ...previous,
      assessments: previous.assessments.map((assessment, position) =>
        position === index ? { ...assessment, [key]: value } : assessment,
      ),
    }))
  }

  const handleSave = async () => {
    setAction('save')
    setError('')
    try {
      const result = await updateEvaluation(candidate.id, {
        executive_summary: draft.executive_summary,
        relevant_experience: cleanList(draft.relevant_experience),
        demonstrated_strengths: cleanList(draft.demonstrated_strengths),
        skill_gaps: cleanList(draft.skill_gaps),
        ai_first_readiness: draft.ai_first_readiness,
        implementation_capability: draft.implementation_capability,
        learning_research_readiness: draft.learning_research_readiness,
        evidence_gaps: cleanList(draft.evidence_gaps),
        recommended_next_step: draft.recommended_next_step,
        assessments: draft.assessments,
      })
      setEvaluation(result)
      setEditing(false)
      onChanged?.()
    } catch (err) {
      setError(err.message ?? 'Could not save the evaluation.')
    } finally {
      setAction('')
    }
  }

  const handleApprove = async () => {
    setAction('approve')
    setError('')
    try {
      const result = await approveEvaluation(candidate.id)
      setEvaluation(result)
      onChanged?.()
    } catch (err) {
      setError(err.message ?? 'Could not approve the recommendation.')
    } finally {
      setAction('')
    }
  }

  if (!evaluation) {
    return (
      <section className="card">
        <div className="flex flex-wrap items-start justify-between gap-4">
          <div>
            <h2 className="flex items-center gap-2 text-sm font-semibold text-white">
              <Sparkles size={15} className="text-brand-300" /> AI Evaluation
            </h2>
            <p className="mt-2 max-w-2xl text-xs leading-relaxed text-slate-400">
              Evaluation compares the recruiter-approved candidate evidence, this candidate’s role
              requirements, and retrieved recruitment knowledge. Missing evidence is not treated as
              proof of weakness.
            </p>
          </div>
          <button
            type="button"
            onClick={handleGenerate}
            disabled={!profileApproved || action !== ''}
            className="btn-primary"
          >
            {action === 'generate' ? <Loader2 size={15} className="animate-spin" /> : <Sparkles size={15} />}
            {action === 'generate' ? 'Generating...' : 'Generate Evaluation'}
          </button>
        </div>
        {!profileApproved ? (
          <p className="mt-4 flex items-center gap-2 text-xs text-amber-300">
            <AlertTriangle size={14} /> Approve the candidate profile before generating an evaluation.
          </p>
        ) : null}
        {error ? <ErrorMessage>{error}</ErrorMessage> : null}
      </section>
    )
  }

  const executiveSummary = evaluation.executive_summary ?? evaluation.summary
  const strengths = asList(evaluation.demonstrated_strengths ?? evaluation.strengths)
  const gaps = asList(evaluation.skill_gaps ?? evaluation.gaps)
  const assessments = editing ? draft.assessments : evaluation.assessments ?? []
  const readiness = [
    ['AI-first readiness', 'ai_first_readiness', evaluation.ai_first_readiness],
    ['Implementation capability', 'implementation_capability', evaluation.implementation_capability],
    ['Learning / research readiness', 'learning_research_readiness', evaluation.learning_research_readiness],
  ]

  return (
    <div className="space-y-5">
      <section className="card flex flex-wrap items-center justify-between gap-3">
        <div>
          <h2 className="flex items-center gap-2 text-sm font-semibold text-white">
            <Sparkles size={15} className="text-brand-300" /> AI Evaluation
            <span className={`chip ${approved ? 'border-emerald-500/30 bg-emerald-500/10 text-emerald-300' : 'border-amber-500/30 bg-amber-500/10 text-amber-300'}`}>
              {approved ? 'Recruiter approved' : 'Draft — review required'}
            </span>
          </h2>
          <p className="mt-1 text-xs text-slate-500">
            Role: {evaluation.role_title ?? '—'}
            {evaluation.generated_at ? ` · Generated ${new Date(evaluation.generated_at).toLocaleString()}` : ''}
            {evaluation.provider ? ` · Provider: ${evaluation.provider}` : ''}
          </p>
        </div>
        <div className="flex flex-wrap gap-2">
          {!approved && !editing ? (
            <button type="button" onClick={startEditing} className="btn-ghost">
              <Pencil size={14} /> Edit Evaluation
            </button>
          ) : null}
          {editing ? (
            <>
              <button type="button" onClick={() => setEditing(false)} className="btn-ghost">Cancel</button>
              <button type="button" onClick={handleSave} disabled={action !== ''} className="btn-primary">
                {action === 'save' ? <Loader2 size={15} className="animate-spin" /> : null}
                Save Changes
              </button>
            </>
          ) : null}
          {!approved && !editing ? (
            <button type="button" onClick={handleApprove} disabled={action !== ''} className="btn-primary">
              {action === 'approve' ? <Loader2 size={15} className="animate-spin" /> : <Award size={15} />}
              Approve Recommendation
            </button>
          ) : null}
        </div>
      </section>

      {error ? <ErrorMessage>{error}</ErrorMessage> : null}
      {approved ? (
        <p className="rounded-xl border border-emerald-500/30 bg-emerald-500/10 px-3 py-2 text-xs text-emerald-300">
          <CheckCircle2 className="mr-1 inline" size={14} />
          Recommendation approved{evaluation.approved_by ? ` by ${evaluation.approved_by}` : ''}.
          A personalized skill-test draft is available in the Skill Test tab.
        </p>
      ) : null}

      <section className="card">
        <h3 className="section-title">Executive summary</h3>
        {editing ? (
          <div className="mt-3">
            <TextAreaField label="Summary" rows={4} value={draft.executive_summary} onChange={(executive_summary) => setDraft((prev) => ({ ...prev, executive_summary }))} />
          </div>
        ) : <p className="mt-2 text-sm leading-relaxed text-slate-300">{executiveSummary || 'No summary provided.'}</p>}
      </section>

      <section className="card">
        <h3 className="section-title">Relevant experience</h3>
        {editing ? (
          <div className="mt-3">
            <ListField label="Relevant experience" values={draft.relevant_experience} onChange={(relevant_experience) => setDraft((prev) => ({ ...prev, relevant_experience }))} hint="Keep each point supported by the recruiter-approved profile." />
          </div>
        ) : (
          <ul className="mt-3 space-y-2 text-sm text-slate-300">
            {asList(evaluation.relevant_experience).length ? asList(evaluation.relevant_experience).map((item, index) => <li key={`${item}-${index}`}>• {item}</li>) : <li className="text-slate-500">No directly relevant experience was identified in the approved evidence.</li>}
          </ul>
        )}
      </section>

      <div className="grid gap-5 lg:grid-cols-2">
        <section className="card">
          <h3 className="section-title">Demonstrated strengths</h3>
          {editing ? (
            <div className="mt-3"><ListField label="Strengths" values={draft.demonstrated_strengths} onChange={(demonstrated_strengths) => setDraft((prev) => ({ ...prev, demonstrated_strengths }))} hint="Only include strengths supported by the approved evidence." /></div>
          ) : <StringList items={strengths} empty="No strengths were identified in the approved evidence." />}
        </section>
        <section className="card">
          <h3 className="section-title">Skill gaps</h3>
          {editing ? (
            <div className="mt-3"><ListField label="Gaps" values={draft.skill_gaps} onChange={(skill_gaps) => setDraft((prev) => ({ ...prev, skill_gaps }))} />
              <p className="mt-3 text-[11px] text-slate-500">Record evidence gaps, not assumptions about the candidate’s abilities.</p>
            </div>
          ) : <StringList items={gaps} empty="No skill gaps were identified." />}
          {!editing ? <p className="mt-3 text-[11px] text-slate-500">A gap means the capability was not evidenced here; it is not a conclusion about the candidate’s actual ability.</p> : null}
        </section>
      </div>

      <section className="card">
        <h3 className="section-title">Capability readiness</h3>
        <div className="mt-3 grid gap-3 md:grid-cols-3">
          {readiness.map(([label, field, value]) => {
            const status = asStatus(value)
            return (
              <div key={label} className="rounded-xl border border-white/5 bg-white/[0.02] p-3">
                <p className="text-xs text-slate-400">{label}</p>
                {editing ? (
                  <select
                    className="input mt-2"
                    aria-label={label}
                    value={draft[field]}
                    onChange={(event) => setDraft((previous) => ({ ...previous, [field]: event.target.value }))}
                  >
                    <option value="">Select a rating</option>
                    {CAPABILITY_RATINGS.map((rating) => <option key={rating} value={rating}>{rating}</option>)}
                  </select>
                ) : <span className={`chip mt-2 ${RATING_STYLES[status] ?? 'border-white/10 text-slate-400'}`}>{status}</span>}
              </div>
            )
          })}
        </div>
        {assessments.length ? (
          <div className="mt-4 space-y-2">
            {assessments.map((assessment, index) => (
              <div key={assessment.capability} className="flex flex-wrap items-start justify-between gap-3 rounded-lg border border-white/5 p-3">
                <div className="min-w-0 flex-1">
                  <p className="text-xs font-medium text-slate-200">{assessment.label || assessment.capability}</p>
                  {assessment.evidence?.length ? <ul className="mt-1 space-y-1 text-[11px] text-slate-400">{assessment.evidence.map((quote) => <li key={quote}>“{quote}”</li>)}</ul> : <p className="mt-1 text-[11px] text-slate-500">No matching evidence in the approved profile.</p>}
                  {editing ? (
                    <TextAreaField label="Recruiter notes" rows={2} value={assessment.notes ?? ''} onChange={(value) => updateAssessment(index, 'notes', value)} />
                  ) : null}
                </div>
                {editing ? (
                  <select
                    className="input w-auto min-w-48"
                    aria-label={`${assessment.label || assessment.capability} rating`}
                    value={assessment.rating}
                    onChange={(event) => updateAssessment(index, 'rating', event.target.value)}
                  >
                    {CAPABILITY_RATINGS.map((rating) => <option key={rating} value={rating}>{rating}</option>)}
                  </select>
                ) : <span className={`chip ${RATING_STYLES[assessment.rating] ?? ''}`}>{assessment.rating}</span>}
              </div>
            ))}
          </div>
        ) : null}
      </section>

      <div className="grid gap-5 lg:grid-cols-2">
        <section className="card">
          <h3 className="section-title">Evidence gaps</h3>
          {editing ? (
            <div className="mt-3"><ListField label="Evidence gaps" values={draft.evidence_gaps} onChange={(evidence_gaps) => setDraft((prev) => ({ ...prev, evidence_gaps }))} /></div>
          ) : <StringList items={asList(evaluation.evidence_gaps)} empty="No specific evidence gaps were recorded." />}
        </section>
        <section className="card">
          <h3 className="section-title">Recommended next step</h3>
          {editing ? (
            <div className="mt-3">
              <TextAreaField label="Recommendation" rows={3} value={draft.recommended_next_step} onChange={(recommended_next_step) => setDraft((prev) => ({ ...prev, recommended_next_step }))} />
            </div>
          ) : <p className="mt-2 text-sm leading-relaxed text-slate-300">{evaluation.recommended_next_step || evaluation.follow_up_questions?.join(' · ') || 'Recruiter review is recommended.'}</p>}
        </section>
      </div>

      <section className="card">
        <h3 className="section-title">Recruitment knowledge sources</h3>
        <StringList items={asList(evaluation.knowledge_sources).map((source) => typeof source === 'string' ? source : source.source ?? source.content ?? JSON.stringify(source))} empty="No knowledge sources were retrieved." />
      </section>
      <p className="flex items-center gap-2 text-[11px] text-slate-500"><RefreshCw size={12} /> No overall score, candidate ranking, automatic selection or rejection is produced.</p>
    </div>
  )
}

function StringList({ items, empty }) {
  return items.length ? (
    <ul className="mt-3 space-y-2 text-sm text-slate-300">{items.map((item, index) => <li key={`${item}-${index}`}>• {item}</li>)}</ul>
  ) : <p className="mt-3 text-xs text-slate-500">{empty}</p>
}

function ErrorMessage({ children }) {
  return <p role="alert" className="rounded-xl border border-rose-500/30 bg-rose-500/10 px-3 py-2 text-xs text-rose-300">{children}</p>
}