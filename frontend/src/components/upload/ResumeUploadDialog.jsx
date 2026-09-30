import { AlertTriangle, CheckCircle2, FileText, Loader2, Upload, X } from 'lucide-react'
import { useEffect, useRef, useState } from 'react'

import { getRoles, uploadResume } from '../../api/quantumhire.js'
import { PIPELINE_STAGES } from '../../constants/pipeline.js'

const MAX_RESUME_MB = 10

const STEPS = [
  { key: 'uploading', label: 'Uploading' },
  { key: 'extracting', label: 'Extracting & Structuring' },
  { key: 'ready', label: 'Ready for Review' },
]

const stepIndex = (key) => STEPS.findIndex((step) => step.key === key)

function validateFile(file) {
  if (!file) return 'Choose a PDF resume first.'

  const looksPdf = file.type === 'application/pdf' || /\.pdf$/i.test(file.name)
  if (!looksPdf) {
    return `"${file.name}" is not a PDF. Only PDF resumes can be uploaded.`
  }
  if (file.size > MAX_RESUME_MB * 1024 * 1024) {
    return `That file is ${(file.size / 1024 / 1024).toFixed(1)} MB, which exceeds the ${MAX_RESUME_MB} MB limit.`
  }
  if (file.size === 0) {
    return 'That file is empty.'
  }

  return ''
}

/**
 * Upload a PDF resume and follow the server-side pipeline:
 * Uploading -> Extracting & Structuring -> Ready for Review.
 *
 * The upload percentage is real (from XHR progress events). Once every byte
 * has been sent, the backend extracts and structures the profile before it
 * responds - the step label follows that real request state, and "Ready" is
 * only shown when the API actually returns the created candidate.
 */
