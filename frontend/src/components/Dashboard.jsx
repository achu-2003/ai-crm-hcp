import { useEffect } from 'react'
import { useDispatch, useSelector } from 'react-redux'
import { fetchStats } from '../store/dashboardSlice'
import { avatarColor, formatDate, initials } from '../utils'

const SENTIMENT_META = [
  { key: 'positive', label: 'Positive', var: 'var(--pos)' },
  { key: 'neutral', label: 'Neutral', var: 'var(--neu)' },
  { key: 'negative', label: 'Negative', var: 'var(--neg)' },
]
const TYPE_META = [
  { key: 'call', label: 'Call' },
  { key: 'visit', label: 'Visit' },
  { key: 'email', label: 'Email' },
  { key: 'virtual', label: 'Virtual' },
]

export default function Dashboard({ onLogClick }) {
  const dispatch = useDispatch()
  const { stats, status } = useSelector((s) => s.dashboard)
  const hcpCount = useSelector((s) => s.hcps.items.length)

  // Refetch on mount and whenever the HCP directory size changes (add/delete).
  useEffect(() => {
    dispatch(fetchStats())
  }, [hcpCount])

  if (!stats && status === 'loading') {
    return <main className="main"><div className="empty-block">Loading dashboard…</div></main>
  }
  if (!stats) {
    return <main className="main"><div className="empty-block">No data yet.</div></main>
  }

  const s = stats
  const totalSent = SENTIMENT_META.reduce((a, m) => a + (s.sentiment[m.key] || 0), 0)
  const maxType = Math.max(1, ...TYPE_META.map((t) => s.interaction_types[t.key] || 0))
  const maxTier = Math.max(1, ...['A', 'B', 'C'].map((t) => s.tiers[t] || 0))

  const KPIS = [
    { label: 'HCPs in directory', value: s.hcp_count, icon: '👥', tone: 'brand' },
    { label: 'Interactions logged', value: s.interaction_count, icon: '📝', tone: 'indigo' },
    { label: 'Logged this week', value: s.logged_this_week, icon: '📈', tone: 'pos' },
    { label: 'Open follow-ups', value: s.followups_open, icon: '📅', tone: 'neu' },
  ]

  return (
    <main className="main fade-in">
      <div className="page-head">
        <div>
          <div className="page-title">Dashboard</div>
          <div className="page-sub">Your HCP engagement at a glance.</div>
        </div>
        <button className="btn ghost sm" style={{ marginLeft: 'auto' }}
          onClick={() => dispatch(fetchStats())}>↻ Refresh</button>
      </div>

      {s.hcp_count === 0 && (
        <div className="card card-pad dash-empty">
          <div className="se-icon">📊</div>
          <div className="se-title">Nothing to show yet</div>
          <div className="se-text">
            Add a Healthcare Professional from the left sidebar, then log an interaction —
            your metrics and activity will appear here.
          </div>
        </div>
      )}

      {/* KPI tiles */}
      <div className="kpi-row">
        {KPIS.map((k) => (
          <div className={`kpi-tile ${k.tone}`} key={k.label}>
            <div className="kpi-icon">{k.icon}</div>
            <div className="kpi-value">{k.value}</div>
            <div className="kpi-label">{k.label}</div>
          </div>
        ))}
      </div>

      <div className="dash-grid">
        {/* Sentiment breakdown */}
        <div className="card card-pad">
          <div className="list-head"><h3>Sentiment breakdown</h3></div>
          {totalSent === 0 ? (
            <div className="empty-block">No interactions logged yet.</div>
          ) : (
            <>
              <div className="stacked-bar">
                {SENTIMENT_META.map((m) => {
                  const v = s.sentiment[m.key] || 0
                  if (!v) return null
                  return (
                    <div key={m.key} className="stacked-seg"
                      style={{ width: `${(v / totalSent) * 100}%`, background: m.var }}
                      title={`${m.label}: ${v}`} />
                  )
                })}
              </div>
              <div className="legend">
                {SENTIMENT_META.map((m) => (
                  <div className="legend-item" key={m.key}>
                    <span className="legend-dot" style={{ background: m.var }} />
                    <span className="legend-label">{m.label}</span>
                    <span className="legend-val">{s.sentiment[m.key] || 0}</span>
                  </div>
                ))}
              </div>
            </>
          )}
        </div>

        {/* Interaction types */}
        <div className="card card-pad">
          <div className="list-head"><h3>Interaction types</h3></div>
          {s.interaction_count === 0 ? (
            <div className="empty-block">No interactions logged yet.</div>
          ) : (
            <div className="bar-list">
              {TYPE_META.map((t) => {
                const v = s.interaction_types[t.key] || 0
                return (
                  <div className="bar-row" key={t.key}>
                    <span className="bar-label">{t.label}</span>
                    <div className="bar-track">
                      <div className="bar-fill" style={{ width: `${(v / maxType) * 100}%` }} />
                    </div>
                    <span className="bar-val">{v}</span>
                  </div>
                )
              })}
            </div>
          )}
        </div>

        {/* Tier distribution */}
        <div className="card card-pad">
          <div className="list-head"><h3>HCP tiers</h3></div>
          {s.hcp_count === 0 ? (
            <div className="empty-block">No HCPs yet.</div>
          ) : (
            <div className="bar-list">
              {['A', 'B', 'C'].map((t) => {
                const v = s.tiers[t] || 0
                return (
                  <div className="bar-row" key={t}>
                    <span className={`bar-label tier-label tier ${t}`}>Tier {t}</span>
                    <div className="bar-track">
                      <div className={`bar-fill tier-fill-${t}`} style={{ width: `${(v / maxTier) * 100}%` }} />
                    </div>
                    <span className="bar-val">{v}</span>
                  </div>
                )
              })}
            </div>
          )}
        </div>

        {/* Recent activity feed (cross-HCP) */}
        <div className="card card-pad dash-activity">
          <div className="list-head">
            <h3>Recent activity</h3>
            <span className="count-badge">{s.recent_activity.length}</span>
          </div>
          {s.recent_activity.length === 0 ? (
            <div className="empty-block">
              No interactions yet.{' '}
              <button className="linklike" onClick={onLogClick}>Log your first one →</button>
            </div>
          ) : (
            s.recent_activity.map((it) => (
              <div className="activity-item" key={it.id}>
                <div className="avatar sm" style={{ background: avatarColor(it.hcp_id) }}>
                  {initials(it.hcp_name || '')}
                </div>
                <div className="activity-body">
                  <div className="activity-top">
                    <span className="activity-name">{it.hcp_name}</span>
                    <span className="type-badge">{it.interaction_type}</span>
                    <span className={`sentiment-tag ${it.sentiment}`}>{it.sentiment}</span>
                    <span className="ti-date">{formatDate(it.interaction_date)}</span>
                  </div>
                  <div className="activity-summary">{it.summary || it.raw_notes}</div>
                </div>
              </div>
            ))
          )}
        </div>
      </div>
    </main>
  )
}
