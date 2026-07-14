import { useEffect, useState } from 'react'
import { useDispatch, useSelector } from 'react-redux'
import { selectSelectedHcp } from '../store/hcpsSlice'
import { fetchInteractions } from '../store/interactionsSlice'
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
  const [tab, setTab] = useState('form')

  useEffect(() => {
    if (hcp) {
      dispatch(fetchInteractions(hcp.id))
      dispatch(fetchFollowups(hcp.id))
      dispatch(resetChat())
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
          <div className="page-sub">Capture a touchpoint via a structured form or a quick chat.</div>
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

      {/* Mode toggle */}
      <div className="tabs">
        <button className={`tab ${tab === 'form' ? 'active' : ''}`} onClick={() => setTab('form')}>
          📋 Structured form
        </button>
        <button className={`tab ${tab === 'chat' ? 'active' : ''}`} onClick={() => setTab('chat')}>
          💬 Conversational
        </button>
      </div>

      <div className="two-col">
        {tab === 'form' ? <InteractionForm hcp={hcp} /> : <ChatPanel hcp={hcp} />}
        <div className="side-col">
          <FollowUpsPanel />
          <InteractionList />
        </div>
      </div>
    </main>
  )
}
