import { createAsyncThunk, createSlice } from '@reduxjs/toolkit'
import { api } from '../api/client'

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

const interactionsSlice = createSlice({
  name: 'interactions',
  initialState: { items: [], status: 'idle', saving: false, error: null, lastCreated: null },
  reducers: {
    clearLastCreated(state) {
      state.lastCreated = null
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
      })
      .addCase(createInteraction.rejected, (state, action) => {
        state.saving = false
        state.error = action.error.message
      })
      .addCase(editInteraction.fulfilled, (state, action) => {
        const idx = state.items.findIndex((i) => i.id === action.payload.id)
        if (idx !== -1) state.items[idx] = action.payload
      })
  },
})

export const { clearLastCreated } = interactionsSlice.actions
export default interactionsSlice.reducer
