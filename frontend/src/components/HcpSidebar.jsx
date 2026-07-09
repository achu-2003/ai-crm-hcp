import { useDispatch, useSelector } from 'react-redux'
import { selectHcp } from '../store/hcpsSlice'
import { avatarColor, initials } from '../utils'

export default function HcpSidebar() {
  const dispatch = useDispatch()
  const { items, selectedId, status } = useSelector((s) => s.hcps)

  return (
    <aside className="sidebar">
      <h2>My HCPs</h2>
      {status === 'loading' && <div className="empty-block">Loading…</div>}
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
            <div className="hcp-spec">{h.specialty}</div>
          </div>
          <span className={`tier ${h.tier}`}>{h.tier}</span>
        </div>
      ))}
    </aside>
  )
}
