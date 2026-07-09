import { useEffect, useState } from 'react'
import { useDispatch } from 'react-redux'
import { fetchHcps } from './store/hcpsSlice'
import { api } from './api/client'
import HcpSidebar from './components/HcpSidebar'
import LogInteractionScreen from './components/LogInteractionScreen'

export default function App() {
  const dispatch = useDispatch()
  const [health, setHealth] = useState(null)

  useEffect(() => {
    dispatch(fetchHcps())
    api.health().then(setHealth).catch(() => setHealth({ status: 'down' }))
  }, [])

  return (
    <div className="app">
      <header className="topbar">
        <div className="brand-mark">M</div>
        <div>
          <div className="brand-name">Meridian CRM</div>
          <div className="brand-sub">AI-First · HCP Engagement Module</div>
        </div>
        <div className="topbar-spacer" />
        {health && (
          <>
            <span className={`pill-badge ${health.llm_configured ? '' : 'warn'}`}>
              {health.llm_configured ? '🟢' : '🟡'} {health.llm_model || 'LLM'}
              {!health.llm_configured && ' · offline'}
            </span>
            <span className="pill-badge">⚡ LangGraph agent</span>
          </>
        )}
      </header>
      <div className="workspace">
        <HcpSidebar />
        <LogInteractionScreen />
      </div>
    </div>
  )
}
