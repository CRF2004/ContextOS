import { useEffect, useState } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { api, RequestLog } from '../api/client'
import { ArrowLeft, ChevronDown, ChevronRight, Hash, Clock } from 'lucide-react'

function extractText(content: string | any[]): string {
  if (typeof content === 'string') return content
  if (Array.isArray(content)) {
    return content
      .filter(b => b.type === 'text')
      .map(b => b.text)
      .join('\n')
  }
  return ''
}

function extractPreview(content: string | any[] | undefined): string {
  if (!content) return ''
  const text = extractText(content)
  return text.slice(0, 300) + (text.length > 300 ? '...' : '')
}

export default function RequestLogsPage() {
  const { id } = useParams<{ id: string }>()
  const navigate = useNavigate()
  const [logs, setLogs] = useState<RequestLog[]>([])
  const [expanded, setExpanded] = useState<Set<number>>(new Set())
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    if (!id) return
    api.getRequestLogs(id, 100)
      .then(setLogs)
      .catch(console.error)
      .finally(() => setLoading(false))
  }, [id])

  const toggle = (logId: number) => {
    setExpanded(prev => {
      const next = new Set(prev)
      if (next.has(logId)) next.delete(logId)
      else next.add(logId)
      return next
    })
  }

  if (loading) return <div style={{ padding: 24, color: '#8b949e' }}>Loading...</div>

  return (
    <div style={{ padding: 24 }}>
      <div style={{ display: 'flex', alignItems: 'center', gap: 16, marginBottom: 24 }}>
        <button onClick={() => navigate(`/session/${id}`)} style={{
          background: 'none', border: 'none', color: '#8b949e', cursor: 'pointer',
          display: 'flex', alignItems: 'center', gap: 4, fontSize: 14,
        }}>
          <ArrowLeft size={16} /> Back
        </button>
        <h2 style={{ fontSize: 20, fontWeight: 600 }}>Request Logs</h2>
        <span style={{ fontSize: 13, color: '#8b949e' }}>
          {logs.length} request(s)
        </span>
      </div>

      {logs.length === 0 ? (
        <div style={{ textAlign: 'center', padding: 60, color: '#8b949e' }}>No request logs found</div>
      ) : (
        <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
          {logs.map(log => {
            const isExpanded = expanded.has(log.id)
            const msgPreview = log.messages.map(m =>
              `[${m.role}]: ${extractText(m.content).slice(0, 100)}`
            ).join('\n')
            const respPreview = extractPreview(log.response_content)

            return (
              <div key={log.id} style={{
                background: '#161b22', border: '1px solid #30363d', borderRadius: 8,
                overflow: 'hidden',
              }}>
                {/* Header */}
                <div onClick={() => toggle(log.id)} style={{
                  padding: '12px 16px', cursor: 'pointer', display: 'flex', alignItems: 'center',
                  gap: 12, userSelect: 'none',
                }}>
                  {isExpanded ? <ChevronDown size={16} color="#8b949e" /> : <ChevronRight size={16} color="#8b949e" />}
                  <div style={{ flex: 1, minWidth: 0 }}>
                    <div style={{ display: 'flex', alignItems: 'center', gap: 12, marginBottom: 4 }}>
                      <span style={{ fontSize: 13, fontWeight: 500, color: '#58a6ff' }}>
                        {log.request_id}
                      </span>
                      <span style={{ fontSize: 12, color: '#8b949e' }}>{log.model}</span>
                      <span style={{
                        fontSize: 12, padding: '1px 6px', borderRadius: 4,
                        background: 'rgba(88,166,255,0.1)', color: '#58a6ff',
                      }}>
                        {(log.token_breakdown.total_tokens / 1000).toFixed(1)}K tokens
                      </span>
                    </div>
                    <div style={{ fontSize: 12, color: '#8b949e', display: 'flex', gap: 16 }}>
                      <span style={{ display: 'flex', alignItems: 'center', gap: 4 }}>
                        <Clock size={11} /> {new Date(log.timestamp).toLocaleString('zh-CN')}
                      </span>
                      <span style={{ display: 'flex', alignItems: 'center', gap: 4 }}>
                        <Hash size={11} /> {log.messages.length} message(s)
                      </span>
                    </div>
                  </div>
                </div>

                {/* Expanded content */}
                {isExpanded && (
                  <div style={{ borderTop: '1px solid #30363d', padding: 16 }}>
                    {/* Messages */}
                    <div style={{ marginBottom: 12 }}>
                      <h4 style={{ fontSize: 12, fontWeight: 600, color: '#8b949e', marginBottom: 6 }}>Messages</h4>
                      <pre style={{
                        fontSize: 12, color: '#e1e4e8', background: '#0d1117', padding: 12,
                        borderRadius: 6, whiteSpace: 'pre-wrap', maxHeight: 200, overflow: 'auto',
                        lineHeight: 1.6,
                      }}>
                        {msgPreview}
                      </pre>
                    </div>

                    {/* Response */}
                    {respPreview && (
                      <div>
                        <h4 style={{ fontSize: 12, fontWeight: 600, color: '#8b949e', marginBottom: 6 }}>Response</h4>
                        <pre style={{
                          fontSize: 12, color: '#3fb950', background: '#0d1117', padding: 12,
                          borderRadius: 6, whiteSpace: 'pre-wrap', maxHeight: 200, overflow: 'auto',
                          lineHeight: 1.6,
                        }}>
                          {respPreview}
                        </pre>
                      </div>
                    )}
                  </div>
                )}
              </div>
            )
          })}
        </div>
      )}
    </div>
  )
}
