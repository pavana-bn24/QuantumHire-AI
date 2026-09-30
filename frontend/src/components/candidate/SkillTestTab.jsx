import { AlertTriangle, CheckCircle2, ClipboardList, Loader2, RefreshCw, Save } from 'lucide-react'
import { useEffect, useState } from 'react'

import {
  approveSkillTest,
  generateSkillTest,
  updateSkillTest,
} from '../../api/quantumhire.js'
import { ListField, TextAreaField, TextField } from './fields.jsx'

const editableFields = [
  'title',
  'business_problem',
  'objective',
  'requirements',
  'technical_requirements',
  'expected_deliverables',
  'evaluation_criteria',
  'time_limit',
  'duration_minutes',
  'instructions',
  'questions',
]

const editable = (test) => ({
  title: test?.title ?? '',
  business_problem: test?.business_problem ?? '',
  objective: test?.objective ?? '',
  requirements: test?.requirements ?? [],
  technical_requirements: test?.technical_requirements ?? [],
  expected_deliverables: test?.expected_deliverables ?? [],
  evaluation_criteria: test?.evaluation_criteria ?? [],
  time_limit: test?.time_limit ?? '',
  duration_minutes: test?.duration_minutes ?? 60,
  instructions: test?.instructions ?? '',
  questions: test?.questions ?? [],
})

