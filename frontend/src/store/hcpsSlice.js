import { createAsyncThunk, createSlice } from '@reduxjs/toolkit'
import { api } from '../api/client'

export const fetchHcps = createAsyncThunk('hcps/fetch', async () => {
  return api.listHcps()
})

export const createHcp = createAsyncThunk('hcps/create', async (payload) => {
  return api.createHcp(payload)
})

export const deleteHcp = createAsyncThunk('hcps/delete', async (id) => {
  await api.deleteHcp(id)
  return id
})

const hcpsSlice = createSlice({
  name: 'hcps',
  initialState: { items: [], selectedId: null, status: 'idle', error: null },
  reducers: {
    selectHcp(state, action) {
      state.selectedId = action.payload
    },
  },
  extraReducers: (builder) => {
    builder
      .addCase(fetchHcps.pending, (state) => {
        state.status = 'loading'
      })
      .addCase(fetchHcps.fulfilled, (state, action) => {
        state.status = 'succeeded'
        state.items = action.payload
        // Keep a valid selection: default to the first HCP, and if the
        // selected one vanished, fall back to the first (or none).
        const stillThere = action.payload.some((h) => h.id === state.selectedId)
        if (!stillThere) {
          state.selectedId = action.payload.length ? action.payload[0].id : null
        }
      })
      .addCase(fetchHcps.rejected, (state, action) => {
        state.status = 'failed'
        state.error = action.error.message
      })
      .addCase(createHcp.fulfilled, (state, action) => {
        state.items.push(action.payload)
        state.items.sort((a, b) => a.name.localeCompare(b.name))
        state.selectedId = action.payload.id // jump to the newly added HCP
      })
      .addCase(deleteHcp.fulfilled, (state, action) => {
        state.items = state.items.filter((h) => h.id !== action.payload)
        if (state.selectedId === action.payload) {
          state.selectedId = state.items.length ? state.items[0].id : null
        }
      })
  },
})

export const { selectHcp } = hcpsSlice.actions
export const selectSelectedHcp = (state) =>
  state.hcps.items.find((h) => h.id === state.hcps.selectedId) || null
export default hcpsSlice.reducer
