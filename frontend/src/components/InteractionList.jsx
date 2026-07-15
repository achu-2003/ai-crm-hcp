import { useState } from 'react'
import { useSelector } from 'react-redux'
import { formatDate } from '../utils'
import EditInteractionModal from './EditInteractionModal'

export default function InteractionList() {
  const { items, status } = useSelector((s) => s.interactions)
  const [editing, setEditing] = useState(null)

  return (
    <div className="card card-pad">
      <div className="list-head">
        <h3>Recent interactions</h3>
        <span className="count-badge">{items.length}</span>
      </div>

      {status === 'loading' && <div className="empty-block">Loading…</div>}
      {status !== 'loading' && items.length === 0 && (
        <div className="empty-block">No interactions logged yet for this HCP.</div>
      )}

      {items.map((it) => (
        <div className="timeline-item" key={it.id}>
          <div className="ti-top">
            <span className="type-badge">{it.interaction_type}</span>
            <span className={`sentiment-tag ${it.sentiment}`}>{it.sentiment}</span>
            <span className="ti-date">{formatDate(it.interaction_date)}</span>
            <button className="btn ghost sm ti-edit" onClick={() => setEditing(it)}>
              Edit
            </button>
          </div>
          <div className="ti-summary">{it.summary || it.raw_notes}</div>
          <div className="chip-row">
            {(it.products_discussed || []).map((p) => (
              <span className="entity-chip" key={p}>💊 {p}</span>
            ))}
            {(it.materials_shared || []).map((m) => (
              <span className="entity-chip" key={`mat-${m}`}>📄 {m}</span>
            ))}
            {(it.samples_dropped || []).map((s) => (
              <span className="entity-chip" key={s}>🎁 {s}</span>
            ))}
            {(it.key_topics || []).map((t) => (
              <span className="entity-chip" key={t}>#{t}</span>
            ))}
            {it.follow_up_needed && <span className="entity-chip">📅 follow-up</span>}
            <span className="source-tag" style={{ marginLeft: 'auto', alignSelf: 'center' }}>
              via {it.source}
            </span>
          </div>
        </div>
      ))}

      {editing && (
        <EditInteractionModal interaction={editing} onClose={() => setEditing(null)} />
      )}
    </div>
  )
}
