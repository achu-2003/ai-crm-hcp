import { createAsyncThunk, createSlice } from '@reduxjs/toolkit'
import { api } from '../api/client'

// Follow-ups for the currently selected HCP — created by the schedule_followup
// agent tool and surfaced here as the rep's next-best-action list.
export const fetchFollowups = createAsyncThunk('followups/fetch', async (hcpId) =>
  api.listFollowups(hcpId),
)

export const completeFollowup = createAsyncThunk('followups/complete', async (id) =>
  api.updateFollowup(id, { status: 'done' }),
)

const followupsSlice = createSlice({
  name: 'followups',
  initialState: { items: [], status: 'idle', error: null },
  extraReducers: (builder) => {
    builder
      .addCase(fetchFollowups.pending, (state) => {
        state.status = 'loading'
      })
      .addCase(fetchFollowups.fulfilled, (state, action) => {
        state.status = 'succeeded'
        state.items = action.payload
      })
      .addCase(fetchFollowups.rejected, (state, action) => {
        state.status = 'failed'
        state.error = action.error.message
      })
      .addCase(completeFollowup.fulfilled, (state, action) => {
        const idx = state.items.findIndex((f) => f.id === action.payload.id)
        if (idx !== -1) state.items[idx] = action.payload
      })
  },
})

export default followupsSlice.reducer
