import { configureStore } from '@reduxjs/toolkit'
import hcps from './hcpsSlice'
import interactions from './interactionsSlice'
import chat from './chatSlice'

export const store = configureStore({
  reducer: { hcps, interactions, chat },
})
