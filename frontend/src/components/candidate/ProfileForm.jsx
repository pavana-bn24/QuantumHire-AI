import { AlertTriangle, CheckCircle2, Loader2, Save } from 'lucide-react'
import { useEffect, useMemo, useState } from 'react'

import { updateCandidateProfile } from '../../api/quantumhire.js'
import { PROFILE_SECTIONS, profileFromCandidate } from '../../constants/profile.js'
import { ListField, ObjectListField, TextField } from './fields.jsx'

/**
 * Recruiter review form for the extracted candidate profile.
 *
 * Every section is editable and nothing is treated as approved evidence until
 * "Save Candidate Profile" is pressed - that single action is what marks the
 * profile reviewed on the backend.
 */
export default function ProfileForm({ candidate, onSaved }) {
  const initial = useMemo(() => profileFromCandidate(candidate), [candidate])
  const [profile, setProfile] = useState(initial)
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState('')
  const [saved, setSaved] = useState(false)

  useEffect(() => {
    setProfile(initial)
    setSaved(false)
    setError('')
  }, [initial])

  const dirty = useMemo(() => JSON.stringify(profile) !== JSON.stringify(initial), [profile, initial])

  const setField = (key, value) => {
    setSaved(false)
    setProfile((previous) => ({ ...previous, [key]: value }))
  }

  const handleSave = async () => {
    setSaving(true)
    setError('')

    try {
      const updated = await updateCandidateProfile(candidate.id, { ...profile, reviewed: true })
      setSaved(true)
      onSaved?.(updated)
    } catch (err) {
      setError(err.message ?? 'Could not save the profile.')
    } finally {
      setSaving(false)
    }
  }

  const reviewed = candidate?.profile_reviewed

  return (
    <div className="space-y-5">
      <div className="card flex flex-wrap items-center justify-between gap-3">
        <div>
          <h2 className="text-sm font-semibold text-white">Review &amp; approve candidate profile</h2>
          <p className="mt-1 text-xs text-slate-400">
            Check every section against the resume text below, correct anything that is wrong, then
            save. Only a saved profile becomes approved candidate evidence.
          </p>
        </div>

        <div className="flex items-center gap-2">
          {reviewed ? (
            <span className="chip border-emerald-500/30 bg-emerald-500/10 text-emerald-300">
              <CheckCircle2 size={12} /> Approved
            </span>
          ) : (
            <span className="chip border-amber-500/30 bg-amber-500/10 text-amber-300">
              <AlertTriangle size={12} /> Not reviewed
            </span>
          )}
          {dirty ? <span className="chip">Unsaved changes</span> : null}

          <button type="button" onClick={handleSave} disabled={saving} className="btn-primary">
            {saving ? <Loader2 size={15} className="animate-spin" /> : <Save size={15} />}
            {saving ? 'Saving...' : 'Save Candidate Profile'}
          </button>
        </div>
      </div>

      {error ? (
        <p className="rounded-xl border border-rose-500/30 bg-rose-500/10 px-3 py-2 text-xs text-rose-300">
          {error}
        </p>
      ) : null}

      {saved ? (
        <p className="rounded-xl border border-emerald-500/30 bg-emerald-500/10 px-3 py-2 text-xs text-emerald-300">
          Profile saved and approved as candidate evidence.
        </p>
      ) : null}

      {PROFILE_SECTIONS.map((section) => (
        <section key={section.key} className="card">
          <h3 className="text-sm font-semibold text-white">{section.title}</h3>

          <div className="mt-4">
            {section.type === 'basic' ? (
              <div className="grid gap-3 sm:grid-cols-3">
                {section.fields.map((field) => (
                  <TextField
                    key={field.key}
                    label={field.label}
                    placeholder={field.placeholder}
                    value={profile[field.key]}
                    onChange={(value) => setField(field.key, value)}
                  />
                ))}
              </div>
            ) : section.type === 'list' ? (
              <ListField
                label={`${section.title} entries`}
                placeholder={section.placeholder}
                values={profile[section.field]}
                onChange={(values) => setField(section.field, values)}
              />
            ) : (
              <ObjectListField
                label={`${section.title} entries`}
                items={profile[section.field]}
                itemFields={section.itemFields}
                blank={section.blank}
                addLabel={section.addLabel}
                onChange={(items) => setField(section.field, items)}
              />
            )}
          </div>
        </section>
      ))}

      <div className="card flex flex-wrap items-center justify-between gap-3">
        <p className="text-xs text-slate-400">
          {reviewed
            ? 'This profile is approved and can be used for evaluation.'
            : 'Save to approve this profile for the evaluation stage.'}
        </p>
        <button type="button" onClick={handleSave} disabled={saving} className="btn-primary">
          {saving ? <Loader2 size={15} className="animate-spin" /> : <Save size={15} />}
          {saving ? 'Saving...' : 'Save Candidate Profile'}
        </button>
      </div>
    </div>
  )
}
