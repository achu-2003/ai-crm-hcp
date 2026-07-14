import { useEffect, useState } from 'react'
import { useDispatch } from 'react-redux'
import { fetchHcps } from './store/hcpsSlice'
import { api } from './api/client'
import HcpSidebar from './components/HcpSidebar'
import LogInteractionScreen from './components/LogInteractionScreen'
import Dashboard from './components/Dashboard'

const NAV = [
  { key: 'dashboard', label: 'Dashboard', icon: '📊' },
  { key: 'log', label: 'Log Interaction', icon: '📝' },
]

export default function App() {
  const dispatch = useDispatch()
  const [health, setHealth] = useState(null)
  const [view, setView] = useState('log')

  useEffect(() => {
    dispatch(fetchHcps())
    api.health().then(setHealth).catch(() => setHealth({ status: 'down' }))
  }, [])

  return (
    <div className="app">
      <header className="topbar">
        <div className="brand-mark">M</div>
        <div className="brand-block">
          <div className="brand-name">Meridian CRM</div>
          <div className="brand-sub">AI-First · HCP Engagement</div>
        </div>

        <nav className="nav">
          {NAV.map((n) => (
            <button
              key={n.key}
              className={`nav-item ${view === n.key ? 'active' : ''}`}
              onClick={() => setView(n.key)}
            >
              <span className="nav-icon">{n.icon}</span>
              {n.label}
            </button>
          ))}
        </nav>

        <div className="topbar-spacer" />
        {health && (
          <div className="badges">
            <span className={`pill-badge ${health.llm_configured ? 'ok' : 'warn'}`}>
              <span className="dot" />
              {health.llm_model || 'LLM'}
              {!health.llm_configured && ' · offline'}
            </span>
            <span className="pill-badge muted">⚡ LangGraph</span>
          </div>
        )}
      </header>

      <div className="workspace">
        <HcpSidebar />
        {view === 'dashboard' ? (
          <Dashboard onLogClick={() => setView('log')} />
        ) : (
          <LogInteractionScreen />
        )}
      </div>
    </div>
  )
}
