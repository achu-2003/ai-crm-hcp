import { useDispatch, useSelector } from 'react-redux'
import { completeFollowup } from '../store/followupsSlice'
import { formatDate } from '../utils'

// Surfaces FollowUp rows created by the schedule_followup agent tool.
export default function FollowUpsPanel() {
  const dispatch = useDispatch()
  const { items } = useSelector((s) => s.followups)
  const open = items.filter((f) => f.status === 'open')

  if (open.length === 0) return null

  const isOverdue = (iso) => new Date(iso) < new Date()

  return (
    <div className="card card-pad followups-card">
      <div className="list-head">
        <h3>📅 Scheduled follow-ups</h3>
        <span className="count-badge">{open.length}</span>
      </div>
      {open.map((f) => (
        <div className="followup-item" key={f.id}>
          <div className="fu-body">
            <div className="fu-purpose">{f.purpose}</div>
            <div className={`fu-date ${isOverdue(f.due_date) ? 'overdue' : ''}`}>
              {isOverdue(f.due_date) ? 'Overdue · ' : 'Due '}
              {formatDate(f.due_date)}
            </div>
          </div>
          <button className="btn ghost sm" onClick={() => dispatch(completeFollowup(f.id))}>
            ✓ Done
          </button>
        </div>
      ))}
    </div>
  )
}
