import { useEffect, useRef, useState } from 'react'
import { useDispatch, useSelector } from 'react-redux'
import { pushUser, sendMessage } from '../store/chatSlice'
import { applyDraft, fetchInteractions } from '../store/interactionsSlice'
import { fetchFollowups } from '../store/followupsSlice'

const TOOL_LABELS = {
  log_interaction: 'Logged ✓',
  edit_interaction: 'Edited ✓',
  get_interaction_history: 'History',
  get_hcp_details: 'HCP lookup',
  schedule_followup: 'Follow-up set',
  chitchat: 'Chat',
}

const SUGGESTIONS = [
  'Today I met with Dr. Smith and discussed Product X efficacy. The sentiment was positive, and I shared the brochures.',
  'What did we discuss recently?',
  'Actually, change the sentiment to positive',
  'Schedule a follow-up in 2 weeks',
]

export default function ChatPanel({ hcp }) {
  const dispatch = useDispatch()
  const { messages, sending } = useSelector((s) => s.chat)
  const [text, setText] = useState('')
  const scrollRef = useRef(null)

  useEffect(() => {
    scrollRef.current?.scrollTo({ top: scrollRef.current.scrollHeight, behavior: 'smooth' })
  }, [messages, sending])

  const send = async (value) => {
    const msg = (value ?? text).trim()
    if (!msg || sending) return
    dispatch(pushUser(msg))
    setText('')
    const res = await dispatch(sendMessage({ hcpId: hcp.id, text: msg }))
    if (sendMessage.fulfilled.match(res)) {
      const { tool_used: tool, tool_result: result } = res.payload
      if (tool === 'log_interaction' || tool === 'edit_interaction') {
        // Mirror the record the agent just wrote into the form, so the rep sees
        // exactly what was extracted and can correct it before it stands.
        if (result && !result.error) dispatch(applyDraft(result))
        dispatch(fetchInteractions(hcp.id))
      }
      if (tool === 'schedule_followup') {
        dispatch(fetchFollowups(hcp.id))
      }
    }
  }

  return (
    <div className="card card-pad chat-wrap fade-in">
      <div className="assistant-head">
        <div className="assistant-title">🤖 AI Assistant</div>
        <div className="assistant-sub">Log interaction details here via chat</div>
      </div>

      <div className="chat-scroll" ref={scrollRef}>
        <div className="assistant-hint">
          Describe the interaction in your own words (e.g. “Met Dr. Mehta, discussed Cardizem
          efficacy, positive sentiment, shared brochure”) and I’ll fill in the form — or ask me
          for help.
        </div>

        {messages.length === 0 && (
          <div className="chat-empty">
            <div className="suggestion-row">
              {SUGGESTIONS.map((s) => (
                <button key={s} className="suggestion" onClick={() => send(s)}>
                  {s}
                </button>
              ))}
            </div>
          </div>
        )}

        {messages.map((m, i) => (
          <div key={i} className={`msg ${m.role}`}>
            <div>{m.text}</div>
            {m.role === 'assistant' && m.tool && (
              <div className="msg-tool-chips">
                <span className="tool-chip tool">🛠 {TOOL_LABELS[m.tool] || m.tool}</span>
                {m.result?.sentiment && (
                  <span className="tool-chip">Sentiment: {m.result.sentiment}</span>
                )}
                {m.result?.interaction_type && (
                  <span className="tool-chip">{m.result.interaction_type}</span>
                )}
                {m.result?.follow_up_needed && <span className="tool-chip">Follow-up flagged</span>}
                {typeof m.result?.count === 'number' && (
                  <span className="tool-chip">{m.result.count} record(s)</span>
                )}
              </div>
            )}
          </div>
        ))}

        {sending && (
          <div className="msg assistant">
            <span className="typing"><span /><span /><span /></span>
          </div>
        )}
      </div>

      <div className="chat-input">
        <input
          type="text"
          placeholder="Describe Interaction…"
          value={text}
          onChange={(e) => setText(e.target.value)}
          onKeyDown={(e) => e.key === 'Enter' && send()}
        />
        <button className="btn" onClick={() => send()} disabled={sending || !text.trim()}>
          Log
        </button>
      </div>
    </div>
  )
}
