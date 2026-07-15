import { useState } from 'react'
import { useDispatch } from 'react-redux'
import { editInteraction } from '../store/interactionsSlice'

// Must track the backend enum (app/schemas.py::InteractionType) — a type missing
// here renders as "no type selected" on a record that in fact has one.
const TYPES = ['meeting', 'call', 'visit', 'email', 'virtual']
const SENTIMENTS = ['positive', 'neutral', 'negative']

// The structured edit path — calls PATCH /interactions/{id} which runs the
// edit_interaction agent tool with an explicit field patch.
export default function EditInteractionModal({ interaction, onClose }) {
  const dispatch = useDispatch()
  const [form, setForm] = useState({
    interaction_type: interaction.interaction_type,
    sentiment: interaction.sentiment,
    summary: interaction.summary,
    follow_up_needed: interaction.follow_up_needed,
  })
  const [saving, setSaving] = useState(false)
  const set = (k, v) => setForm((f) => ({ ...f, [k]: v }))

  const save = async () => {
    setSaving(true)
    await dispatch(editInteraction({ id: interaction.id, patch: form }))
    setSaving(false)
    onClose()
  }

  return (
    <div className="modal-overlay" onClick={onClose}>
      <div className="modal fade-in" onClick={(e) => e.stopPropagation()}>
        <div className="modal-head">
          <h3>Edit interaction #{interaction.id}</h3>
          <button className="modal-close" onClick={onClose}>×</button>
        </div>
        <div className="modal-body">
          <div className="field">
            <label>Type</label>
            <div className="segmented">
              {TYPES.map((t) => (
                <button key={t} className={`seg ${form.interaction_type === t ? 'on' : ''}`}
                  onClick={() => set('interaction_type', t)}>{t}</button>
              ))}
            </div>
          </div>
          <div className="field">
            <label>Sentiment</label>
            <div className="segmented">
              {SENTIMENTS.map((s) => (
                <button key={s} className={`seg sent-${s} ${form.sentiment === s ? 'on' : ''}`}
                  onClick={() => set('sentiment', s)}>{s}</button>
              ))}
            </div>
          </div>
          <div className="field">
            <label>Summary</label>
            <textarea value={form.summary} onChange={(e) => set('summary', e.target.value)} />
          </div>
          <div className="field">
            <label style={{ display: 'flex', alignItems: 'center', gap: 8, cursor: 'pointer' }}>
              <input type="checkbox" style={{ width: 'auto' }} checked={form.follow_up_needed}
                onChange={(e) => set('follow_up_needed', e.target.checked)} />
              Follow-up needed
            </label>
          </div>
        </div>
        <div className="modal-foot">
          <button className="btn ghost" onClick={onClose}>Cancel</button>
          <button className="btn" onClick={save} disabled={saving}>
            {saving ? <><span className="spinner" /> Saving…</> : 'Save changes'}
          </button>
        </div>
      </div>
    </div>
  )
}
