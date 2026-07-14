import { createAsyncThunk, createSlice } from '@reduxjs/toolkit'
import { api } from '../api/client'

// Aggregated metrics for the Dashboard view (GET /api/v1/stats).
export const fetchStats = createAsyncThunk('dashboard/fetch', async () => api.stats())

const dashboardSlice = createSlice({
  name: 'dashboard',
  initialState: { stats: null, status: 'idle', error: null },
  extraReducers: (builder) => {
    builder
      .addCase(fetchStats.pending, (state) => {
        state.status = 'loading'
      })
      .addCase(fetchStats.fulfilled, (state, action) => {
        state.status = 'succeeded'
        state.stats = action.payload
      })
      .addCase(fetchStats.rejected, (state, action) => {
        state.status = 'failed'
        state.error = action.error.message
      })
  },
})

export default dashboardSlice.reducer
