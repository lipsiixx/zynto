import { useEffect, useRef, useState, useCallback, useMemo } from 'react'
import ForceGraph2D from 'react-force-graph-2d'
import type { NetworkGraph as NetworkGraphType, NetworkNode } from '../types'
import { getNetworkGraph } from '../api'
import { useApp } from '../App'

// ── Internal graph types (extend NetworkNode with simulation coords) ──────────

interface FGNode extends NetworkNode {
  x?: number
  y?: number
  vx?: number
  vy?: number
  fx?: number
  fy?: number
}

interface FGLink {
  source: string | FGNode
  target: string | FGNode
  weight: number
  trust_score: number | null
  strength: number
}

// ── Canvas helpers ────────────────────────────────────────────────────────────

function nodeColor(n: FGNode): string {
  if (n.type === 'self') return '#7c3aed'
  const s = n.strength
  if (s >= 0.8) return '#a78bfa'
  if (s >= 0.6) return '#7c3aed'
  if (s >= 0.4) return '#4c1d95'
  if (s >= 0.2) return '#3d2a6e'
  return '#2a1d4a'
}

function nodeRadius(n: FGNode): number {
  if (n.type === 'self') return 18
  return 5 + n.strength * 10
}

function linkColor(l: FGLink): string {
  const s = l.strength
  if (s >= 0.7) return 'rgba(167,139,250,0.6)'
  if (s >= 0.4) return 'rgba(124,58,237,0.4)'
  return 'rgba(90,82,114,0.25)'
}

// ── Component ─────────────────────────────────────────────────────────────────

