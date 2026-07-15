import { useEffect } from 'react'
import { useDispatch, useSelector } from 'react-redux'
import { selectSelectedHcp } from '../store/hcpsSlice'
import { fetchInteractions, resetDraft } from '../store/interactionsSlice'
import { fetchFollowups } from '../store/followupsSlice'
import { resetChat } from '../store/chatSlice'
import { avatarColor, initials } from '../utils'
import InteractionForm from './InteractionForm'
import ChatPanel from './ChatPanel'
import InteractionList from './InteractionList'
import FollowUpsPanel from './FollowUpsPanel'

export default function LogInteractionScreen() {
  const dispatch = useDispatch()
  const hcp = useSelector(selectSelectedHcp)

  useEffect(() => {
    if (hcp) {
      dispatch(fetchInteractions(hcp.id))
      dispatch(fetchFollowups(hcp.id))
      dispatch(resetChat())
      // A half-filled draft belongs to the HCP it was written for.
      dispatch(resetDraft())
    }
  }, [hcp?.id])

  if (!hcp) {
    return (
      <main className="main">
        <div className="empty-block big-empty">
          <div className="se-icon">🩺</div>
          <div className="se-title">No HCP selected</div>
          <div className="se-text">Add or select a Healthcare Professional in the left sidebar to log an interaction.</div>
        </div>
      </main>
    )
  }

  return (
    <main className="main fade-in">
      <div className="page-head">
        <div>
          <div className="page-title">Log Interaction</div>
          <div className="page-sub">
            Describe the touchpoint to the assistant, dictate it, or fill the form — you confirm
            what gets saved.
          </div>
        </div>
      </div>

      {/* HCP context hero */}
      <div className="hcp-hero">
        <div className="avatar" style={{ background: avatarColor(hcp.id), width: 46, height: 46 }}>
          {initials(hcp.name)}
        </div>
        <div>
          <div className="hcp-name" style={{ fontSize: 15 }}>{hcp.name}</div>
          <div className="hcp-spec">
            {[hcp.specialty, hcp.institution].filter(Boolean).join(' · ') || 'No profile details'}
          </div>
          <div className="chip-row">
            {(hcp.preferred_products || []).map((p) => (
              <span className="mini-chip" key={p}>💊 {p}</span>
            ))}
          </div>
        </div>
        <div className="hero-facts">
          <div>
            <div className="fact-label">Tier</div>
            <div className={`fact-value tier ${hcp.tier}`} style={{ display: 'inline-block' }}>{hcp.tier}</div>
          </div>
          <div>
            <div className="fact-label">City</div>
            <div className="fact-value">{hcp.city || '—'}</div>
          </div>
        </div>
      </div>

      {/* The form and the assistant are one workspace, not two modes: the rep
          can type into either side and the agent's extraction lands in the
          form, where they confirm it. */}
      <div className="log-cols">
        <InteractionForm hcp={hcp} />
        <ChatPanel hcp={hcp} />
      </div>

      <div className="two-col" style={{ marginTop: 18 }}>
        <InteractionList />
        <div className="side-col">
          <FollowUpsPanel />
        </div>
      </div>
    </main>
  )
}
