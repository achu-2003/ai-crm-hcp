import { configureStore } from '@reduxjs/toolkit'
import hcps from './hcpsSlice'
import interactions from './interactionsSlice'
import chat from './chatSlice'
import followups from './followupsSlice'
import dashboard from './dashboardSlice'

export const store = configureStore({
  reducer: { hcps, interactions, chat, followups, dashboard },
})
