import { useEffect, useRef, useState, useCallback, useMemo } from 'react'
import { useNavigate } from 'react-router-dom'
import ForceGraph2D from 'react-force-graph-2d'
import type { NetworkGraph as NetworkGraphType, NetworkNode, NetworkStatus } from '../types'
import {
  getNetworkGraph,
  getNetworkStatus,
  joinNetwork,
  updateNetworkSettings,
} from '../api'
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
}

// ── Canvas helpers ────────────────────────────────────────────────────────────

function nodeColor(n: FGNode): string {
  if (n.type === 'self') return '#7C5CBF'
  if (n.type === 'first') return n.has_subscription ? '#2E8B57' : '#888888'
  return '#cccccc'
}

function nodeRadius(n: FGNode): number {
  if (n.type === 'self') return 16
  if (n.type === 'first') return n.has_subscription ? 10 : 8
  return 6
}

function linkColor(l: FGLink): string {
  const ts = l.trust_score
  if (ts === null || ts === undefined) return 'rgba(150,150,150,0.4)'
  if (ts >= 70) return 'rgba(56,161,105,0.6)'
  if (ts < 40) return 'rgba(229,62,62,0.5)'
  return 'rgba(150,150,150,0.4)'
}

// ── Component ─────────────────────────────────────────────────────────────────

