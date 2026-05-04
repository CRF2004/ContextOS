import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { api, Session } from '../api/client'
import { Plus, Archive, ExternalLink, Clock, Hash } from 'lucide-react'

export default function SessionListPage() {
  const navigate = useNavigate()
  const [sessions, setSessions] = useState<Session[]>([])
  const [loading, setLoading] = useState(true)
  const [creating, setCreating] = useState(false)

  const load = () => {
    api.listSessions()
      .then(setSessions)
      .catch(err => console.error('Failed to load sessions:', err))
      .finally(() => setLoading(false))
  }

  useEffect(() => { load() }, [])

  const handleCreate = async () => {
    setCreating(true)
    try {
      const s = await api.createSession('New Session')
      load()
      navigate(`/session/${s.session_id}`)
    } catch (e) {
      console.error(e)
    } finally {
      setCreating(false)
    }
  }

  const statusColor: Record<string, string> = {
    active: '#3fb950',
    archived: '#8b949e',
    forked: '#d29922',
  }

  return (
    <div style={{ padding: 24 }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 24 }}>
        <h2 style={{ fontSize: 20, fontWeight: 600 }}>Sessions</h2>
        <button onClick={handleCreate} disabled={creating} style={{
          display: 'flex', alignItems: 'center', gap: 6, padding: '8px 16px',
          background: '#238636', color: '#fff', border: 'none', borderRadius: 6,
          cursor: creating ? 'not-allowed' : 'pointer', fontSize: 14, fontWeight: 500,
        }}>
          <Plus size={16} /> New Session
        </button>
      </div>

      {loading ? (
        <div style={{ textAlign: 'center', padding: 60, color: '#8b949e' }}>Loading...</div>
      ) : sessions.length === 0 ? (
        <div style={{ textAlign: 'center', padding: 60, color: '#8b949e' }}>
          No sessions yet. Create one to get started.
        </div>
      ) : (
        <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
          {sessions.map(s => (
            <div key={s.session_id} style={{
              background: '#161b22', border: '1px solid #30363d', borderRadius: 8,
              padding: 16, display: 'flex', alignItems: 'center', gap: 16,
              cursor: 'pointer', transition: 'border-color 0.15s',
            }}
              onClick={() => navigate(`/session/${s.session_id}`)}
              onMouseEnter={e => (e.currentTarget.style.borderColor = '#58a6ff')}
              onMouseLeave={e => (e.currentTarget.style.borderColor = '#30363d')}
            >
              <div style={{
                width: 10, height: 10, borderRadius: '50%',
                background: statusColor[s.status] || '#8b949e', flexShrink: 0,
              }} />
              <div style={{ flex: 1, minWidth: 0 }}>
                <div style={{ fontSize: 15, fontWeight: 500, marginBottom: 4 }}>
                  {s.name || s.session_id}
                </div>
                <div style={{ fontSize: 12, color: '#8b949e', display: 'flex', gap: 16 }}>
                  <span style={{ display: 'flex', alignItems: 'center', gap: 4 }}>
                    <Hash size={12} /> {s.session_id}
                  </span>
                  {s.parent_session_id && (
                    <span style={{ display: 'flex', alignItems: 'center', gap: 4 }}>
                      forked from {s.parent_session_id.slice(-8)}
                    </span>
                  )}
                </div>
              </div>
              <div style={{ textAlign: 'right', flexShrink: 0 }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: 6, marginBottom: 4 }}>
                  <Hash size={12} color="#8b949e" />
                  <span style={{ fontSize: 15, fontWeight: 600 }}>
                    {(s.total_tokens / 1000).toFixed(1)}K
                  </span>
                  <span style={{ fontSize: 11, color: '#8b949e' }}>tokens</span>
                </div>
                <div style={{ fontSize: 11, color: '#8b949e', display: 'flex', alignItems: 'center', gap: 4, justifyContent: 'flex-end' }}>
                  <Clock size={12} />
                  {new Date(s.updated_at).toLocaleString('zh-CN')}
                </div>
              </div>
              <ExternalLink size={14} color="#8b949e" />
            </div>
          ))}
        </div>
      )}
    </div>
  )
}