export default function ResumeUploadDialog({ open, onClose, onUploaded, roleId: presetRoleId }) {
  const [file, setFile] = useState(null)
  const [roles, setRoles] = useState([])
  const [roleId, setRoleId] = useState(presetRoleId ?? '')
  const [rolesError, setRolesError] = useState('')
  const [stage, setStage] = useState(PIPELINE_STAGES[0])
  const [percent, setPercent] = useState(0)
  const [step, setStep] = useState(null)
  const [error, setError] = useState('')
  const [result, setResult] = useState(null)
  const [dragging, setDragging] = useState(false)

  const inputRef = useRef(null)

  useEffect(() => {
    if (!open) return undefined

    let cancelled = false
    getRoles()
      .then((data) => {
        if (!cancelled) {
          setRoles(data)
          if (!presetRoleId) {
            const preferred = data.find((role) => role.title === 'AI Full-Stack Developer')
              ?? data.find((role) => role.status === 'active')
              ?? data[0]
            if (preferred) setRoleId((current) => current || preferred.id)
          }
        }
      })
      .catch((err) => {
        if (!cancelled) {
          setRoles([])
          setRolesError(err.message ?? 'Could not load roles.')
        }
      })

    return () => {
      cancelled = true
    }
  }, [open])

  if (!open) return null

  const busy = step !== null && step !== 'ready'

  const reset = () => {
    setFile(null)
    setPercent(0)
    setStep(null)
    setError('')
    setResult(null)
  }

  const handleClose = () => {
    if (busy) return
    reset()
    onClose?.()
  }

  const start = async () => {
    const validationError = validateFile(file)
    if (validationError) {
      setError(validationError)
      return
    }
    if (!roleId) {
      setError('Select a role before uploading so the evaluation uses the correct requirements.')
      return
    }

    setError('')
    setResult(null)
    setPercent(0)
    setStep('uploading')

    try {
      const data = await uploadResume(
        file,
        { roleId: roleId || undefined, stage },
        {
          onUploadProgress: (event) => {
            if (!event.total) return
            const pct = Math.round((event.loaded / event.total) * 100)
            setPercent(pct)
            // Real signal: once every byte is sent the server is extracting
            // and structuring the profile - no simulated timers.
            if (pct >= 100) setStep('extracting')
          },
        },
      )

      setPercent(100)
      setStep('ready')
      setResult(data)
      onUploaded?.(data)
    } catch (err) {
      setStep(null)
      setError(err.message ?? 'Upload failed. Please try again.')
    }
  }

  return (
    <div className="fixed inset-0 z-50 flex items-start justify-center overflow-y-auto bg-ink-950/80 p-4 backdrop-blur-sm">
      <div className="card my-8 w-full max-w-2xl animate-fade-up">
        <div className="flex items-start justify-between gap-4">
          <div className="flex items-start gap-3">
            <span className="grid h-10 w-10 place-items-center rounded-xl bg-brand-600/20 text-brand-300 ring-1 ring-brand-500/30">
              <FileText size={18} />
            </span>
            <div>
              <h2 className="text-base font-bold text-white">Upload Resume</h2>
              <p className="mt-0.5 text-xs text-slate-400">
                PDF only, up to {MAX_RESUME_MB} MB. The file is processed in memory and is never
                stored or published.
              </p>
            </div>
          </div>
          <button
            type="button"
            onClick={handleClose}
            disabled={busy}
            className="rounded-lg border border-white/10 bg-white/5 p-2 text-slate-400 transition hover:text-slate-100 disabled:opacity-40"
            title="Close"
          >
            <X size={16} />
          </button>
        </div>

        {step === null ? (
          <>
            <div
              onDragOver={(event) => {
                event.preventDefault()
                setDragging(true)
              }}
              onDragLeave={() => setDragging(false)}
              onDrop={(event) => {
                event.preventDefault()
                setDragging(false)
                const dropped = event.dataTransfer.files?.[0]
                if (dropped) {
                  setFile(dropped)
                  setError(validateFile(dropped))
                }
              }}
              className={`mt-5 rounded-2xl border-2 border-dashed p-6 text-center transition ${
                dragging ? 'border-brand-500/60 bg-brand-600/10' : 'border-white/10 bg-ink-950/40'
              }`}
            >
              <Upload size={22} className="mx-auto text-slate-500" />
              <p className="mt-2 text-sm text-slate-300">Drag a resume here, or choose a file</p>
              <input
                ref={inputRef}
                type="file"
                accept="application/pdf,.pdf"
                className="hidden"
                onChange={(event) => {
                  const chosen = event.target.files?.[0] ?? null
                  setFile(chosen)
                  setError(chosen ? validateFile(chosen) : '')
                }}
              />
              <button type="button" onClick={() => inputRef.current?.click()} className="btn-ghost mt-3">
                Choose PDF
              </button>

              {file ? (
                <p className="mt-3 truncate text-xs text-brand-200">
                  {file.name} · {(file.size / 1024).toFixed(0)} KB
                </p>
              ) : null}
            </div>

            <div className="mt-4 grid gap-3 sm:grid-cols-2">
              <label className="block">
                <span className="label">Role for this candidate</span>
                <select
                  className="input"
                  value={roleId}
                  onChange={(event) => setRoleId(event.target.value)}
                >
                  <option value="">Choose a role</option>
                  {roles.map((role) => (
                    <option key={role.id} value={role.id}>
                      {role.title}
                    </option>
                  ))}
                </select>
              </label>

              <label className="block">
                <span className="label">Initial stage</span>
                <select
                  className="input"
                  value={stage}
                  onChange={(event) => setStage(event.target.value)}
                >
                  {PIPELINE_STAGES.map((option) => (
                    <option key={option} value={option}>
                      {option}
                    </option>
                  ))}
                </select>
              </label>
            </div>

            {rolesError ? (
              <p role="alert" className="mt-3 text-xs text-rose-300">{rolesError}</p>
            ) : roles.length === 0 ? (
              <p className="mt-3 text-xs text-amber-300">
                No active role is available. Create the AI Full-Stack Developer role before uploading a resume.
              </p>
            ) : null}

            {error ? (
              <p className="mt-4 flex items-start gap-2 rounded-xl border border-rose-500/30 bg-rose-500/10 px-3 py-2 text-xs text-rose-300">
                <AlertTriangle size={14} className="mt-0.5 shrink-0" />
                {error}
              </p>
            ) : null}

            <div className="mt-5 flex justify-end gap-2">
              <button type="button" onClick={handleClose} className="btn-ghost">
                Cancel
              </button>
              <button type="button" onClick={start} disabled={!file || !roleId} className="btn-primary">
                <Upload size={15} /> Upload Resume
              </button>
            </div>
          </>
        ) : null}

        <ResumePipelineProgress
          visible={step !== null}
          step={step}
          percent={percent}
          error={error}
          result={result}
          onReset={reset}
          onRetry={start}
          onOpen={() => {
            reset()
            onClose?.()
          }}
        />
      </div>
    </div>
  )
}