export default function SkillTestTab({ candidate, onChanged }) {
  const [test, setTest] = useState(candidate?.skill_test ?? null)
  const [draft, setDraft] = useState(editable(candidate?.skill_test))
  const [action, setAction] = useState('')
  const [error, setError] = useState('')
  const evaluationApproved = candidate?.evaluation?.status === 'approved'
  const testApproved = test?.status === 'approved'

  useEffect(() => {
    const next = candidate?.skill_test ?? null
    setTest(next)
    setDraft(editable(next))
    setError('')
  }, [candidate?.id, candidate?.skill_test])

  const setField = (field, value) => setDraft((previous) => ({ ...previous, [field]: value }))
  const toPayload = () => {
    const minutes = Number(String(draft.time_limit).match(/\d+/)?.[0])
    return {
      ...Object.fromEntries(editableFields.map((field) => [field, draft[field]])),
      duration_minutes: Number.isFinite(minutes) ? Math.min(480, Math.max(5, minutes)) : draft.duration_minutes,
      questions: draft.questions ?? [],
    }
  }

  const run = async (kind) => {
    setAction(kind)
    setError('')
    try {
      const result = await generateSkillTest(candidate.id)
      setTest(result)
      setDraft(editable(result))
      onChanged?.()
    } catch (err) {
      setError(err.message ?? 'Could not generate the skill test.')
    } finally {
      setAction('')
    }
  }

  const save = async () => {
    setAction('save')
    setError('')
    try {
      const result = await updateSkillTest(candidate.id, toPayload())
      setTest(result)
      setDraft(editable(result))
      onChanged?.()
    } catch (err) {
      setError(err.message ?? 'Could not save the skill-test draft.')
    } finally {
      setAction('')
    }
  }

  const approve = async () => {
    setAction('approve')
    setError('')
    try {
      const result = await updateSkillTest(candidate.id, toPayload())
      setTest(result)
      const approved = await approveSkillTest(candidate.id)
      setTest(approved)
      setDraft(editable(approved))
      onChanged?.()
    } catch (err) {
      setError(err.message ?? 'Could not approve the skill test.')
    } finally {
      setAction('')
    }
  }

  if (!evaluationApproved) {
    return (
      <section className="card">
        <h2 className="flex items-center gap-2 text-sm font-semibold text-white"><ClipboardList size={15} /> Personalized skill test</h2>
        <p className="mt-2 text-xs text-slate-400">A recruiter must approve the AI evaluation before a tailored practical test can be generated.</p>
        {!candidate?.profile_reviewed ? <p className="mt-3 flex items-center gap-2 text-xs text-amber-300"><AlertTriangle size={14} /> Approve the candidate profile first.</p> : null}
      </section>
    )
  }

  if (!test) {
    return (
      <section className="card">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <div>
            <h2 className="flex items-center gap-2 text-sm font-semibold text-white"><ClipboardList size={15} /> Personalized skill test</h2>
            <p className="mt-2 max-w-2xl text-xs text-slate-400">The draft uses this role’s requirements and the candidate’s approved strengths and evidence gaps.</p>
          </div>
          <button type="button" onClick={() => run('generate')} disabled={action !== ''} className="btn-primary">
            {action === 'generate' ? <Loader2 size={15} className="animate-spin" /> : <RefreshCw size={15} />}
            Generate Personalized Test
          </button>
        </div>
        {error ? <ErrorMessage>{error}</ErrorMessage> : null}
      </section>
    )
  }

  return (
    <div className="space-y-5">
      <section className="card flex flex-wrap items-center justify-between gap-3">
        <div>
          <h2 className="flex items-center gap-2 text-sm font-semibold text-white">
            <ClipboardList size={15} /> Personalized skill test
            <span className={`chip ${testApproved ? 'border-emerald-500/30 bg-emerald-500/10 text-emerald-300' : 'border-amber-500/30 bg-amber-500/10 text-amber-300'}`}>
              {testApproved ? 'Recruiter approved' : 'Draft — recruiter review required'}
            </span>
          </h2>
          <p className="mt-1 text-xs text-slate-500">
            Generated {test.generated_at ? new Date(test.generated_at).toLocaleString() : '—'}
            {test.provider ? ` · Provider: ${test.provider}` : ''}
          </p>
        </div>
        {!testApproved ? (
          <div className="flex flex-wrap gap-2">
            <button type="button" onClick={() => run('regenerate')} disabled={action !== ''} className="btn-ghost">
              {action === 'regenerate' ? <Loader2 size={15} className="animate-spin" /> : <RefreshCw size={14} />}
              Regenerate
            </button>
            <button type="button" onClick={save} disabled={action !== ''} className="btn-ghost">
              {action === 'save' ? <Loader2 size={15} className="animate-spin" /> : <Save size={14} />}
              Save Draft
            </button>
            <button type="button" onClick={approve} disabled={action !== ''} className="btn-primary">
              {action === 'approve' ? <Loader2 size={15} className="animate-spin" /> : <CheckCircle2 size={15} />}
              Approve &amp; Move to Skill Test
            </button>
          </div>
        ) : null}
      </section>
      {error ? <ErrorMessage>{error}</ErrorMessage> : null}
      {testApproved ? (
        <p className="rounded-xl border border-emerald-500/30 bg-emerald-500/10 px-3 py-2 text-xs text-emerald-300">
          Skill test approved by {test.approved_by ?? 'a recruiter'}; the candidate is now in the Skill Test stage.
        </p>
      ) : null}

      {test.knowledge_sources?.length ? (
        <section className="card">
          <h3 className="section-title">Retrieved skill-test guidelines</h3>
          <ul className="mt-2 flex flex-wrap gap-2">
            {test.knowledge_sources.map((source) => (
              <li key={source} className="chip">
                {source}
              </li>
            ))}
          </ul>
        </section>
      ) : null}

      <section className="card space-y-4">
        <TextField label="Title" value={draft.title} onChange={(value) => setField('title', value)} />
        <TextAreaField label="Business Problem" rows={3} value={draft.business_problem} onChange={(value) => setField('business_problem', value)} />
        <TextAreaField label="Objective" rows={3} value={draft.objective} onChange={(value) => setField('objective', value)} />
        <div className="grid gap-5 md:grid-cols-2">
          <ListField label="Requirements" values={draft.requirements} onChange={(value) => setField('requirements', value)} />
          <ListField label="Technical Requirements" values={draft.technical_requirements} onChange={(value) => setField('technical_requirements', value)} />
          <ListField label="Expected Deliverables" values={draft.expected_deliverables} onChange={(value) => setField('expected_deliverables', value)} />
          <ListField label="Evaluation Criteria" values={draft.evaluation_criteria} onChange={(value) => setField('evaluation_criteria', value)} />
        </div>
        <TextField label="Time Limit" value={draft.time_limit} onChange={(value) => setField('time_limit', value)} placeholder="e.g. 60 minutes" />
        <TextAreaField label="Candidate Instructions" rows={3} value={draft.instructions} onChange={(value) => setField('instructions', value)} />
      </section>

      <section className="card">
        <h3 className="section-title">Practical questions</h3>
        {draft.questions?.length ? (
          <ol className="mt-3 list-decimal space-y-3 pl-5 text-sm text-slate-300">
            {draft.questions.map((question, index) => (
              <li key={`${question.focus}-${index}`}>
                {question.prompt}
                <span className="ml-2 chip">{question.type}</span>
                {question.focus ? <p className="mt-1 text-[11px] text-slate-500">Focus: {question.focus}</p> : null}
              </li>
            ))}
          </ol>
        ) : <p className="mt-3 text-xs text-slate-500">No questions were returned in this draft.</p>}
      </section>
      <p className="text-[11px] text-slate-500">Saving keeps this as a draft. Only recruiter approval moves the candidate to Skill Test and records the integration event.</p>
    </div>
  )
}

function ErrorMessage({ children }) {
  return <p role="alert" className="mt-3 rounded-xl border border-rose-500/30 bg-rose-500/10 px-3 py-2 text-xs text-rose-300">{children}</p>
}