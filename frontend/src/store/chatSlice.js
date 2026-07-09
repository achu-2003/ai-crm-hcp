import { createAsyncThunk, createSlice } from '@reduxjs/toolkit'
import { api } from '../api/client'

export const sendMessage = createAsyncThunk(
  'chat/send',
  async ({ hcpId, text }, { getState }) => {
    const history = getState()
      .chat.messages.slice(-6)
      .map((m) => ({ role: m.role, content: m.text }))
    return api.chat({ hcp_id: hcpId, message: text, history })
  },
)

const chatSlice = createSlice({
  name: 'chat',
  initialState: { messages: [], sending: false, error: null },
  reducers: {
    pushUser(state, action) {
      state.messages.push({ role: 'user', text: action.payload, ts: Date.now() })
    },
    resetChat(state) {
      state.messages = []
    },
  },
  extraReducers: (builder) => {
    builder
      .addCase(sendMessage.pending, (state) => {
        state.sending = true
        state.error = null
      })
      .addCase(sendMessage.fulfilled, (state, action) => {
        state.sending = false
        const { reply, tool_used, tool_result } = action.payload
        state.messages.push({
          role: 'assistant',
          text: reply,
          tool: tool_used,
          result: tool_result,
          ts: Date.now(),
        })
      })
      .addCase(sendMessage.rejected, (state, action) => {
        state.sending = false
        state.error = action.error.message
        state.messages.push({
          role: 'assistant',
          text: `⚠️ ${action.error.message}`,
          ts: Date.now(),
        })
      })
  },
})

export const { pushUser, resetChat } = chatSlice.actions
export default chatSlice.reducer
