import { Plus, Trash2 } from 'lucide-react'

/** Reusable, fully-editable form primitives for the candidate profile. */

export function TextField({ label, value, onChange, placeholder, type = 'text' }) {
  return (
    <label className="block">
      <span className="label">{label}</span>
      <input
        type={type}
        className="input"
        value={value ?? ''}
        placeholder={placeholder}
        onChange={(event) => onChange(event.target.value)}
      />
    </label>
  )
}

export function TextAreaField({ label, value, onChange, placeholder, rows = 3 }) {
  return (
    <label className="block">
      <span className="label">{label}</span>
      <textarea
        className="input resize-y"
        rows={rows}
        value={value ?? ''}
        placeholder={placeholder}
        onChange={(event) => onChange(event.target.value)}
      />
    </label>
  )
}

/**
 * Editable list of plain strings (skills, technologies, achievements, ...).
 * Each item can be renamed or removed and new items can be appended.
 */
export function ListField({ label, values = [], onChange, placeholder = 'Add an item', hint }) {
  const update = (index, next) => {
    const copy = [...values]
    copy[index] = next
    onChange(copy)
  }

  const remove = (index) => onChange(values.filter((_, position) => position !== index))
  const add = () => onChange([...values, ''])

  return (
    <div>
      <div className="flex items-center justify-between gap-2">
        <span className="label mb-0">{label}</span>
        <span className="text-[11px] tabular-nums text-slate-500">{values.length}</span>
      </div>

      {hint ? <p className="mt-1 text-[11px] text-slate-500">{hint}</p> : null}

      <div className="mt-2 space-y-2">
        {values.length === 0 ? (
          <p className="rounded-lg border border-dashed border-white/10 px-3 py-2 text-[11px] text-slate-500">
            Nothing extracted. Add an entry only if the resume supports it.
          </p>
        ) : null}

        {values.map((value, index) => (
          <div key={`${label}-${index}`} className="flex items-center gap-2">
            <input
              className="input"
              value={value}
              placeholder={placeholder}
              onChange={(event) => update(index, event.target.value)}
            />
            <button
              type="button"
              onClick={() => remove(index)}
              className="rounded-lg border border-white/10 bg-white/5 p-2 text-slate-400 transition hover:border-rose-500/40 hover:text-rose-300"
              title={`Remove ${label} entry`}
            >
              <Trash2 size={14} />
            </button>
          </div>
        ))}
      </div>

      <button type="button" onClick={add} className="btn-ghost mt-2 px-3 py-1.5 text-xs">
        <Plus size={13} /> Add
      </button>
    </div>
  )
}

/**
 * Editable list of structured records (work experience, projects, education).
 * Nested ``type: "list"`` fields recurse into :func:`ListField`.
 */
export function ObjectListField({
  label,
  items = [],
  onChange,
  itemFields = [],
  blank,
  addLabel = 'Add entry',
  titleKey = 'name',
}) {
  const updateItem = (index, key, value) => {
    const copy = items.map((item, position) =>
      position === index ? { ...item, [key]: value } : item,
    )
    onChange(copy)
  }

  const removeItem = (index) => onChange(items.filter((_, position) => position !== index))
  const addItem = () => onChange([...items, blank()])

  return (
    <div>
      <div className="flex items-center justify-between gap-2">
        <span className="label mb-0">{label}</span>
        <span className="text-[11px] tabular-nums text-slate-500">{items.length}</span>
      </div>

      <div className="mt-2 space-y-3">
        {items.length === 0 ? (
          <p className="rounded-lg border border-dashed border-white/10 px-3 py-2 text-[11px] text-slate-500">
            Nothing extracted for this section.
          </p>
        ) : null}

        {items.map((item, index) => (
          <div
            key={`${label}-${index}`}
            className="rounded-xl border border-white/5 bg-ink-950/50 p-3"
          >
            <div className="mb-3 flex items-center justify-between gap-2">
              <p className="text-xs font-semibold text-slate-300">
                {item[titleKey] || item.title || item.company || item.institution || `Entry ${index + 1}`}
              </p>
              <button
                type="button"
                onClick={() => removeItem(index)}
                className="rounded-lg border border-white/10 bg-white/5 p-1.5 text-slate-400 transition hover:border-rose-500/40 hover:text-rose-300"
                title={`Remove ${label} entry`}
              >
                <Trash2 size={13} />
              </button>
            </div>

            <div className="grid gap-3 sm:grid-cols-2">
              {itemFields.map((field) => {
                const shared = {
                  key: field.key,
                  label: field.label,
                  value: item[field.key],
                  placeholder: field.placeholder,
                  onChange: (next) => updateItem(index, field.key, next),
                }

                if (field.type === 'list') return <ListField {...shared} key={field.key} />
                if (field.type === 'textarea') return <TextAreaField {...shared} key={field.key} />
                return <TextField {...shared} key={field.key} />
              })}
            </div>
          </div>
        ))}
      </div>

      <button type="button" onClick={addItem} className="btn-ghost mt-3 px-3 py-1.5 text-xs">
        <Plus size={13} /> {addLabel}
      </button>
    </div>
  )
}