export function NetworkGraph() {
  const { showToast } = useApp()

  const [graphData, setGraphData] = useState<NetworkGraphType | null>(null)
  const [loading, setLoading] = useState(true)
  const [selectedNode, setSelectedNode] = useState<FGNode | null>(null)

  const graphContainerRef = useRef<HTMLDivElement>(null)
  const [graphDims, setGraphDims] = useState({ width: 300, height: 500 })
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  const fgRef = useRef<any>(null)

  // Load graph on mount
  useEffect(() => {
    setLoading(true)
    getNetworkGraph()
      .then((data) => setGraphData(data))
      .catch(() => showToast('Ошибка загрузки графа', 'error'))
      .finally(() => setLoading(false))
  }, [showToast])

  // Spread nodes apart: strong repulsion + longer link distance
  useEffect(() => {
    if (!fgRef.current || !graphData) return
    fgRef.current.d3Force('charge')?.strength(-400)
    fgRef.current.d3Force('link')?.distance(120)
    fgRef.current.d3ReheatSimulation()
  }, [graphData])

  // Measure container for ForceGraph2D dimensions
  useEffect(() => {
    const el = graphContainerRef.current
    if (!el) return
    const obs = new ResizeObserver((entries) => {
      const rect = entries[0]?.contentRect
      if (rect && rect.width > 0 && rect.height > 0) {
        setGraphDims({ width: Math.floor(rect.width), height: Math.floor(rect.height) })
      }
    })
    obs.observe(el)
    return () => obs.disconnect()
  }, [])

  // ── ForceGraph2D callbacks ───────────────────────────────────────────────────

  const fgData = useMemo(
    () => ({
      nodes: (graphData?.nodes ?? []) as FGNode[],
      links: (graphData?.edges ?? []).map((e) => ({
        source: e.source,
        target: e.target,
        weight: e.weight,
        trust_score: e.trust_score,
        strength: e.strength,
      })) as FGLink[],
    }),
    [graphData],
  )

  const nodeCanvasObject = useCallback((node: object, ctx: CanvasRenderingContext2D) => {
    const n = node as FGNode
    const x = n.x ?? 0
    const y = n.y ?? 0
    const r = nodeRadius(n)
    const fill = nodeColor(n)

    // Glow for self node and strong contacts
    if (n.type === 'self' || n.strength > 0.6) {
      ctx.shadowBlur = n.type === 'self' ? 20 : n.strength * 15
      ctx.shadowColor = '#7c3aed'
    }

    ctx.beginPath()
    ctx.arc(x, y, r, 0, 2 * Math.PI)
    ctx.fillStyle = fill
    ctx.fill()

    // Reset shadow
    ctx.shadowBlur = 0

    // Letter inside large enough nodes
    if (r >= 8) {
      ctx.font = `bold ${Math.floor(r * 0.7)}px sans-serif`
      ctx.textAlign = 'center'
      ctx.textBaseline = 'middle'
      ctx.fillStyle = 'rgba(255,255,255,0.9)'
      ctx.fillText(n.label.charAt(0).toUpperCase(), x, y)
    }
  }, [])

  const nodePointerAreaPaint = useCallback(
    (node: object, color: string, ctx: CanvasRenderingContext2D) => {
      const n = node as FGNode
      const x = n.x ?? 0
      const y = n.y ?? 0
      ctx.fillStyle = color
      ctx.beginPath()
      ctx.arc(x, y, nodeRadius(n) + 4, 0, 2 * Math.PI)
      ctx.fill()
    },
    [],
  )

  const getLinkColor = useCallback((link: object) => linkColor(link as FGLink), [])

  const getLinkWidth = useCallback((link: object) => {
    const l = link as FGLink
    return 1 + l.strength * 3
  }, [])

  const getLinkParticleWidth = useCallback((link: object) => {
    const l = link as FGLink
    return l.strength > 0.5 ? 2 : 0
  }, [])

  const handleNodeClick = useCallback((node: object) => {
    setSelectedNode(node as FGNode)
  }, [])

  // ── Render: loading ──────────────────────────────────────────────────────────

  if (loading) {
    return (
      <div className="loading-center" style={{ flex: 1 }}>
        <div className="spinner" />
      </div>
    )
  }

  const contactCount = (graphData?.nodes.length ?? 0) - 1
  const hasContacts = contactCount > 0

  // ── Render ───────────────────────────────────────────────────────────────────

  return (
    <div
      style={{
        flex: 1,
        display: 'flex',
        flexDirection: 'column',
        overflow: 'hidden',
      }}
    >
      {/* Top bar */}
      <div
        style={{
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          padding: '10px 16px',
          background: 'rgba(13,13,20,0.9)',
          backdropFilter: 'blur(12px)',
          WebkitBackdropFilter: 'blur(12px)',
          borderBottom: '1px solid var(--purple-border)',
          flexShrink: 0,
          zIndex: 10,
        }}
      >
        <div>
          <span style={{ fontWeight: 700, fontSize: 16 }}>Мои связи</span>
          {graphData && (
            <span style={{ fontSize: 12, color: 'var(--text2)', marginLeft: 8 }}>
              {contactCount} контактов
            </span>
          )}
        </div>
      </div>

      {/* Graph area — paddingBottom чтобы граф не уходил под fixed nav */}
      <div
        ref={graphContainerRef}
        style={{ flex: 1, position: 'relative', overflow: 'hidden', background: '#0d0d14', paddingBottom: 'var(--nav-total)' }}
      >
        {!hasContacts ? (
          <div
            style={{
              display: 'flex',
              flexDirection: 'column',
              alignItems: 'center',
              justifyContent: 'center',
              height: '100%',
              padding: 24,
              textAlign: 'center',
            }}
          >
            <div style={{ fontSize: 56, marginBottom: 16 }}>🌌</div>
            <div style={{ fontWeight: 700, fontSize: 18, marginBottom: 8 }}>Нет данных</div>
            <div style={{ color: 'var(--text2)', fontSize: 14, textAlign: 'center', lineHeight: 1.5 }}>
              Здесь будут отображаться ваши контакты после первых перехваченных сообщений
            </div>
          </div>
        ) : (
          graphDims.width > 0 && graphDims.height > 0 && (
            <ForceGraph2D
              ref={fgRef}
              graphData={fgData}
              width={graphDims.width}
              height={graphDims.height}
              backgroundColor="#0d0d14"
              nodeCanvasObject={nodeCanvasObject}
              nodePointerAreaPaint={nodePointerAreaPaint}
              nodeLabel={() => ''}
              linkColor={getLinkColor}
              linkWidth={getLinkWidth}
              onNodeClick={handleNodeClick}
              cooldownTicks={100}
              d3AlphaDecay={0.02}
              d3VelocityDecay={0.3}
              linkDirectionalParticles={2}
              linkDirectionalParticleWidth={getLinkParticleWidth}
              linkDirectionalParticleColor={() => 'rgba(167,139,250,0.8)'}
            />
          )
        )}
      </div>

      {/* Node detail bottom sheet */}
      {selectedNode && (
        <div
          style={{
            position: 'fixed',
            inset: 0,
            background: 'rgba(0,0,0,0.55)',
            zIndex: 200,
            display: 'flex',
            alignItems: 'flex-end',
          }}
          onClick={() => setSelectedNode(null)}
        >
          <div
            style={{
              background: 'var(--bg-card)',
              borderRadius: '20px 20px 0 0',
              border: '1px solid var(--purple-border)',
              padding: '16px 20px',
              paddingBottom: 'calc(var(--nav-total) + 20px)',
              width: '100%',
              maxHeight: '60vh',
              overflow: 'auto',
            }}
            onClick={(e) => e.stopPropagation()}
          >
            {/* Drag handle */}
            <div
              style={{
                width: 36,
                height: 4,
                background: 'var(--text3)',
                borderRadius: 2,
                margin: '0 auto 20px',
              }}
            />

            {/* Header */}
            <div style={{ display: 'flex', alignItems: 'center', gap: 14, marginBottom: 16 }}>
              <div
                style={{
                  width: 48,
                  height: 48,
                  borderRadius: '50%',
                  background: nodeColor(selectedNode),
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  fontSize: 20,
                  fontWeight: 700,
                  color: '#fff',
                  flexShrink: 0,
                  boxShadow: selectedNode.type === 'self' || selectedNode.strength > 0.6
                    ? '0 0 12px rgba(124,58,237,0.5)'
                    : 'none',
                }}
              >
                {selectedNode.label.charAt(0).toUpperCase()}
              </div>
              <div style={{ flex: 1, minWidth: 0 }}>
                <div className="truncate" style={{ fontWeight: 700, fontSize: 16, marginBottom: 6 }}>
                  {selectedNode.label}
                </div>
                <div style={{ display: 'flex', gap: 6, flexWrap: 'wrap' }}>
                  {selectedNode.type === 'self' && (
                    <span className="badge badge-gray">Вы</span>
                  )}
                </div>
              </div>
            </div>

            <div className="divider" />

            {/* Stats */}
            <div style={{ display: 'flex', flexDirection: 'column', gap: 12, marginTop: 12 }}>
              <InfoRow label="Сообщений" value={selectedNode.message_count} />
              {selectedNode.trust_score !== null && (
                <InfoRow label="Доверие" value={`${selectedNode.trust_score} / 100`} />
              )}
            </div>

            {/* Strength bar */}
            {selectedNode.type !== 'self' && (
              <div style={{ marginTop: 16 }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 4 }}>
                  <span style={{ fontSize: 12, color: 'var(--text2)' }}>Сила связи</span>
                  <span style={{ fontSize: 12, fontWeight: 600 }}>
                    {Math.round(selectedNode.strength * 100)}%
                  </span>
                </div>
                <div style={{ height: 4, background: 'var(--bg-card2)', borderRadius: 2 }}>
                  <div
                    style={{
                      height: '100%',
                      borderRadius: 2,
                      width: `${selectedNode.strength * 100}%`,
                      background: selectedNode.strength > 0.6
                        ? 'linear-gradient(90deg, #7c3aed, #a78bfa)'
                        : 'var(--purple-d)',
                      boxShadow: selectedNode.strength > 0.6 ? '0 0 8px var(--purple-glow)' : 'none',
                    }}
                  />
                </div>
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  )
}

// ── Helpers ───────────────────────────────────────────────────────────────────

function InfoRow({ label, value }: { label: string; value: string | number }) {
  return (
    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
      <span style={{ color: 'var(--text2)', fontSize: 14 }}>{label}</span>
      <span style={{ fontWeight: 600, fontSize: 14 }}>{value}</span>
    </div>
  )
}
