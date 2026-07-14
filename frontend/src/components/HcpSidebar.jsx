import { useState } from 'react'
import { useDispatch, useSelector } from 'react-redux'
import { deleteHcp, selectHcp } from '../store/hcpsSlice'
import { avatarColor, initials } from '../utils'
import AddHcpModal from './AddHcpModal'

export default function HcpSidebar() {
  const dispatch = useDispatch()
  const { items, selectedId, status } = useSelector((s) => s.hcps)
  const [adding, setAdding] = useState(false)

  const remove = (e, h) => {
    e.stopPropagation()
    if (window.confirm(`Delete ${h.name} and all their interactions?`)) {
      dispatch(deleteHcp(h.id))
    }
  }

  return (
    <aside className="sidebar">
      <div className="sidebar-head">
        <h2>My HCPs</h2>
        <button className="add-hcp-btn" onClick={() => setAdding(true)} title="Add HCP">
          + Add
        </button>
      </div>

      {status === 'loading' && <div className="empty-block">Loading…</div>}

      {status !== 'loading' && items.length === 0 && (
        <div className="sidebar-empty">
          <div className="se-icon">🩺</div>
          <div className="se-title">No HCPs yet</div>
          <div className="se-text">Add your first Healthcare Professional to start logging interactions.</div>
          <button className="btn sm" onClick={() => setAdding(true)}>+ Add your first HCP</button>
        </div>
      )}

      {items.map((h) => (
        <div
          key={h.id}
          className={`hcp-card ${h.id === selectedId ? 'active' : ''}`}
          onClick={() => dispatch(selectHcp(h.id))}
        >
          <div className="avatar" style={{ background: avatarColor(h.id) }}>
            {initials(h.name)}
          </div>
          <div className="hcp-meta">
            <div className="hcp-name">{h.name}</div>
            <div className="hcp-spec">{h.specialty || '—'}</div>
          </div>
          <span className={`tier ${h.tier}`}>{h.tier}</span>
          <button className="hcp-del" onClick={(e) => remove(e, h)} title="Delete HCP">×</button>
        </div>
      ))}

      {adding && <AddHcpModal onClose={() => setAdding(false)} />}
    </aside>
  )
}