export function NetworkGraph() {
  const { showToast } = useApp()
  const navigate = useNavigate()

  const [status, setStatus] = useState<NetworkStatus | null>(null)
  const [statusLoading, setStatusLoading] = useState(true)

  const [graphData, setGraphData] = useState<NetworkGraphType | null>(null)
  const [graphLoading, setGraphLoading] = useState(false)

  const [visible, setVisible] = useState(true)
  const [joining, setJoining] = useState(false)

  const [depth, setDepth] = useState<1 | 2>(1)
  const [selectedNode, setSelectedNode] = useState<FGNode | null>(null)
  const [showSettings, setShowSettings] = useState(false)

  const graphContainerRef = useRef<HTMLDivElement>(null)
  const [graphDims, setGraphDims] = useState({ width: 300, height: 500 })

  // Load network status
  useEffect(() => {
    getNetworkStatus()
      .then((s) => {
        setStatus(s)
        setVisible(s.visible)
      })
      .catch(() => showToast('Ошибка загрузки', 'error'))
      .finally(() => setStatusLoading(false))
  }, [showToast])

  // Load graph when in network or depth changes
  const loadGraph = useCallback(
    async (d: 1 | 2) => {
      setGraphLoading(true)
      try {
        const data = await getNetworkGraph(d)
        setGraphData(data)
      } catch {
        showToast('Ошибка загрузки графа', 'error')
      } finally {
        setGraphLoading(false)
      }
    },
    [showToast],
  )

  useEffect(() => {
    if (status?.in_network) {
      loadGraph(depth)
    }
  }, [status?.in_network, depth, loadGraph])

  // Measure the graph container for ForceGraph2D dimensions
  useEffect(() => {
    if (!status?.in_network) return
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
  }, [status?.in_network])

  // ── Actions ─────────────────────────────────────────────────────────────────

  const handleJoin = async () => {
    setJoining(true)
    try {
      const s = await joinNetwork(visible)
      setStatus(s)
    } catch (e) {
      showToast((e as Error).message || 'Ошибка', 'error')
    } finally {
      setJoining(false)
    }
  }

  const handleUpdateSettings = useCallback(
    async (newVisible: boolean) => {
      try {
        await updateNetworkSettings(newVisible)
        setStatus((s) => (s ? { ...s, visible: newVisible } : s))
        showToast('Настройки сохранены', 'success')
      } catch {
        setVisible((v) => !v) // revert optimistic update
        showToast('Ошибка сохранения', 'error')
      }
    },
    [showToast],
  )

  const shareBot = () => {
    const url = 'https://t.me/zynto_bot'
    const text = 'Присоединяйся к Zynto — умный мониторинг удалённых сообщений!'
    const shareUrl = `https://t.me/share/url?url=${encodeURIComponent(url)}&text=${encodeURIComponent(text)}`
    const tg = (window as { Telegram?: { WebApp?: { openTelegramLink?: (u: string) => void } } })
      .Telegram?.WebApp
    if (tg?.openTelegramLink) {
      tg.openTelegramLink(shareUrl)
    } else {
      window.open(shareUrl, '_blank')
    }
  }

  // ── ForceGraph2D callbacks ───────────────────────────────────────────────────

  const fgData = useMemo(
    () => ({
      nodes: (graphData?.nodes ?? []) as FGNode[],
      links: (graphData?.edges ?? []).map((e) => ({
        source: e.source,
        target: e.target,
        weight: e.weight,
        trust_score: e.trust_score,
      })) as FGLink[],
    }),
    [graphData],
  )

  const maxWeight = useMemo(() => {
    const weights = graphData?.edges.map((e) => e.weight) ?? []
    return Math.max(1, ...weights)
  }, [graphData])

  const nodeCanvasObject = useCallback(
    (node: object, ctx: CanvasRenderingContext2D) => {
      const n = node as FGNode
      const x = n.x ?? 0
      const y = n.y ?? 0
      const r = nodeRadius(n)
      const fill = nodeColor(n)

      ctx.beginPath()
      ctx.arc(x, y, r, 0, 2 * Math.PI)
      ctx.fillStyle = fill
      ctx.fill()

      if (n.type === 'self' || n.type === 'first') {
        const fontSize = Math.max(7, Math.floor(r * 0.75))
        ctx.font = `bold ${fontSize}px sans-serif`
        ctx.textAlign = 'center'
        ctx.textBaseline = 'middle'
        ctx.fillStyle = n.type === 'self' ? '#ffffff' : 'rgba(255,255,255,0.8)'
        ctx.fillText(n.label.charAt(0).toUpperCase(), x, y)
      }
    },
    [],
  )

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

  const getLinkWidth = useCallback(
    (link: object) => {
      const l = link as FGLink
      return 1 + (l.weight / maxWeight) * 3
    },
    [maxWeight],
  )

  const handleNodeClick = useCallback((node: object) => {
    setSelectedNode(node as FGNode)
  }, [])

  // ── Render: loading ──────────────────────────────────────────────────────────

  if (statusLoading) {
    return (
      <div className="loading-center" style={{ flex: 1 }}>
        <div className="spinner" />
      </div>
    )
  }

  // ── Render: consent screen ───────────────────────────────────────────────────

  if (!status?.in_network) {
    return (
      <div className="page">
        <div
          style={{
            display: 'flex',
            flexDirection: 'column',
            alignItems: 'center',
            textAlign: 'center',
            paddingTop: 16,
          }}
        >
          <svg
            width="72"
            height="72"
            viewBox="0 0 24 24"
            fill="none"
            strokeWidth="1.5"
            style={{ marginBottom: 20 }}
          >
            <circle cx="5" cy="12" r="2" fill="#4c1d95" stroke="#a78bfa" />
            <circle cx="19" cy="5" r="2" fill="#4c1d95" stroke="#a78bfa" />
            <circle cx="19" cy="19" r="2" fill="#4c1d95" stroke="#a78bfa" />
            <line x1="7" y1="12" x2="17" y2="6" stroke="#a78bfa" />
            <line x1="7" y1="12" x2="17" y2="18" stroke="#a78bfa" />
          </svg>

          <h1 style={{ fontSize: 22, fontWeight: 800, marginBottom: 12 }}>Сеть связей</h1>
          <p
            style={{
              color: 'var(--text2)',
              fontSize: 14,
              lineHeight: 1.6,
              maxWidth: 280,
              marginBottom: 24,
            }}
          >
            Видите, кто из ваших контактов тоже использует Zynto — и насколько крепка ваша связь.
          </p>

          <div className="card" style={{ width: '100%', textAlign: 'left', marginBottom: 12 }}>
            <div
              className="text-xs text3"
              style={{ marginBottom: 10, textTransform: 'uppercase', letterSpacing: '0.5px' }}
            >
              Что увидят другие:
            </div>
            <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
              <div style={{ display: 'flex', gap: 8, fontSize: 14, color: 'var(--text2)' }}>
                <span>•</span>
                <span>Ваше имя и уровень связи с вами</span>
              </div>
              <div style={{ display: 'flex', gap: 8, fontSize: 14, color: 'var(--text2)' }}>
                <span>•</span>
                <span>Ваш статус в Zynto (подписчик / нет)</span>
              </div>
            </div>
          </div>

          <div
            className="card"
            style={{ width: '100%', marginBottom: 24, cursor: 'pointer' }}
            onClick={() => setVisible((v) => !v)}
          >
            <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
              <div
                style={{
                  width: 20,
                  height: 20,
                  border: `2px solid ${visible ? 'var(--purple-l)' : 'var(--text3)'}`,
                  borderRadius: 4,
                  background: visible ? 'var(--purple)' : 'transparent',
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  flexShrink: 0,
                  transition: 'all 0.15s',
                }}
              >
                {visible && (
                  <svg width="12" height="12" viewBox="0 0 12 12" fill="none">
                    <polyline
                      points="2,6 5,9 10,3"
                      stroke="#fff"
                      strokeWidth="2"
                      strokeLinecap="round"
                      strokeLinejoin="round"
                    />
                  </svg>
                )}
              </div>
              <div>
                <div style={{ fontSize: 14, fontWeight: 600 }}>
                  Показывать меня в сети других участников
                </div>
                <div className="text-xs text3" style={{ marginTop: 2 }}>
                  Можно изменить в настройках в любой момент
                </div>
              </div>
            </div>
          </div>

          <button
            className="btn btn-primary"
            style={{ width: '100%', marginBottom: 12 }}
            onClick={handleJoin}
            disabled={joining}
          >
            {joining ? 'Подключение...' : 'Войти в сеть'}
          </button>
          <button
            style={{
              background: 'none',
              border: 'none',
              color: 'var(--text3)',
              fontSize: 14,
              cursor: 'pointer',
              padding: '8px 0',
              WebkitTapHighlightColor: 'transparent',
            }}
            onClick={() => navigate('/')}
          >
            Не сейчас
          </button>
        </div>
      </div>
    )
  }

  // ── Render: graph screen ─────────────────────────────────────────────────────

  const hasNodes = (graphData?.nodes.length ?? 0) > 0

  return (
    <div
      style={{
        flex: 1,
        display: 'flex',
        flexDirection: 'column',
        overflow: 'hidden',
        paddingBottom: 'var(--nav-total)',
      }}
    >
      {/* Top bar */}
      <div
        style={{
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          padding: '10px 16px',
          background: 'rgba(13, 13, 20, 0.95)',
          backdropFilter: 'blur(8px)',
          WebkitBackdropFilter: 'blur(8px)',
          borderBottom: '1px solid var(--purple-border)',
          flexShrink: 0,
          zIndex: 10,
        }}
      >
        <div style={{ display: 'flex', alignItems: 'baseline', gap: 8 }}>
          <span style={{ fontWeight: 700, fontSize: 15 }}>Сеть</span>
          {graphData && (
            <span style={{ fontSize: 13, color: 'var(--text2)' }}>
              {graphData.total_in_network} участников
            </span>
          )}
        </div>

        <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
          {graphData?.is_premium && (
            <div style={{ display: 'flex', gap: 4 }}>
              {([1, 2] as const).map((d) => (
                <button
                  key={d}
                  onClick={() => setDepth(d)}
                  style={{
                    padding: '4px 10px',
                    borderRadius: 12,
                    fontSize: 12,
                    fontWeight: 600,
                    border: 'none',
                    cursor: 'pointer',
                    background: depth === d ? 'var(--purple)' : 'var(--bg-card2)',
                    color: depth === d ? '#fff' : 'var(--text2)',
                    transition: 'all 0.15s',
                    WebkitTapHighlightColor: 'transparent',
                  }}
                >
                  {d} ур.
                </button>
              ))}
            </div>
          )}
          <button
            onClick={() => setShowSettings(true)}
            style={{
              background: 'none',
              border: 'none',
              color: 'var(--text2)',
              cursor: 'pointer',
              fontSize: 18,
              padding: '4px 6px',
              lineHeight: 1,
              WebkitTapHighlightColor: 'transparent',
            }}
            aria-label="Настройки"
          >
            ⚙️
          </button>
        </div>
      </div>

      {/* Graph area */}
      <div
        ref={graphContainerRef}
        style={{ flex: 1, position: 'relative', overflow: 'hidden', background: '#0d0d14' }}
      >
        {graphLoading ? (
          <div className="loading-center" style={{ height: '100%' }}>
            <div className="spinner" />
          </div>
        ) : !hasNodes ? (
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
            <div style={{ fontSize: 48, marginBottom: 16 }}>🌐</div>
            <div style={{ fontWeight: 700, fontSize: 16, marginBottom: 8 }}>Пока пусто</div>
            <div
              style={{
                color: 'var(--text2)',
                fontSize: 14,
                marginBottom: 24,
                lineHeight: 1.5,
              }}
            >
              Пока никто из ваших контактов не в сети. Поделитесь ссылкой на бота!
            </div>
            <button
              className="btn btn-primary"
              style={{ width: 'auto', padding: '12px 24px' }}
              onClick={shareBot}
            >
              📤 Поделиться ботом
            </button>
          </div>
        ) : (
          <>
            {graphDims.width > 0 && graphDims.height > 0 && (
              <ForceGraph2D
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
                cooldownTicks={120}
              />
            )}

            {!graphData?.is_premium && (
              <div
                style={{
                  position: 'absolute',
                  bottom: 16,
                  left: '50%',
                  transform: 'translateX(-50%)',
                  background: 'rgba(13, 13, 20, 0.85)',
                  backdropFilter: 'blur(6px)',
                  WebkitBackdropFilter: 'blur(6px)',
                  border: '1px solid var(--purple-border)',
                  borderRadius: 20,
                  padding: '6px 14px',
                  fontSize: 12,
                  color: 'var(--text2)',
                  whiteSpace: 'nowrap',
                  pointerEvents: 'none',
                }}
              >
                ✨ Получите Premium для 2-го уровня
              </div>
            )}
          </>
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
            <div
              style={{
                width: 36,
                height: 4,
                background: 'var(--text3)',
                borderRadius: 2,
                margin: '0 auto 20px',
              }}
            />
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
                }}
              >
                {selectedNode.label.charAt(0).toUpperCase()}
              </div>
              <div style={{ flex: 1, minWidth: 0 }}>
                <div
                  className="truncate"
                  style={{ fontWeight: 700, fontSize: 16, marginBottom: 6 }}
                >
                  {selectedNode.label}
                </div>
                <div style={{ display: 'flex', gap: 6, flexWrap: 'wrap' }}>
                  {selectedNode.has_subscription && (
                    <span className="badge badge-purple">Premium</span>
                  )}
                  {selectedNode.type === 'self' && (
                    <span className="badge badge-gray">Вы</span>
                  )}
                  {selectedNode.type === 'first' && (
                    <span className="badge badge-gray">1-й уровень</span>
                  )}
                  {selectedNode.type === 'second' && (
                    <span className="badge badge-gray">2-й уровень</span>
                  )}
                </div>
              </div>
            </div>

            <div className="divider" />

            <div style={{ display: 'flex', flexDirection: 'column', gap: 12, marginTop: 12 }}>
              <InfoRow label="Сообщений" value={selectedNode.message_count} />
              {selectedNode.trust_score !== null && (
                <InfoRow label="Доверие" value={`${selectedNode.trust_score} / 100`} />
              )}
            </div>
          </div>
        </div>
      )}

      {/* Settings drawer */}
      {showSettings && (
        <div
          style={{
            position: 'fixed',
            inset: 0,
            background: 'rgba(0,0,0,0.55)',
            zIndex: 200,
            display: 'flex',
            alignItems: 'flex-end',
          }}
          onClick={() => setShowSettings(false)}
        >
          <div
            style={{
              background: 'var(--bg-card)',
              borderRadius: '20px 20px 0 0',
              border: '1px solid var(--purple-border)',
              padding: '16px 20px',
              paddingBottom: 'calc(var(--nav-total) + 20px)',
              width: '100%',
            }}
            onClick={(e) => e.stopPropagation()}
          >
            <div
              style={{
                width: 36,
                height: 4,
                background: 'var(--text3)',
                borderRadius: 2,
                margin: '0 auto 20px',
              }}
            />
            <div style={{ fontWeight: 700, fontSize: 17, marginBottom: 20 }}>
              Настройки сети
            </div>
            <div
              style={{ display: 'flex', alignItems: 'center', gap: 14, cursor: 'pointer', marginBottom: 24 }}
              onClick={() => {
                const next = !visible
                setVisible(next)
                handleUpdateSettings(next)
              }}
            >
              <div
                style={{
                  width: 44,
                  height: 24,
                  borderRadius: 12,
                  background: visible ? 'var(--purple)' : 'var(--bg-card2)',
                  border: `1px solid ${visible ? 'var(--purple)' : 'var(--text3)'}`,
                  position: 'relative',
                  transition: 'all 0.2s',
                  flexShrink: 0,
                }}
              >
                <div
                  style={{
                    position: 'absolute',
                    top: 2,
                    left: visible ? 20 : 2,
                    width: 18,
                    height: 18,
                    borderRadius: 9,
                    background: '#fff',
                    transition: 'left 0.2s',
                    boxShadow: '0 1px 4px rgba(0,0,0,0.3)',
                  }}
                />
              </div>
              <div>
                <div style={{ fontSize: 14, fontWeight: 600 }}>Показывать меня в сети</div>
                <div className="text-xs text3" style={{ marginTop: 2 }}>
                  Другие участники смогут видеть вас в своих сетях
                </div>
              </div>
            </div>
            <button className="btn btn-secondary" onClick={() => setShowSettings(false)}>
              Закрыть
            </button>
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
