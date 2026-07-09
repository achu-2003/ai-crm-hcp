import { useState } from 'react'
import { useDispatch, useSelector } from 'react-redux'
import { createInteraction, fetchInteractions } from '../store/interactionsSlice'

const TYPES = ['call', 'visit', 'email', 'virtual']
const SENTIMENTS = ['positive', 'neutral', 'negative']

const emptyForm = {
  raw_notes: '',
  interaction_type: '',
  sentiment: '',
  channel: '',
  products: '',
  samples: '',
  follow_up_needed: false,
}

export default function InteractionForm({ hcp }) {
  const dispatch = useDispatch()
  const saving = useSelector((s) => s.interactions.saving)
  const [form, setForm] = useState(emptyForm)
  const [flash, setFlash] = useState(null)

  const set = (k, v) => setForm((f) => ({ ...f, [k]: v }))

  const submit = async (e) => {
    e.preventDefault()
    const payload = {
      hcp_id: hcp.id,
      raw_notes: form.raw_notes,
      enrich: true,
      ...(form.interaction_type ? { interaction_type: form.interaction_type } : {}),
      ...(form.sentiment ? { sentiment: form.sentiment } : {}),
      ...(form.channel ? { channel: form.channel } : {}),
      ...(form.products ? { products_discussed: split(form.products) } : {}),
      ...(form.samples ? { samples_dropped: split(form.samples) } : {}),
      ...(form.follow_up_needed ? { follow_up_needed: true } : {}),
    }
    const res = await dispatch(createInteraction(payload))
    if (createInteraction.fulfilled.match(res)) {
      setForm(emptyForm)
      setFlash(res.payload)
      dispatch(fetchInteractions(hcp.id))
      setTimeout(() => setFlash(null), 4000)
    }
  }

  return (
    <form className="card card-pad fade-in" onSubmit={submit}>
      <div className="enrich-note">
        <span>✨</span>
        <span>
          <b>AI-assisted logging.</b> Type your field notes below — the LangGraph{' '}
          <code>log_interaction</code> tool uses <b>gemma2-9b-it</b> to auto-summarise and extract
          entities (type, products, sentiment, follow-up). Any field you set manually overrides the AI.
        </span>
      </div>

      <div className="field">
        <label>
          Interaction notes <span className="hint">— free text, the AI does the rest</span>
        </label>
        <textarea
          placeholder="e.g. Met Dr. Mehta at Apollo, discussed Cardizem dosing, left 5 samples, very receptive, wants a follow-up next month."
          value={form.raw_notes}
          onChange={(e) => set('raw_notes', e.target.value)}
          required
        />
      </div>

      <div className="field">
        <label>Interaction type <span className="hint">(optional — AI infers)</span></label>
        <div className="segmented">
          {TYPES.map((t) => (
            <button
              type="button"
              key={t}
              className={`seg ${form.interaction_type === t ? 'on' : ''}`}
              onClick={() => set('interaction_type', form.interaction_type === t ? '' : t)}
            >
              {t}
            </button>
          ))}
        </div>
      </div>

      <div className="field">
        <label>HCP sentiment <span className="hint">(optional — AI infers)</span></label>
        <div className="segmented">
          {SENTIMENTS.map((s) => (
            <button
              type="button"
              key={s}
              className={`seg sent-${s} ${form.sentiment === s ? 'on' : ''}`}
              onClick={() => set('sentiment', form.sentiment === s ? '' : s)}
            >
              {s}
            </button>
          ))}
        </div>
      </div>

      <div className="field-row">
        <div className="field">
          <label>Products discussed <span className="hint">(comma-sep)</span></label>
          <input type="text" placeholder="Cardizem, Brilinta" value={form.products}
            onChange={(e) => set('products', e.target.value)} />
        </div>
        <div className="field">
          <label>Samples dropped <span className="hint">(comma-sep)</span></label>
          <input type="text" placeholder="Cardizem x5" value={form.samples}
            onChange={(e) => set('samples', e.target.value)} />
        </div>
      </div>

      <div className="field">
        <label style={{ display: 'flex', alignItems: 'center', gap: 8, cursor: 'pointer' }}>
          <input type="checkbox" style={{ width: 'auto' }} checked={form.follow_up_needed}
            onChange={(e) => set('follow_up_needed', e.target.checked)} />
          Flag a follow-up as needed
        </label>
      </div>

      <div className="btn-row">
        <button className="btn" disabled={saving}>
          {saving ? <><span className="spinner" /> Logging…</> : <>✨ Log interaction</>}
        </button>
        {flash && (
          <span style={{ color: 'var(--pos)', fontWeight: 600, fontSize: 13 }}>
            ✓ Logged & enriched (#{flash.id})
          </span>
        )}
      </div>
    </form>
  )
}

function split(s) {
  return s.split(',').map((x) => x.trim()).filter(Boolean)
}
