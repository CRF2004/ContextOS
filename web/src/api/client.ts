const API_BASE = (import.meta as any).env?.VITE_API_BASE || '/api'

async function request<T>(path: string, options?: RequestInit): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`, {
    headers: { 'Content-Type': 'application/json' },
    ...options,
  })
  if (!res.ok) {
    throw new Error(`${res.status} ${res.statusText}`)
  }
  return res.json()
}

export interface Session {
  session_id: string
  name: string | null
  status: string
  parent_session_id: string | null
  total_tokens: number
  created_at: string
  updated_at: string
  metadata: Record<string, any>
}

export interface TokenSummary {
  session_id: string
  total_tokens: number
  total_requests: number
  total_prompt_tokens: number
  total_completion_tokens: number
  total_mcp_tokens: number
  total_skill_tokens: number
  total_system_tokens: number
}

export interface TokenRecord {
  id: number
  session_id: string
  request_id: string
  timestamp: string
  model: string
  token_breakdown: {
    total_tokens: number
    prompt_tokens: number
    completion_tokens: number
    mcp_tokens: number
    skill_tokens: number
    system_tokens: number
  }
}

export interface RequestLog {
  id: number
  session_id: string
  request_id: string
  timestamp: string
  model: string
  messages: { role: string; content: string | any[] }[]
  token_breakdown: {
    total_tokens: number
    prompt_tokens: number
    completion_tokens: number
  }
  response_content?: string | any[]
  tools?: any[]
  system?: any
}

export interface ForkNode {
  session_id: string
  name: string | null
  parent_session_id: string | null
  fork_point_token: number
  fork_point_time: string
  children: string[]
}

export interface ForkGraph {
  nodes: ForkNode[]
  edges: [string, string][]
}

// Sessions
export const api = {
  listSessions: (limit = 50, offset = 0) =>
    request<Session[]>(`/sessions?limit=${limit}&offset=${offset}`),

  getSession: (id: string) =>
    request<Session>(`/sessions/${id}`),

  createSession: (name?: string) =>
    request<Session>('/sessions', {
      method: 'POST',
      body: JSON.stringify({ name }),
    }),

  archiveSession: (id: string) =>
    request<{ status: string }>(`/sessions/${id}/archive`, { method: 'POST' }),

  // Tokens
  getTokenSummary: (id: string) =>
    request<TokenSummary>(`/sessions/${id}/tokens`),

  getTokenHistory: (id: string, limit = 100, offset = 0) =>
    request<TokenRecord[]>(`/sessions/${id}/tokens/history?limit=${limit}&offset=${offset}`),

  // Requests
  getRequestLogs: (id: string, limit = 50, offset = 0) =>
    request<RequestLog[]>(`/sessions/${id}/requests?limit=${limit}&offset=${offset}`),

  // Fork
  forkSession: (id: string, name?: string) =>
    request<Session>(`/sessions/${id}/fork`, {
      method: 'POST',
      body: JSON.stringify({ session_id: id, name }),
    }),

  getForkGraph: (id: string) =>
    request<ForkGraph>(`/sessions/${id}/fork-graph`),

  // Proxy
  proxyMessages: (sessionId: string, body: any) =>
    request<any>(`/proxy/messages?session_id=${sessionId}`, {
      method: 'POST',
      body: JSON.stringify(body),
    }),
}
