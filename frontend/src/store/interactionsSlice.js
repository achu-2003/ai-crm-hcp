import { createAsyncThunk, createSlice } from '@reduxjs/toolkit'
import { api } from '../api/client'
import { splitDateTime } from '../utils'

export const fetchInteractions = createAsyncThunk(
  'interactions/fetch',
  async (hcpId) => api.listInteractions(hcpId),
)

export const createInteraction = createAsyncThunk(
  'interactions/create',
  async (payload) => api.createInteraction(payload),
)

export const editInteraction = createAsyncThunk(
  'interactions/edit',
  async ({ id, patch }) => api.updateInteraction(id, patch),
)

/** Free text (typed notes or a voice transcript) → structured fields, WITHOUT
 *  persisting. The rep reviews the draft on the form and submits it. */
export const extractDraft = createAsyncThunk(
  'interactions/extract',
  async ({ hcpId, text, consent = false }) =>
    api.extractInteraction({ hcp_id: hcpId, text, consent_obtained: consent }),
)

/** The Log Interaction form is a controlled view over this draft. Both the rep
 *  (typing) and the agent (extracting) write to it, which is what lets the AI
 *  fill the form while leaving the human in control of what gets committed.
 *
 *  `id` is null for a new interaction and set once a record exists — that is
 *  what decides whether submitting POSTs a new row or PATCHes the existing one,
 *  so an agent-logged interaction is edited rather than duplicated. */
export function emptyDraft() {
  const { date, time } = splitDateTime(null)
  return {
    id: null,
    interaction_type: 'meeting',
    interaction_date: date,
    interaction_time: time,
    attendees: [],
    topics_discussed: '',
    materials_shared: [],
    samples_dropped: [],
    sentiment: '',
    outcomes: '',
    follow_up_actions: '',
    raw_notes: '',
    consent_obtained: false,
  }
}

/** API interaction record (or an /extract draft) → form draft.
 *
 *  `merge` decides what an empty value means, and the two callers need opposite
 *  answers:
 *
 *  - An /extract draft is a *suggestion*: `[]` means "found nothing", so it must
 *    not wipe what the rep already typed → merge = true.
 *  - A persisted record is the *truth*: `[]` means the field is genuinely empty,
 *    so the form must show that. Merging here would let a field the agent just
 *    cleared ("drop the brochures") survive on screen and get written straight
 *    back on the next submit.
 */
function toDraft(record, previous, { merge } = { merge: false }) {
  const base = previous ?? emptyDraft()
  const { date, time } = record.interaction_date
    ? splitDateTime(record.interaction_date)
    : { date: base.interaction_date, time: base.interaction_time }

  const isBlank = (v) =>
    v === undefined || v === null || v === '' || (Array.isArray(v) && !v.length)
  const pick = (next, current) => (merge && isBlank(next) ? current : next ?? current)

  return {
    ...base,
    id: record.id ?? base.id,
    interaction_type: pick(record.interaction_type, base.interaction_type),
    interaction_date: date,
    interaction_time: time,
    attendees: pick(record.attendees, base.attendees),
    topics_discussed: pick(record.topics_discussed, base.topics_discussed),
    materials_shared: pick(record.materials_shared, base.materials_shared),
    samples_dropped: pick(record.samples_dropped, base.samples_dropped),
    sentiment: pick(record.sentiment, base.sentiment),
    outcomes: pick(record.outcomes, base.outcomes),
    follow_up_actions: pick(record.follow_up_actions, base.follow_up_actions),
    raw_notes: pick(record.raw_notes, base.raw_notes),
    consent_obtained: record.consent_obtained ?? base.consent_obtained,
  }
}

/** Load a record into the draft and remember which fields moved, so the form can
 *  highlight exactly what the AI touched. */
function loadIntoDraft(state, record, merge) {
  const before = state.draft
  state.draft = toDraft(record, before, { merge })
  state.aiFilled = Object.keys(state.draft).filter(
    (f) => f !== 'id' && JSON.stringify(state.draft[f]) !== JSON.stringify(before[f]),
  )
}

const initialState = {
  items: [],
  status: 'idle',
  saving: false,
  extracting: false,
  error: null,
  lastCreated: null,
  draft: emptyDraft(),
  /** Fields the AI just wrote, so the form can highlight them for review. */
  aiFilled: [],
}

const interactionsSlice = createSlice({
  name: 'interactions',
  initialState,
  reducers: {
    clearLastCreated(state) {
      state.lastCreated = null
    },
    setDraftField(state, action) {
      const { field, value } = action.payload
      state.draft[field] = value
      // The rep has taken ownership of this field — stop flagging it as AI-filled.
      state.aiFilled = state.aiFilled.filter((f) => f !== field)
    },
    /** Load a persisted interaction (the one the agent just logged or edited)
     *  into the form. Authoritative — see toDraft's `merge`. */
    applyDraft(state, action) {
      loadIntoDraft(state, action.payload, false)
    },
    resetDraft(state) {
      state.draft = emptyDraft()
      state.aiFilled = []
    },
  },
  extraReducers: (builder) => {
    builder
      .addCase(fetchInteractions.pending, (state) => {
        state.status = 'loading'
      })
      .addCase(fetchInteractions.fulfilled, (state, action) => {
        state.status = 'succeeded'
        state.items = action.payload
      })
      .addCase(fetchInteractions.rejected, (state, action) => {
        state.status = 'failed'
        state.error = action.error.message
      })
      .addCase(createInteraction.pending, (state) => {
        state.saving = true
        state.error = null
      })
      .addCase(createInteraction.fulfilled, (state, action) => {
        state.saving = false
        state.lastCreated = action.payload
        state.items.unshift(action.payload)
        state.draft = emptyDraft()
        state.aiFilled = []
      })
      .addCase(createInteraction.rejected, (state, action) => {
        state.saving = false
        state.error = action.error.message
      })
      // editInteraction has two callers: the Log Interaction form, and the
      // timeline's Edit modal (which has its own local saving state and its own
      // copy of the record). Only the form owns the draft and the shared
      // `saving` flag — a modal save must not clear the rep's half-written form
      // or freeze the form's submit button.
      .addCase(editInteraction.pending, (state, action) => {
        if (action.meta.arg.fromForm) state.saving = true
        state.error = null
      })
      .addCase(editInteraction.fulfilled, (state, action) => {
        const idx = state.items.findIndex((i) => i.id === action.payload.id)
        if (idx !== -1) state.items[idx] = action.payload
        if (!action.meta.arg.fromForm) return
        state.saving = false
        state.draft = emptyDraft()
        state.aiFilled = []
      })
      .addCase(editInteraction.rejected, (state, action) => {
        if (action.meta.arg.fromForm) state.saving = false
        state.error = action.error.message
      })
      .addCase(extractDraft.pending, (state) => {
        state.extracting = true
        state.error = null
      })
      .addCase(extractDraft.fulfilled, (state, action) => {
        state.extracting = false
        // A suggestion, not the truth — merge so it cannot wipe typed input.
        loadIntoDraft(state, action.payload, true)
      })
      .addCase(extractDraft.rejected, (state, action) => {
        state.extracting = false
        state.error = action.error.message
      })
  },
})

export const { clearLastCreated, setDraftField, applyDraft, resetDraft } =
  interactionsSlice.actions
export default interactionsSlice.reducer
