import { BrowserRouter, Routes, Route, Link, useLocation } from 'react-router-dom'
import { LayoutDashboard, GitBranch, Terminal, FileText } from 'lucide-react'
import SessionListPage from './pages/SessionListPage'
import SessionDetailPage from './pages/SessionDetailPage'
import ForkGraphPage from './pages/ForkGraphPage'
import RequestLogsPage from './pages/RequestLogsPage'

function Layout({ children }: { children: React.ReactNode }) {
  const location = useLocation()
  const navs = [
    { path: '/', label: 'Sessions', icon: <LayoutDashboard size={18} /> },
    { path: '/forks', label: 'Fork Graph', icon: <GitBranch size={18} /> },
  ]
  return (
    <div style={{ display: 'flex', minHeight: '100vh' }}>
      {/* Sidebar */}
      <div style={{
        width: 220, background: '#161b22', borderRight: '1px solid #30363d',
        padding: '20px 0', display: 'flex', flexDirection: 'column',
      }}>
        <div style={{ padding: '0 16px 20px', borderBottom: '1px solid #30363d', marginBottom: 12 }}>
          <h1 style={{ fontSize: 18, fontWeight: 700, color: '#58a6ff' }}>⚡ ContextOS</h1>
          <p style={{ fontSize: 11, color: '#8b949e', marginTop: 4 }}>Context Operating System</p>
        </div>
        {navs.map(n => (
          <Link key={n.path} to={n.path} style={{
            display: 'flex', alignItems: 'center', gap: 10, padding: '10px 16px',
            color: location.pathname === n.path ? '#58a6ff' : '#8b949e',
            textDecoration: 'none', borderLeft: location.pathname === n.path ? '3px solid #58a6ff' : '3px solid transparent',
            background: location.pathname === n.path ? 'rgba(56,139,253,0.1)' : 'transparent',
            fontSize: 14, fontWeight: location.pathname === n.path ? 600 : 400,
          }}>
            {n.icon}
            {n.label}
          </Link>
        ))}
      </div>
      <div style={{ flex: 1, overflow: 'auto' }}>
        {children}
      </div>
    </div>
  )
}

export default function App() {
  return (
    <BrowserRouter>
      <Layout>
        <Routes>
          <Route path="/" element={<SessionListPage />} />
          <Route path="/session/:id" element={<SessionDetailPage />} />
          <Route path="/session/:id/logs" element={<RequestLogsPage />} />
          <Route path="/forks/:sessionId?" element={<ForkGraphPage />} />
        </Routes>
      </Layout>
    </BrowserRouter>
  )
}
