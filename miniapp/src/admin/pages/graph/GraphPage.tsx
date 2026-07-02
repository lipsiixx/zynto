import { useCallback, useEffect, useMemo, useRef, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import ForceGraph2D from 'react-force-graph-2d'
import { getGraph, type Graph as GraphData, type GraphNode } from '@/admin/entities/graph'

// ── Internal graph types (extend GraphNode with simulation coords) ─────────

interface FGNode extends GraphNode {
  x?: number
  y?: number
  vx?: number
  vy?: number
  fx?: number
  fy?: number
  degree?: number
}

interface FGLink {
  source: string | FGNode
  target: string | FGNode
  weight: number
}

// ── Settings (порт DEFAULT_SETTINGS из старого admin-panel Graph.jsx,
// шкала слайдеров 0–100 — как в pages/network/ui/NetworkPage.tsx) ──────────

const SETTINGS_KEY = 'admin_graph_settings'

interface GraphSettings {
  repulsion: number // 0–100
  nodeSize: number // 0–100
  edgeWidth: number // 0–100
  nodeColor: string
  showLabels: boolean
}

const DEFAULT_SETTINGS: GraphSettings = {
  repulsion: 50,
  nodeSize: 50,
  edgeWidth: 50,
  nodeColor: '#8b5cf6',
  showLabels: true,
}

const COLOR_PRESETS = ['#8b5cf6', '#3b82f6', '#06b6d4', '#22c55e', '#ec4899', '#f97316']

function loadSettings(): GraphSettings {
  try {
    const raw = localStorage.getItem(SETTINGS_KEY)
    if (!raw) return DEFAULT_SETTINGS
    return { ...DEFAULT_SETTINGS, ...JSON.parse(raw) }
  } catch {
    return DEFAULT_SETTINGS
  }
}

function persistSettings(s: GraphSettings): void {
  try {
    localStorage.setItem(SETTINGS_KEY, JSON.stringify(s))
  } catch {
    // ignore — localStorage может быть недоступен
  }
}

// 0 → charge -700 (разрежённо), 50 → -400 (по умолчанию), 100 → -100 (плотно)
function sliderToCharge(v: number): number {
  return -700 + (v / 100) * 600
}

// 0 → distance 180, 50 → 120 (по умолчанию), 100 → 60
function sliderToLinkDist(v: number): number {
  return 180 - (v / 100) * 120
}

// 0 → ×0.33, 50 → ×1.0 (по умолчанию), 100 → ×1.67
function sliderToMult(v: number): number {
  return (v + 25) / 75
}

// ── Color helpers (порт hexToRgba/lighten/darken из Graph.jsx) ─────────────

function hexToRgba(hex: string, alpha: number): string {
  const r = parseInt(hex.slice(1, 3), 16)
  const g = parseInt(hex.slice(3, 5), 16)
  const b = parseInt(hex.slice(5, 7), 16)
  return `rgba(${r},${g},${b},${alpha})`
}

function lighten(hex: string, amt: number): string {
  const r = parseInt(hex.slice(1, 3), 16)
  const g = parseInt(hex.slice(3, 5), 16)
  const b = parseInt(hex.slice(5, 7), 16)
  const f = (v: number) => Math.min(255, Math.round(v + (255 - v) * amt)).toString(16).padStart(2, '0')
  return `#${f(r)}${f(g)}${f(b)}`
}

// ── Component ────────────────────────────────────────────────────────────

export function GraphPage() {
  const navigate = useNavigate()

  const [minWeight, setMinWeight] = useState(1)
  const [graphData, setGraphData] = useState<GraphData | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [settingsOpen, setSettingsOpen] = useState(false)
  const [settings, setSettings] = useState<GraphSettings>(loadSettings)
  const [picker, setPicker] = useState<{ contact: FGNode; subs: FGNode[] } | null>(null)

  const containerRef = useRef<HTMLDivElement>(null)
  const [dims, setDims] = useState({ width: 0, height: 0 })
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  const fgRef = useRef<any>(null)

  const load = useCallback(() => {
    setLoading(true)
    setError('')
    getGraph(minWeight)
      .then(setGraphData)
      .catch((e) => setError(e instanceof Error ? e.message : 'Ошибка загрузки графа'))
      .finally(() => setLoading(false))
  }, [minWeight])

  useEffect(() => {
    load()
  }, [load])

  const updateSetting = useCallback(<K extends keyof GraphSettings>(key: K, value: GraphSettings[K]) => {
    setSettings((prev) => {
      const next = { ...prev, [key]: value }
      persistSettings(next)
      return next
    })
  }, [])

  // Измеряем контейнер под ForceGraph2D
  useEffect(() => {
    const el = containerRef.current
    if (!el) return
    const immediate = el.getBoundingClientRect()
    if (immediate.width > 0 && immediate.height > 0) {
      setDims({ width: Math.floor(immediate.width), height: Math.floor(immediate.height) })
    }
    const obs = new ResizeObserver((entries) => {
      const rect = entries[0]?.contentRect
      if (rect && rect.width > 0 && rect.height > 0) {
        setDims({ width: Math.floor(rect.width), height: Math.floor(rect.height) })
      }
    })
    obs.observe(el)
    return () => obs.disconnect()
  }, [loading])

  // Применяем физику при смене repulsion
  useEffect(() => {
    if (!fgRef.current || !graphData) return
    fgRef.current.d3Force('charge')?.strength(sliderToCharge(settings.repulsion))
    fgRef.current.d3Force('link')?.distance(sliderToLinkDist(settings.repulsion))
    fgRef.current.d3ReheatSimulation()
  }, [graphData, settings.repulsion])

  const nodes = graphData?.nodes ?? []
  const edges = graphData?.edges ?? []
  const subCount = nodes.filter((n) => n.type === 'subscriber').length
  const cntCount = nodes.filter((n) => n.type === 'contact').length
  const maxWeight = edges.reduce((m, e) => Math.max(m, e.weight), 1)

  // degree (кол-во связей) на узел — влияет на размер
  const degreeMap = useMemo(() => {
    const map = new Map<string, number>()
    for (const e of edges) {
      map.set(e.source, (map.get(e.source) || 0) + 1)
      map.set(e.target, (map.get(e.target) || 0) + 1)
    }
    return map
  }, [edges])

  // contact.id → подписчики, с которыми у него есть переписка (для клика по контакту)
  const contactToSubs = useMemo(() => {
    const nodeMap = new Map(nodes.map((n) => [n.id, n as FGNode]))
    const map = new Map<string, FGNode[]>()
    for (const e of edges) {
      if (e.target.startsWith('c:')) {
        const sub = nodeMap.get(e.source)
        if (sub) {
          if (!map.has(e.target)) map.set(e.target, [])
          map.get(e.target)!.push(sub)
        }
      }
    }
    return map
  }, [nodes, edges])

  const fgData = useMemo(
    () => ({
      nodes: nodes as FGNode[],
      links: edges.map((e) => ({ source: e.source, target: e.target, weight: e.weight })) as FGLink[],
    }),
    [nodes, edges],
  )

  const nodeCanvasObject = useCallback(
    (node: object, ctx: CanvasRenderingContext2D) => {
      const n = node as FGNode
      const x = n.x ?? 0
      const y = n.y ?? 0
      const isSub = n.type === 'subscriber'
      const deg = degreeMap.get(n.id) || 1
      const base = isSub ? 9 : 5
      const r = (base + Math.sqrt(deg) * 2.5) * sliderToMult(settings.nodeSize)
      const color = settings.nodeColor

      const grd = ctx.createRadialGradient(x, y, 0, x, y, r)
      if (isSub) {
        grd.addColorStop(0, lighten(color, 0.35))
        grd.addColorStop(1, color)
      } else {
        grd.addColorStop(0, '#4b3c7a')
        grd.addColorStop(1, '#1e1540')
      }

      ctx.shadowColor = isSub ? color : '#4c3394'
      ctx.shadowBlur = isSub ? 14 : 6
      ctx.beginPath()
      ctx.arc(x, y, r, 0, 2 * Math.PI)
      ctx.fillStyle = grd
      ctx.fill()
      ctx.shadowBlur = 0

      ctx.lineWidth = 1
      ctx.strokeStyle = isSub ? hexToRgba(lighten(color, 0.4), 0.7) : 'rgba(139,92,246,0.25)'
      ctx.stroke()

      if (settings.showLabels && isSub) {
        const fontSize = Math.max(9, Math.min(12, r * 0.6))
        ctx.font = `500 ${fontSize}px sans-serif`
        ctx.textAlign = 'center'
        ctx.textBaseline = 'top'
        ctx.fillStyle = hexToRgba(lighten(color, 0.6), 0.85)
        ctx.fillText(n.label.slice(0, 22), x, y + r + 3)
      }
    },
    [settings.nodeSize, settings.nodeColor, settings.showLabels, degreeMap],
  )

  const nodePointerAreaPaint = useCallback(
    (node: object, color: string, ctx: CanvasRenderingContext2D) => {
      const n = node as FGNode
      const isSub = n.type === 'subscriber'
      const deg = degreeMap.get(n.id) || 1
      const base = isSub ? 9 : 5
      const r = (base + Math.sqrt(deg) * 2.5) * sliderToMult(settings.nodeSize) + 4
      ctx.fillStyle = color
      ctx.beginPath()
      ctx.arc(n.x ?? 0, n.y ?? 0, r, 0, 2 * Math.PI)
      ctx.fill()
    },
    [settings.nodeSize, degreeMap],
  )

  const getLinkColor = useCallback(
    (link: object) => {
      const l = link as FGLink
      const norm = Math.sqrt(l.weight / maxWeight)
      return hexToRgba(settings.nodeColor, 0.08 + norm * 0.55)
    },
    [settings.nodeColor, maxWeight],
  )

  const getLinkWidth = useCallback(
    (link: object) => {
      const l = link as FGLink
      const norm = Math.sqrt(l.weight / maxWeight)
      return (0.5 + norm * 4.5) * sliderToMult(settings.edgeWidth)
    },
    [settings.edgeWidth, maxWeight],
  )

  const handleNodeClick = useCallback(
    (node: object) => {
      const n = node as FGNode
      setSettingsOpen(false)

      if (n.type === 'subscriber') {
        if (n.dbId == null) {
          // backend GraphNode пока не отдаёт dbId — см. предупреждение в
          // entities/graph/model/types.ts. Переход невозможен, тихо игнорируем.
          return
        }
        navigate(`/a/users/${n.dbId}`)
        return
      }

      // contact node
      const subs = contactToSubs.get(n.id) || []
      if (subs.length === 0) return
      if (subs.length === 1) {
        const sub = subs[0]
        if (sub.dbId == null) return
        navigate(`/a/chat/${sub.dbId}/${n.id.slice(2)}`)
      } else {
        setPicker({ contact: n, subs })
      }
    },
    [navigate, contactToSubs],
  )

  const handleEngineStop = useCallback(() => {
    fgRef.current?.zoomToFit(400, 48)
  }, [])

  return (
    <div className="admin-page" style={{ padding: 0, display: 'flex', flexDirection: 'column', height: '100%' }}>
      {/* Toolbar */}
      <div className="admin-graph-toolbar">
        <span style={{ fontWeight: 700, fontSize: 15 }}>Граф связей</span>

        <span className="text-sm text2">Порог сообщений:</span>
        <input
          type="number"
          min={1}
          max={100}
          value={minWeight}
          onChange={(e) => setMinWeight(Math.max(1, Number(e.target.value)))}
        />

        <button className="admin-icon-btn" onClick={load} disabled={loading}>
          {loading ? '...' : '↻'}
        </button>

        <button
          className="admin-icon-btn"
          style={settingsOpen ? { background: 'rgba(124,58,237,0.2)', color: 'var(--purple-l)' } : undefined}
          onClick={() => setSettingsOpen((v) => !v)}
        >
          ⚙ настройки
        </button>

        {graphData && (
          <div style={{ marginLeft: 'auto', display: 'flex', gap: 8, alignItems: 'center' }}>
            <span className="badge badge-purple">Подписчиков: {subCount}</span>
            <span className="badge badge-gray">Контактов: {cntCount}</span>
            <span className="text3 text-sm">Связей: {edges.length}</span>
          </div>
        )}
      </div>

      {/* Canvas */}
      <div ref={containerRef} className="admin-graph-canvas-wrap">
        {loading && (
          <div className="loading-center" style={{ position: 'absolute', inset: 0 }}>
            <div className="spinner" />
          </div>
        )}

        {!loading && error && (
          <div className="empty-state">
            <div style={{ color: 'var(--red)', marginBottom: 12 }}>{error}</div>
            <button className="admin-icon-btn" onClick={load}>
              Повторить
            </button>
          </div>
        )}

        {!loading && !error && nodes.length === 0 && (
          <div className="empty-state">
            <div style={{ fontSize: 40, marginBottom: 12 }}>🕸</div>
            <div style={{ fontWeight: 700, marginBottom: 4 }}>Граф пуст</div>
            <div className="text2 text-sm">Уменьшите порог или дождитесь входящих сообщений</div>
          </div>
        )}

        {!loading && !error && nodes.length > 0 && dims.width > 0 && dims.height > 0 && (
          <ForceGraph2D
            ref={fgRef}
            graphData={fgData}
            width={dims.width}
            height={dims.height}
            backgroundColor="#0d0d14"
            nodeCanvasObject={nodeCanvasObject}
            nodePointerAreaPaint={nodePointerAreaPaint}
            nodeLabel={(node: object) => (node as FGNode).label}
            linkColor={getLinkColor}
            linkWidth={getLinkWidth}
            onNodeClick={handleNodeClick}
            onEngineStop={handleEngineStop}
            cooldownTicks={100}
            d3AlphaDecay={0.02}
            d3VelocityDecay={0.3}
          />
        )}

        {/* Settings panel */}
        {settingsOpen && (
          <div className="admin-graph-settings-panel">
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 14 }}>
              <span style={{ fontWeight: 600, fontSize: 13 }}>Настройки графа</span>
              <button
                className="admin-icon-btn"
                style={{ padding: '2px 8px' }}
                onClick={() => setSettingsOpen(false)}
              >
                ×
              </button>
            </div>

            <SliderRow label="Плотность связей" value={settings.repulsion} onChange={(v) => updateSetting('repulsion', v)} />
            <SliderRow label="Размер узлов" value={settings.nodeSize} onChange={(v) => updateSetting('nodeSize', v)} />
            <SliderRow label="Толщина рёбер" value={settings.edgeWidth} onChange={(v) => updateSetting('edgeWidth', v)} />

            <div className="divider" />

            <div style={{ marginBottom: 14 }}>
              <div className="text-sm text2" style={{ marginBottom: 8 }}>
                Цвет подписчиков
              </div>
              <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                <label style={{ position: 'relative', cursor: 'pointer', flexShrink: 0 }}>
                  <div
                    style={{
                      width: 26,
                      height: 26,
                      background: settings.nodeColor,
                      borderRadius: 6,
                      border: '2px solid rgba(255,255,255,0.15)',
                      boxShadow: `0 0 8px ${hexToRgba(settings.nodeColor, 0.5)}`,
                    }}
                  />
                  <input
                    type="color"
                    value={settings.nodeColor}
                    onChange={(e) => updateSetting('nodeColor', e.target.value)}
                    style={{ position: 'absolute', inset: 0, opacity: 0, width: '100%', height: '100%', cursor: 'pointer' }}
                  />
                </label>
                <div style={{ display: 'flex', gap: 5, marginLeft: 'auto' }}>
                  {COLOR_PRESETS.map((c) => (
                    <button
                      key={c}
                      onClick={() => updateSetting('nodeColor', c)}
                      title={c}
                      style={{
                        width: 16,
                        height: 16,
                        borderRadius: '50%',
                        background: c,
                        border: 'none',
                        padding: 0,
                        cursor: 'pointer',
                        outline: settings.nodeColor === c ? '2px solid rgba(255,255,255,0.8)' : 'none',
                        outlineOffset: 1,
                      }}
                    />
                  ))}
                </div>
              </div>
            </div>

            <label style={{ display: 'flex', alignItems: 'center', gap: 8, cursor: 'pointer', marginBottom: 14 }}>
              <input
                type="checkbox"
                checked={settings.showLabels}
                onChange={(e) => updateSetting('showLabels', e.target.checked)}
                style={{ accentColor: 'var(--purple)', width: 14, height: 14, cursor: 'pointer' }}
              />
              <span className="text-sm text2">Показывать подписи</span>
            </label>

            <button
              className="btn btn-secondary"
              style={{ padding: '8px 0' }}
              onClick={() => {
                setSettings(DEFAULT_SETTINGS)
                persistSettings(DEFAULT_SETTINGS)
              }}
            >
              Сбросить
            </button>
          </div>
        )}
      </div>

      {/* Legend */}
      <div className="admin-graph-legend">
        <LegendDot color={settings.nodeColor} glow label="Подписчик → чаты" />
        <LegendDot color="#3d2d6e" label="Контакт → чат" />
        <span>Тащи · Колесо — масштаб</span>
      </div>

      {/* Picker modal */}
      {picker && (
        <div
          style={{
            position: 'fixed',
            inset: 0,
            zIndex: 300,
            background: 'rgba(0,0,0,0.55)',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            padding: 24,
          }}
          onClick={() => setPicker(null)}
        >
          <div className="card" style={{ width: '100%', maxWidth: 360 }} onClick={(e) => e.stopPropagation()}>
            <div style={{ fontWeight: 700, marginBottom: 4 }}>Выберите подписчика</div>
            <div className="text-sm text2" style={{ marginBottom: 16 }}>
              Контакт <strong style={{ color: 'var(--purple-l)' }}>{picker.contact.label}</strong> переписывался с
              несколькими подписчиками бота.
            </div>
            <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
              {picker.subs.map((sub) => (
                <button
                  key={sub.id}
                  className="btn btn-secondary"
                  style={{ justifyContent: 'flex-start', padding: '10px 14px' }}
                  onClick={() => {
                    setPicker(null)
                    if (sub.dbId != null) navigate(`/a/chat/${sub.dbId}/${picker.contact.id.slice(2)}`)
                  }}
                >
                  {sub.label}
                </button>
              ))}
            </div>
          </div>
        </div>
      )}
    </div>
  )
}

function SliderRow({ label, value, onChange }: { label: string; value: number; onChange: (v: number) => void }) {
  return (
    <div style={{ marginBottom: 14 }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 6 }}>
        <span className="text-sm text2">{label}</span>
        <span className="text-sm" style={{ color: 'var(--purple-l)', fontWeight: 600 }}>
          {value}
        </span>
      </div>
      <div className="slider-wrap">
        <input
          type="range"
          min={0}
          max={100}
          step={1}
          value={value}
          onChange={(e) => onChange(Number(e.target.value))}
          style={{
            background: `linear-gradient(to right, var(--purple-l) 0%, var(--purple-l) ${value}%, var(--bg-card2) ${value}%, var(--bg-card2) 100%)`,
          }}
        />
      </div>
    </div>
  )
}

function LegendDot({ color, glow, label }: { color: string; glow?: boolean; label: string }) {
  return (
    <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
      <div
        style={{
          width: 10,
          height: 10,
          borderRadius: '50%',
          background: color,
          boxShadow: glow ? `0 0 6px ${color}` : 'none',
        }}
      />
      <span>{label}</span>
    </div>
  )
}
