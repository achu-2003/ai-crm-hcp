import { useState } from 'react'
import { useDispatch } from 'react-redux'
import { createHcp } from '../store/hcpsSlice'

const SPECIALTIES = [
  'Cardiology', 'Endocrinology', 'Oncology', 'Pulmonology',
  'Neurology', 'Rheumatology', 'Dermatology', 'Gastroenterology',
]
const TIERS = ['A', 'B', 'C']

// Create a real HCP from the UI — this is what makes the seeded demo data
// unnecessary: a rep builds their own directory.
export default function AddHcpModal({ onClose }) {
  const dispatch = useDispatch()
  const [form, setForm] = useState({
    name: '', specialty: '', institution: '', tier: 'B',
    city: '', email: '', preferred_products: '',
  })
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState(null)
  const set = (k, v) => setForm((f) => ({ ...f, [k]: v }))

  const save = async (e) => {
    e.preventDefault()
    if (!form.name.trim()) return
    setSaving(true)
    setError(null)
    const payload = {
      ...form,
      name: form.name.trim(),
      preferred_products: form.preferred_products
        .split(',').map((p) => p.trim()).filter(Boolean),
    }
    const res = await dispatch(createHcp(payload))
    setSaving(false)
    if (createHcp.fulfilled.match(res)) onClose()
    else setError(res.error?.message || 'Could not add HCP')
  }

  return (
    <div className="modal-overlay" onClick={onClose}>
      <form className="modal fade-in" onClick={(e) => e.stopPropagation()} onSubmit={save}>
        <div className="modal-head">
          <h3>Add a Healthcare Professional</h3>
          <button type="button" className="modal-close" onClick={onClose}>×</button>
        </div>
        <div className="modal-body">
          <div className="field">
            <label>Full name <span className="req">*</span></label>
            <input type="text" autoFocus placeholder="Dr. Ananya Mehta"
              value={form.name} onChange={(e) => set('name', e.target.value)} required />
          </div>
          <div className="field-row">
            <div className="field">
              <label>Specialty</label>
              <input type="text" list="specialties" placeholder="Cardiology"
                value={form.specialty} onChange={(e) => set('specialty', e.target.value)} />
              <datalist id="specialties">
                {SPECIALTIES.map((s) => <option key={s} value={s} />)}
              </datalist>
            </div>
            <div className="field">
              <label>Tier</label>
              <div className="segmented">
                {TIERS.map((t) => (
                  <button type="button" key={t}
                    className={`seg ${form.tier === t ? 'on' : ''}`}
                    onClick={() => set('tier', t)}>{t}</button>
                ))}
              </div>
            </div>
          </div>
          <div className="field">
            <label>Institution</label>
            <input type="text" placeholder="Apollo Hospitals"
              value={form.institution} onChange={(e) => set('institution', e.target.value)} />
          </div>
          <div className="field-row">
            <div className="field">
              <label>City</label>
              <input type="text" placeholder="Mumbai"
                value={form.city} onChange={(e) => set('city', e.target.value)} />
            </div>
            <div className="field">
              <label>Email</label>
              <input type="text" placeholder="a.mehta@apollo.example"
                value={form.email} onChange={(e) => set('email', e.target.value)} />
            </div>
          </div>
          <div className="field">
            <label>Preferred products <span className="hint">(comma-separated)</span></label>
            <input type="text" placeholder="Cardizem, Brilinta"
              value={form.preferred_products}
              onChange={(e) => set('preferred_products', e.target.value)} />
          </div>
          {error && <div className="form-error">⚠️ {error}</div>}
        </div>
        <div className="modal-foot">
          <button type="button" className="btn ghost" onClick={onClose}>Cancel</button>
          <button className="btn" disabled={saving || !form.name.trim()}>
            {saving ? <><span className="spinner" /> Adding…</> : 'Add HCP'}
          </button>
        </div>
      </form>
    </div>
  )
}
