import { useState } from 'react'
import { useDispatch, useSelector } from 'react-redux'
import {
  createInteraction,
  editInteraction,
  extractDraft,
  fetchInteractions,
  resetDraft,
  setDraftField,
} from '../store/interactionsSlice'
import { fetchFollowups } from '../store/followupsSlice'
import { joinDateTime } from '../utils'
import ChipInput from './ChipInput'
import VoiceNoteButton from './VoiceNoteButton'

const TYPES = ['meeting', 'call', 'visit', 'email', 'virtual']
const SENTIMENTS = [
  { value: 'positive', emoji: '🙂', label: 'Positive' },
  { value: 'neutral', emoji: '😐', label: 'Neutral' },
  { value: 'negative', emoji: '🙁', label: 'Negative' },
]
const COMMON_MATERIALS = ['Brochure', 'Reprint', 'Slide deck', 'Clinical study']

export default function InteractionForm({ hcp }) {
  const dispatch = useDispatch()
  const { draft, aiFilled, saving, extracting, error } = useSelector((s) => s.interactions)
  const [flash, setFlash] = useState(null)

  const set = (field, value) => dispatch(setDraftField({ field, value }))
  // A field the agent just filled gets a highlight so the rep knows what to review.
  const ai = (field) => (aiFilled.includes(field) ? 'ai-filled' : '')

  const editing = draft.id !== null

  /** Run the same extraction the chat uses over the free-notes box, so the rep
   *  can type notes into the form and have the AI structure them without
   *  switching to chat. */
  const summarizeNotes = () => {
    const text = draft.raw_notes.trim()
    if (text) dispatch(extractDraft({ hcpId: hcp.id, text }))
  }

  const submit = async (e) => {
    e.preventDefault()

    const fields = {
      interaction_type: draft.interaction_type,
      interaction_date: joinDateTime(draft.interaction_date, draft.interaction_time),
      attendees: draft.attendees,
      topics_discussed: draft.topics_discussed,
      materials_shared: draft.materials_shared,
      samples_dropped: draft.samples_dropped,
      sentiment: draft.sentiment || undefined,
      outcomes: draft.outcomes,
      follow_up_actions: draft.follow_up_actions,
      // A written next step means a follow-up is needed. Only ever set this to
      // true: sending false would override the AI's own inference on create.
      ...(draft.follow_up_actions.trim() ? { follow_up_needed: true } : {}),
    }

    // An interaction the agent already logged is PATCHed, not re-created —
    // otherwise confirming an AI-filled form would duplicate the row.
    const res = editing
      ? await dispatch(editInteraction({ id: draft.id, patch: fields, fromForm: true }))
      : await dispatch(
          createInteraction({
            hcp_id: hcp.id,
            raw_notes: draft.raw_notes,
            consent_obtained: draft.consent_obtained,
            source: draft.consent_obtained ? 'voice' : 'form',
            ...fields,
          }),
        )

    const thunk = editing ? editInteraction : createInteraction
    if (thunk.fulfilled.match(res)) {
      setFlash(editing ? `Updated interaction #${res.payload.id}` : `Logged interaction #${res.payload.id}`)
      dispatch(fetchInteractions(hcp.id))
      dispatch(fetchFollowups(hcp.id))
      setTimeout(() => setFlash(null), 4000)
    }
  }

  return (
    <form className="card card-pad fade-in" onSubmit={submit}>
      <div className="form-head">
        <div className="page-title" style={{ fontSize: 19 }}>Log HCP Interaction</div>
        {editing && (
          <span className="editing-badge">
            Editing #{draft.id}
            <button type="button" className="tag-x" onClick={() => dispatch(resetDraft())}>
              ×
            </button>
          </span>
        )}
      </div>

      <div className="enrich-note">
        <span>✨</span>
        <span>
          <b>AI-assisted.</b> Describe the interaction to the assistant on the right (or dictate a
          voice note) and these fields fill themselves. Anything you change by hand wins.
        </span>
      </div>

      <div className="section-label">Interaction Details</div>

      <div className="field-row">
        <div className="field">
          <label>HCP Name</label>
          <input type="text" value={hcp.name} readOnly className="readonly" />
        </div>
        <div className="field">
          <label>Interaction Type</label>
          <select
            className={ai('interaction_type')}
            value={draft.interaction_type}
            onChange={(e) => set('interaction_type', e.target.value)}
          >
            {TYPES.map((t) => (
              <option key={t} value={t}>
                {t[0].toUpperCase() + t.slice(1)}
              </option>
            ))}
          </select>
        </div>
      </div>

      <div className="field-row">
        <div className="field">
          <label>Date</label>
          <input
            type="date"
            className={ai('interaction_date')}
            value={draft.interaction_date}
            onChange={(e) => set('interaction_date', e.target.value)}
            required
          />
        </div>
        <div className="field">
          <label>Time</label>
          <input
            type="time"
            className={ai('interaction_time')}
            value={draft.interaction_time}
            onChange={(e) => set('interaction_time', e.target.value)}
          />
        </div>
      </div>

      <div className="field">
        <label>Attendees <span className="hint">— anyone else in the room</span></label>
        <ChipInput
          value={draft.attendees}
          onChange={(v) => set('attendees', v)}
          placeholder="Enter names or search…"
          highlight={aiFilled.includes('attendees')}
        />
      </div>

      <div className="field">
        <label>Topics Discussed</label>
        <textarea
          className={ai('topics_discussed')}
          placeholder="Enter key discussion points…"
          value={draft.topics_discussed}
          onChange={(e) => set('topics_discussed', e.target.value)}
        />
      </div>

      <VoiceNoteButton hcp={hcp} />

      <div className="section-label">Materials Shared / Samples Distributed</div>

      <div className="field">
        <label>Materials Shared</label>
        <ChipInput
          value={draft.materials_shared}
          onChange={(v) => set('materials_shared', v)}
          placeholder="Brochure, reprint, slide deck…"
          addLabel="🔍 Search/Add"
          suggestions={COMMON_MATERIALS}
          highlight={aiFilled.includes('materials_shared')}
        />
      </div>

      <div className="field">
        <label>Samples Distributed</label>
        <ChipInput
          value={draft.samples_dropped}
          onChange={(v) => set('samples_dropped', v)}
          placeholder="e.g. Cardizem x5"
          addLabel="+ Add Sample"
          suggestions={hcp.preferred_products || []}
          highlight={aiFilled.includes('samples_dropped')}
        />
      </div>

      <div className="field">
        <label>Observed/Inferred HCP Sentiment</label>
        <div className={`radio-row ${ai('sentiment')}`}>
          {SENTIMENTS.map((s) => (
            <label key={s.value} className={`radio-opt ${draft.sentiment === s.value ? 'on' : ''}`}>
              <input
                type="radio"
                name="sentiment"
                checked={draft.sentiment === s.value}
                onChange={() => set('sentiment', s.value)}
              />
              <span className="radio-emoji">{s.emoji}</span>
              {s.label}
            </label>
          ))}
        </div>
      </div>

      <div className="field">
        <label>Outcomes</label>
        <textarea
          className={ai('outcomes')}
          placeholder="Key outcomes or agreements…"
          value={draft.outcomes}
          onChange={(e) => set('outcomes', e.target.value)}
        />
      </div>

      <div className="field">
        <label>Follow-up Actions</label>
        <textarea
          className={ai('follow_up_actions')}
          placeholder="Next steps — the assistant can schedule these for you…"
          value={draft.follow_up_actions}
          onChange={(e) => set('follow_up_actions', e.target.value)}
        />
      </div>

      <details className="raw-notes">
        <summary>Free notes {draft.raw_notes ? '(1)' : '(optional)'}</summary>
        <div className="field" style={{ marginTop: 10 }}>
          <textarea
            placeholder="Type raw field notes here and let the AI structure them into the fields above."
            value={draft.raw_notes}
            onChange={(e) => set('raw_notes', e.target.value)}
          />
          <button
            type="button"
            className="btn ghost sm"
            onClick={summarizeNotes}
            disabled={extracting || !draft.raw_notes.trim()}
          >
            {extracting ? <><span className="spinner" /> Summarizing…</> : <>✨ Summarize into fields</>}
          </button>
        </div>
      </details>

      <div className="btn-row">
        <button className="btn" disabled={saving}>
          {saving ? (
            <><span className="spinner" /> Saving…</>
          ) : editing ? (
            <>💾 Update interaction</>
          ) : (
            <>✨ Log interaction</>
          )}
        </button>
        <button
          type="button"
          className="btn ghost"
          onClick={() => dispatch(resetDraft())}
          disabled={saving}
        >
          Clear
        </button>
        {flash && <span className="flash-ok">✓ {flash}</span>}
      </div>

      {/* A failed save used to land in the store and never reach the screen. */}
      {error && !saving && <div className="form-error">⚠️ {error}</div>}
    </form>
  )
}
