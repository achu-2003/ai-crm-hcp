import { useEffect, useState } from 'react'
import { useDispatch, useSelector } from 'react-redux'
import { selectSelectedHcp } from '../store/hcpsSlice'
import { fetchInteractions } from '../store/interactionsSlice'
import { resetChat } from '../store/chatSlice'
import { avatarColor, initials } from '../utils'
import InteractionForm from './InteractionForm'
import ChatPanel from './ChatPanel'
import InteractionList from './InteractionList'

export default function LogInteractionScreen() {
  const dispatch = useDispatch()
  const hcp = useSelector(selectSelectedHcp)
  const [tab, setTab] = useState('form')

  useEffect(() => {
    if (hcp) {
      dispatch(fetchInteractions(hcp.id))
      dispatch(resetChat())
    }
  }, [hcp?.id])

  if (!hcp) return <main className="main"><div className="empty-block">Select an HCP to begin.</div></main>

  return (
    <main className="main">
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
          <div className="hcp-spec">{hcp.specialty} · {hcp.institution}</div>
          <div className="chip-row">
            {(hcp.preferred_products || []).map((p) => (
              <span className="mini-chip" key={p}>💊 {p}</span>
            ))}
          </div>
        </div>
        <div className="hero-facts">
          <div>
            <div className="fact-label">Tier</div>
            <div className="fact-value">{hcp.tier}</div>
          </div>
          <div>
            <div className="fact-label">City</div>
            <div className="fact-value">{hcp.city}</div>
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
        <InteractionList />
      </div>
    </main>
  )
}
