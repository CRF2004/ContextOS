import { useEffect, useState } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { api, TokenSummary, TokenRecord, Session } from '../api/client'
import {
  BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer,
  PieChart, Pie, Cell,
} from 'recharts'
import { ArrowLeft, ArrowRight, GitBranch, FileText, Activity } from 'lucide-react'

const COLORS = ['#58a6ff', '#3fb950', '#f0883e', '#f778ba', '#bc8cff', '#8b949e']

export default function SessionDetailPage() {
  const { id } = useParams<{ id: string }>()
  const navigate = useNavigate()
  const [session, setSession] = useState<Session | null>(null)
  const [summary, setSummary] = useState<TokenSummary | null>(null)
  const [history, setHistory] = useState<TokenRecord[]>([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    if (!id) return
    Promise.all([
      api.getSession(id),
      api.getTokenSummary(id),
      api.getTokenHistory(id, 50),
    ]).then(([s, sum, hist]) => {
      setSession(s)
      setSummary(sum)
      setHistory(hist.reverse())
    }).catch(console.error).finally(() => setLoading(false))
  }, [id])

  if (loading) return <div style={{ padding: 24, color: '#8b949e' }}>Loading...</div>
  if (!session) return <div style={{ padding: 24 }}>Session not found</div>

  const pieData = [
    { name: 'Prompt', value: summary?.total_prompt_tokens || 0 },
    { name: 'Completion', value: summary?.total_completion_tokens || 0 },
    { name: 'MCP Tools', value: summary?.total_mcp_tokens || 0 },
    { name: 'Skill', value: summary?.total_skill_tokens || 0 },
    { name: 'System', value: summary?.total_system_tokens || 0 },
  ].filter(d => d.value > 0)

  const chartData = history.map(h => ({
    name: h.request_id.slice(-6),
    time: new Date(h.timestamp).toLocaleTimeString('zh-CN', { hour: '2-digit', minute: '2-digit' }),
    prompt: h.token_breakdown.prompt_tokens,
    completion: h.token_breakdown.completion_tokens,
    total: h.token_breakdown.total_tokens,
  }))

  const totalSum = pieData.reduce((a, b) => a + b.value, 0)

  return (
    <div style={{ padding: 24 }}>
      {/* Header */}
      <div style={{ display: 'flex', alignItems: 'center', gap: 16, marginBottom: 24 }}>
        <button onClick={() => navigate('/')} style={{
          background: 'none', border: 'none', color: '#8b949e', cursor: 'pointer',
          display: 'flex', alignItems: 'center', gap: 4, fontSize: 14,
        }}>
          <ArrowLeft size={16} /> Back
        </button>
        <h2 style={{ fontSize: 20, fontWeight: 600 }}>{session.name || session.session_id}</h2>
        <span style={{
          fontSize: 12, padding: '2px 8px', borderRadius: 12,
          background: session.status === 'active' ? 'rgba(63,185,80,0.15)' : 'rgba(139,148,158,0.15)',
          color: session.status === 'active' ? '#3fb950' : '#8b949e',
        }}>
          {session.status}
        </span>
        <div style={{ marginLeft: 'auto', display: 'flex', gap: 8 }}>
          <button onClick={() => navigate(`/session/${id}/logs`)} style={{
            display: 'flex', alignItems: 'center', gap: 6, padding: '8px 16px',
            background: '#21262d', color: '#e1e4e8', border: '1px solid #30363d',
            borderRadius: 6, cursor: 'pointer', fontSize: 13,
          }}>
            <FileText size={14} /> Logs
          </button>
          <button onClick={() => navigate(`/forks/${id}`)} style={{
            display: 'flex', alignItems: 'center', gap: 6, padding: '8px 16px',
            background: '#21262d', color: '#e1e4e8', border: '1px solid #30363d',
            borderRadius: 6, cursor: 'pointer', fontSize: 13,
          }}>
            <GitBranch size={14} /> Fork Graph
          </button>
        </div>
      </div>

      {/* Stats Cards */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: 16, marginBottom: 24 }}>
        {[
          { label: 'Total Tokens', value: `${(totalSum / 1000).toFixed(1)}K`, icon: <Activity size={18} /> },
          { label: 'Requests', value: `${summary?.total_requests || 0}`, icon: <FileText size={18} /> },
          { label: 'Prompt', value: `${((summary?.total_prompt_tokens || 0) / 1000).toFixed(1)}K` },
          { label: 'Completion', value: `${((summary?.total_completion_tokens || 0) / 1000).toFixed(1)}K` },
        ].map((card, i) => (
          <div key={i} style={{
            background: '#161b22', border: '1px solid #30363d', borderRadius: 8, padding: 16,
          }}>
            <div style={{ fontSize: 12, color: '#8b949e', marginBottom: 8, display: 'flex', alignItems: 'center', gap: 6 }}>
              {card.icon} {card.label}
            </div>
            <div style={{ fontSize: 22, fontWeight: 700 }}>{card.value}</div>
          </div>
        ))}
      </div>

      {/* Charts */}
      <div style={{ display: 'grid', gridTemplateColumns: '2fr 1fr', gap: 16, marginBottom: 24 }}>
        {/* Token History */}
        <div style={{
          background: '#161b22', border: '1px solid #30363d', borderRadius: 8, padding: 16,
          height: 320,
        }}>
          <h3 style={{ fontSize: 14, fontWeight: 600, marginBottom: 12 }}>Token Usage Over Requests</h3>
          <ResponsiveContainer width="100%" height="85%">
            <BarChart data={chartData}>
              <XAxis dataKey="time" tick={{ fontSize: 10, fill: '#8b949e' }} />
              <YAxis tick={{ fontSize: 10, fill: '#8b949e' }} />
              <Tooltip
                contentStyle={{ background: '#1c2128', border: '1px solid #30363d', borderRadius: 6 }}
                labelStyle={{ color: '#e1e4e8' }}
              />
              <Bar dataKey="prompt" stackId="a" fill="#58a6ff" name="Prompt" />
              <Bar dataKey="completion" stackId="a" fill="#3fb950" name="Completion" />
            </BarChart>
          </ResponsiveContainer>
        </div>

        {/* Token Pie */}
        <div style={{
          background: '#161b22', border: '1px solid #30363d', borderRadius: 8, padding: 16,
          height: 320,
        }}>
          <h3 style={{ fontSize: 14, fontWeight: 600, marginBottom: 8 }}>Token Breakdown</h3>
          <ResponsiveContainer width="100%" height="80%">
            <PieChart>
              <Pie
                data={pieData}
                cx="50%"
                cy="50%"
                innerRadius={50}
                outerRadius={80}
                paddingAngle={2}
                dataKey="value"
                label={({ name, percent }) => `${name} ${(percent * 100).toFixed(0)}%`}
              >
                {pieData.map((_, i) => (
                  <Cell key={i} fill={COLORS[i % COLORS.length]} />
                ))}
              </Pie>
              <Tooltip contentStyle={{ background: '#1c2128', border: '1px solid #30363d', borderRadius: 6 }} />
            </PieChart>
          </ResponsiveContainer>
        </div>
      </div>

      {/* Session Info */}
      <div style={{
        background: '#161b22', border: '1px solid #30363d', borderRadius: 8, padding: 16,
      }}>
        <h3 style={{ fontSize: 14, fontWeight: 600, marginBottom: 12 }}>Session Info</h3>
        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 8, fontSize: 13 }}>
          <div><span style={{ color: '#8b949e' }}>ID:</span> {session.session_id}</div>
          <div><span style={{ color: '#8b949e' }}>Created:</span> {session.created_at}</div>
          <div><span style={{ color: '#8b949e' }}>Updated:</span> {session.updated_at}</div>
          {session.parent_session_id && (
            <div>
              <span style={{ color: '#8b949e' }}>Parent:</span>{' '}
              <span
                style={{ color: '#58a6ff', cursor: 'pointer' }}
                onClick={() => navigate(`/session/${session.parent_session_id}`)}
              >
                {session.parent_session_id}
              </span>
            </div>
          )}
        </div>
      </div>
    </div>
  )
}
