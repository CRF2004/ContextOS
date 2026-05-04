import { useEffect, useState, useCallback } from 'react'
import ReactFlow, {
  Node, Edge, Background, Controls, MiniMap,
  MarkerType, Handle, Position,
} from 'reactflow'
import 'reactflow/dist/style.css'
import { useParams } from 'react-router-dom'
import { useNavigate } from 'react-router-dom'
import { api, ForkGraph, ForkNode } from '../api/client'

function SessionNode({ data }: { data: ForkNode & { onClick?: () => void } }) {
  const isCurrent = data.fork_point_time === data.fork_point_time
  return (
    <div onClick={data.onClick} style={{
      padding: '10px 16px', background: '#1c2128', border: '2px solid #30363d',
      borderRadius: 8, color: '#e1e4e8', minWidth: 180, cursor: 'pointer',
      transition: 'border-color 0.2s',
    }}
      onMouseEnter={e => e.currentTarget.style.borderColor = '#58a6ff'}
      onMouseLeave={e => e.currentTarget.style.borderColor = '#30363d'}
    >
      <Handle type="target" position={Position.Top} />
      <div style={{ fontSize: 13, fontWeight: 600, marginBottom: 4 }}>
        {data.name || data.session_id.slice(-8)}
      </div>
      <div style={{ fontSize: 11, color: '#8b949e', display: 'flex', justifyContent: 'space-between' }}>
        <span>{data.session_id.slice(-8)}</span>
        <span>{(data.fork_point_token / 1000).toFixed(1)}K tokens</span>
      </div>
      {data.children.length > 0 && (
        <div style={{ fontSize: 10, color: '#58a6ff', marginTop: 4 }}>
          {data.children.length} child(ren)
        </div>
      )}
      <Handle type="source" position={Position.Bottom} />
    </div>
  )
}

const nodeTypes = { session: SessionNode }

export default function ForkGraphPage() {
  const { sessionId } = useParams<{ sessionId: string }>()
  const navigate = useNavigate()
  const [graph, setGraph] = useState<ForkGraph | null>(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    // If no sessionId, fetch the latest session
    if (!sessionId) {
      api.listSessions(1).then(sessions => {
        if (sessions.length > 0) {
          loadGraph(sessions[0].session_id)
        } else {
          setLoading(false)
        }
      })
    } else {
      loadGraph(sessionId)
    }
  }, [sessionId])

  const loadGraph = (sid: string) => {
    api.getForkGraph(sid)
      .then(setGraph)
      .catch(console.error)
      .finally(() => setLoading(false))
  }

  const nodes: Node[] = graph ? graph.nodes.map((n, i) => {
    const row = Math.floor(i / 2)
    const col = i % 2
    return {
      id: n.session_id,
      type: 'session',
      position: { x: col * 250 + 100, y: row * 150 + 50 },
      data: {
        ...n,
        onClick: () => navigate(`/session/${n.session_id}`),
      },
    }
  }) : []

  const edges: Edge[] = graph ? graph.edges.map(([parent, child]) => ({
    id: `${parent}-${child}`,
    source: parent,
    target: child,
    type: 'smoothstep',
    animated: true,
    markerEnd: { type: MarkerType.ArrowClosed, width: 20, height: 20 },
    style: { stroke: '#58a6ff', strokeWidth: 2 },
  })) : []

  if (loading) return <div style={{ padding: 24, color: '#8b949e' }}>Loading fork graph...</div>
  if (!graph || graph.nodes.length === 0) {
    return <div style={{ padding: 24, color: '#8b949e' }}>No fork data available</div>
  }

  return (
    <div style={{ height: 'calc(100vh - 40px)', padding: 24, display: 'flex', flexDirection: 'column' }}>
      <h2 style={{ fontSize: 20, fontWeight: 600, marginBottom: 16 }}>
        Fork Graph — {graph.nodes.length} session(s)
      </h2>
      <div style={{ flex: 1, background: '#0f1117', borderRadius: 8, border: '1px solid #30363d' }}>
        <ReactFlow
          nodes={nodes}
          edges={edges}
          nodeTypes={nodeTypes}
          fitView
          fitViewOptions={{ padding: 0.2 }}
        >
          <Background color="#30363d" gap={16} />
          <Controls />
          <MiniMap
            nodeStrokeColor="#58a6ff"
            nodeColor="#1c2128"
            maskColor="rgba(15,17,23,0.8)"
          />
        </ReactFlow>
      </div>
    </div>
  )
}