/** The 3-step pipeline indicator shown while the request is in flight. */
function ResumePipelineProgress({ visible, step, percent, error, result, onReset, onRetry, onOpen }) {
  if (!visible) return null

  const current = stepIndex(step)
  const ready = step === 'ready'

  const barWidth = ready
    ? '100%'
    : step === 'extracting'
      ? '85%'
      : `${Math.max(percent, 5)}%`

  return (
    <div className="mt-6">
      <ol className="space-y-3">
        {STEPS.map((entry, index) => {
          const done = index < current || ready
          const active = index === current && !ready

          return (
            <li key={entry.key} className="flex items-center gap-3">
              <span
                className={`grid h-7 w-7 shrink-0 place-items-center rounded-full border text-[11px] font-bold ${
                  done
                    ? 'border-emerald-500/40 bg-emerald-500/15 text-emerald-300'
                    : active
                      ? 'border-brand-500/50 bg-brand-600/20 text-brand-200'
                      : 'border-white/10 bg-white/5 text-slate-500'
                }`}
              >
                {done ? (
                  <CheckCircle2 size={14} />
                ) : active ? (
                  <Loader2 size={13} className="animate-spin" />
                ) : (
                  index + 1
                )}
              </span>
              <span
                className={`text-sm ${
                  done || active ? 'font-medium text-slate-100' : 'text-slate-500'
                }`}
              >
                {entry.label}
                {entry.key === 'uploading' && active ? ` · ${percent}%` : ''}
              </span>
            </li>
          )
        })}
      </ol>

      <div className="mt-4 h-1.5 overflow-hidden rounded-full bg-white/5">
        <div
          className="h-full rounded-full bg-gradient-to-r from-brand-500 to-accent-500 transition-all duration-300"
          style={{ width: barWidth }}
        />
      </div>

      {error ? (
        <p className="mt-4 flex items-start gap-2 rounded-xl border border-rose-500/30 bg-rose-500/10 px-3 py-2 text-xs text-rose-300">
          <AlertTriangle size={14} className="mt-0.5 shrink-0" />
          {error}
        </p>
      ) : null}

      {result ? (
        <div className="mt-4 rounded-xl border border-emerald-500/25 bg-emerald-500/5 p-3">
          <p className="text-xs font-semibold text-emerald-300">
            Ready for review · {result.candidate?.name ?? 'Candidate'}
          </p>
          <p className="mt-1 text-[11px] text-slate-400">
            {result.extraction?.provider}/{result.extraction?.model} ·{' '}
            {result.extraction?.page_count} page(s) · {result.extraction?.word_count} words extracted
          </p>
          {result.extraction?.warnings?.length ? (
            <ul className="mt-2 space-y-1">
              {result.extraction.warnings.map((warning) => (
                <li key={warning} className="text-[11px] text-amber-300">
                  · {warning}
                </li>
              ))}
            </ul>
          ) : null}
        </div>
      ) : null}

      <div className="mt-5 flex justify-end gap-2">
        {ready && result ? (
          <>
            <button type="button" onClick={onReset} className="btn-ghost">
              Upload another
            </button>
            <button type="button" onClick={onOpen} className="btn-primary">
              Open candidate review
            </button>
          </>
        ) : error ? (
          <>
            <button type="button" onClick={onReset} className="btn-ghost">
              Back
            </button>
            <button type="button" onClick={onRetry} className="btn-primary">
              Retry upload
            </button>
          </>
        ) : null}
      </div>
    </div>
  )
}
