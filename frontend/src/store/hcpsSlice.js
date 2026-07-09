import { createAsyncThunk, createSlice } from '@reduxjs/toolkit'
import { api } from '../api/client'

export const fetchHcps = createAsyncThunk('hcps/fetch', async () => {
  return api.listHcps()
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
        if (state.selectedId == null && action.payload.length) {
          state.selectedId = action.payload[0].id
        }
      })
      .addCase(fetchHcps.rejected, (state, action) => {
        state.status = 'failed'
        state.error = action.error.message
      })
  },
})

export const { selectHcp } = hcpsSlice.actions
export const selectSelectedHcp = (state) =>
  state.hcps.items.find((h) => h.id === state.hcps.selectedId) || null
export default hcpsSlice.reducer
