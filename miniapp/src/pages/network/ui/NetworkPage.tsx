import { useEffect, useRef, useState, useCallback, useMemo } from "react";
import ForceGraph2D from "react-force-graph-2d";
import type { NetworkGraph as NetworkGraphType, NetworkNode } from "@/entities/network";
import { getNetworkGraph } from "@/entities/network";
import { useApp } from "@/app/AppContext";

// ── Internal graph types (extend NetworkNode with simulation coords) ──────────

interface FGNode extends NetworkNode {
  x?: number;
  y?: number;
  vx?: number;
  vy?: number;
  fx?: number;
  fy?: number;
}

interface FGLink {
  source: string | FGNode;
  target: string | FGNode;
  weight: number;
  trust_score: number | null;
  strength: number;
}

// ── Graph Settings ────────────────────────────────────────────────────────────

const SETTINGS_KEY = "miniapp_graph_settings";

interface GraphSettings {
  repulsion: number;   // 0–100
  nodeSize: number;    // 0–100
  linkWidth: number;   // 0–100
  showLabels: boolean;
}

const DEFAULT_SETTINGS: GraphSettings = {
  repulsion: 50,
  nodeSize: 50,
  linkWidth: 50,
  showLabels: false,
};

function loadSettings(): GraphSettings {
  try {
    const raw = localStorage.getItem(SETTINGS_KEY);
    if (!raw) return DEFAULT_SETTINGS;
    return { ...DEFAULT_SETTINGS, ...JSON.parse(raw) };
  } catch {
    return DEFAULT_SETTINGS;
  }
}

function persistSettings(s: GraphSettings): void {
  localStorage.setItem(SETTINGS_KEY, JSON.stringify(s));
}

// 0 → charge -100 (dense), 50 → -400 (default), 100 → -700 (sparse)
function sliderToCharge(v: number): number {
  return -100 - (v / 100) * 600;
}

// 0 → distance 60, 50 → 120 (default), 100 → 180
function sliderToLinkDist(v: number): number {
  return 60 + (v / 100) * 120;
}

// 0 → ×0.33, 50 → ×1.0 (default), 100 → ×1.67
function sliderToMult(v: number): number {
  return (v + 25) / 75;
}

// ── Canvas helpers ────────────────────────────────────────────────────────────

function nodeColor(n: FGNode): string {
  if (n.type === "self") return "#9f67ff";
  const s = n.strength;
  if (s >= 0.8) return "#ddd6fe";
  if (s >= 0.6) return "#a78bfa";
  if (s >= 0.4) return "#7c3aed";
  if (s >= 0.2) return "#6d28d9";
  return "#5b21b6";
}

function nodeRadius(n: FGNode): number {
  if (n.type === "self") return 20;
  return 5 + n.strength * 12; // 5–17
}

function linkColor(l: FGLink): string {
  const s = l.strength;
  if (s >= 0.8) return "rgba(221,214,254,0.85)";
  if (s >= 0.6) return "rgba(167,139,250,0.75)";
  if (s >= 0.4) return "rgba(124,58,237,0.55)";
  if (s >= 0.2) return "rgba(109,40,217,0.55)";
  return "rgba(91,33,182,0.45)";
}

// ── Component ─────────────────────────────────────────────────────────────────

export function NetworkPage() {
  const { showToast } = useApp();

  const [graphData, setGraphData] = useState<NetworkGraphType | null>(null);
  const [loading, setLoading] = useState(true);
  const [selectedNode, setSelectedNode] = useState<FGNode | null>(null);
  const [settingsOpen, setSettingsOpen] = useState(false);
  const [settings, setSettings] = useState<GraphSettings>(loadSettings);

  const graphContainerRef = useRef<HTMLDivElement>(null);
  const [graphDims, setGraphDims] = useState({ width: 0, height: 0 });
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  const fgRef = useRef<any>(null);

  // Load graph on mount
  useEffect(() => {
    setLoading(true);
    getNetworkGraph()
      .then((data) => setGraphData(data))
      .catch(() => showToast("Ошибка загрузки графа", "error"))
      .finally(() => setLoading(false));
  }, [showToast]);

  // Apply repulsion / link distance — runs on data load and whenever slider changes
  useEffect(() => {
    if (!fgRef.current || !graphData) return;
    fgRef.current.d3Force("charge")?.strength(sliderToCharge(settings.repulsion));
    fgRef.current.d3Force("link")?.distance(sliderToLinkDist(settings.repulsion));
    fgRef.current.d3ReheatSimulation();
  }, [graphData, settings.repulsion]);

  // Measure container for ForceGraph2D dimensions
  useEffect(() => {
    const el = graphContainerRef.current;
    if (!el) return;
    const immediate = el.getBoundingClientRect();
    if (immediate.width > 0 && immediate.height > 0) {
      setGraphDims({ width: Math.floor(immediate.width), height: Math.floor(immediate.height) });
    }
    const obs = new ResizeObserver((entries) => {
      const rect = entries[0]?.contentRect;
      if (rect && rect.width > 0 && rect.height > 0) {
        setGraphDims({ width: Math.floor(rect.width), height: Math.floor(rect.height) });
      }
    });
    obs.observe(el);
    return () => obs.disconnect();
  }, [loading]);

  // Settings updater — saves to localStorage
  const updateSetting = useCallback(
    <K extends keyof GraphSettings>(key: K, value: GraphSettings[K]) => {
      setSettings((prev) => {
        const next = { ...prev, [key]: value };
        persistSettings(next);
        return next;
      });
    },
    [],
  );

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
  );

  const nodeCanvasObject = useCallback(
    (node: object, ctx: CanvasRenderingContext2D) => {
      const n = node as FGNode;
      const x = n.x ?? 0;
      const y = n.y ?? 0;
      const r = nodeRadius(n) * sliderToMult(settings.nodeSize);
      const fill = nodeColor(n);

      // Glow
      if (n.type === "self") {
        ctx.shadowBlur = 30;
        ctx.shadowColor = "#9f67ff";
      } else if (n.strength >= 0.8) {
        ctx.shadowBlur = 28;
        ctx.shadowColor = "#ddd6fe";
      } else if (n.strength >= 0.6) {
        ctx.shadowBlur = 20;
        ctx.shadowColor = "#a78bfa";
      } else if (n.strength >= 0.4) {
        ctx.shadowBlur = 10;
        ctx.shadowColor = "#7c3aed";
      } else if (n.strength >= 0.2) {
        ctx.shadowBlur = 6;
        ctx.shadowColor = "#6d28d9";
      } else {
        ctx.shadowBlur = 3;
        ctx.shadowColor = "#5b21b6";
      }

      ctx.beginPath();
      ctx.arc(x, y, r, 0, 2 * Math.PI);
      ctx.fillStyle = fill;
      ctx.fill();
      ctx.shadowBlur = 0;

      // Letter inside large enough nodes
      if (r >= 8) {
        ctx.font = `bold ${Math.floor(r * 0.7)}px sans-serif`;
        ctx.textAlign = "center";
        ctx.textBaseline = "middle";
        ctx.fillStyle = "rgba(255,255,255,0.9)";
        ctx.fillText(n.label.charAt(0).toUpperCase(), x, y);
      }

      // Full label below node when enabled
      if (settings.showLabels) {
        const fontSize = Math.max(9, Math.min(12, r * 0.55));
        ctx.font = `${fontSize}px sans-serif`;
        ctx.textAlign = "center";
        ctx.textBaseline = "top";
        ctx.fillStyle = "rgba(240,238,255,0.75)";
        ctx.fillText(n.label, x, y + r + 3);
      }
    },
    [settings.nodeSize, settings.showLabels],
  );

  const nodePointerAreaPaint = useCallback(
    (node: object, color: string, ctx: CanvasRenderingContext2D) => {
      const n = node as FGNode;
      ctx.fillStyle = color;
      ctx.beginPath();
      ctx.arc(
        n.x ?? 0,
        n.y ?? 0,
        nodeRadius(n) * sliderToMult(settings.nodeSize) + 4,
        0,
        2 * Math.PI,
      );
      ctx.fill();
    },
    [settings.nodeSize],
  );

  const getLinkColor = useCallback(
    (link: object) => linkColor(link as FGLink),
    [],
  );

  const getLinkWidth = useCallback(
    (link: object) => {
      const l = link as FGLink;
      return (0.5 + l.strength * 4) * sliderToMult(settings.linkWidth);
    },
    [settings.linkWidth],
  );

  const getLinkParticleWidth = useCallback((link: object) => {
    const l = link as FGLink;
    if (l.strength >= 0.7) return 3;
    if (l.strength >= 0.4) return 1.5;
    return 0;
  }, []);

  const handleNodeClick = useCallback((node: object) => {
    setSettingsOpen(false);
    setSelectedNode(node as FGNode);
  }, []);

  const handleEngineStop = useCallback(() => {
    fgRef.current?.zoomToFit(400, 48);
  }, []);

  // ── Render: loading ──────────────────────────────────────────────────────────

  if (loading) {
    return (
      <div className="loading-center" style={{ flex: 1 }}>
        <div className="spinner" />
      </div>
    );
  }

  const contactCount = (graphData?.nodes.length ?? 0) - 1;
  const hasContacts = contactCount > 0;

  // ── Render ───────────────────────────────────────────────────────────────────

  return (
    <div
      style={{
        flex: 1,
        display: "flex",
        flexDirection: "column",
        overflow: "hidden",
      }}
    >
      {/* Top bar */}
      <div
        style={{
          display: "flex",
          alignItems: "center",
          justifyContent: "space-between",
          padding: "10px 16px",
          background: "rgba(13,13,20,0.9)",
          backdropFilter: "blur(12px)",
          WebkitBackdropFilter: "blur(12px)",
          borderBottom: "1px solid var(--purple-border)",
          flexShrink: 0,
          zIndex: 10,
        }}
      >
        <div>
          <span style={{ fontWeight: 700, fontSize: 16 }}>Мои связи</span>
          {graphData && (
            <span style={{ fontSize: 12, color: "var(--text2)", marginLeft: 8 }}>
              {contactCount} контактов
            </span>
          )}
        </div>

        {/* Settings button */}
        {hasContacts && (
          <button
            onClick={() => {
              setSelectedNode(null);
              setSettingsOpen(true);
            }}
            style={{
              background: settingsOpen
                ? "rgba(124,58,237,0.2)"
                : "rgba(255,255,255,0.04)",
              border: "1px solid var(--purple-border)",
              borderRadius: 8,
              color: settingsOpen ? "var(--purple-l)" : "var(--text2)",
              padding: "6px 10px",
              cursor: "pointer",
              display: "flex",
              alignItems: "center",
              gap: 5,
              fontSize: 13,
              fontWeight: 500,
              transition: "background 0.15s, color 0.15s",
              WebkitTapHighlightColor: "transparent",
            }}
            aria-label="Настройки графа"
          >
            {/* Sliders icon */}
            <svg
              width="16"
              height="16"
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
              strokeWidth="2"
              strokeLinecap="round"
              strokeLinejoin="round"
            >
              <line x1="4" y1="6" x2="20" y2="6" />
              <line x1="4" y1="12" x2="20" y2="12" />
              <line x1="4" y1="18" x2="20" y2="18" />
              <circle cx="8" cy="6" r="2" fill="currentColor" stroke="none" />
              <circle cx="15" cy="12" r="2" fill="currentColor" stroke="none" />
              <circle cx="10" cy="18" r="2" fill="currentColor" stroke="none" />
            </svg>
            Вид
          </button>
        )}
      </div>

      {/* Graph area */}
      <div
        ref={graphContainerRef}
        style={{
          flex: 1,
          position: "relative",
          overflow: "hidden",
          background: "#0d0d14",
        }}
      >
        {!hasContacts ? (
          <div
            style={{
              display: "flex",
              flexDirection: "column",
              alignItems: "center",
              justifyContent: "center",
              height: "100%",
              padding: 24,
              textAlign: "center",
            }}
          >
            <div style={{ fontSize: 56, marginBottom: 16 }}>🌌</div>
            <div style={{ fontWeight: 700, fontSize: 18, marginBottom: 8 }}>
              Нет данных
            </div>
            <div
              style={{
                color: "var(--text2)",
                fontSize: 14,
                textAlign: "center",
                lineHeight: 1.5,
              }}
            >
              Тут вы сможете увидеть ваши связи
            </div>
          </div>
        ) : (
          graphDims.width > 0 &&
          graphDims.height > 0 && (
            <ForceGraph2D
              ref={fgRef}
              graphData={fgData}
              width={graphDims.width}
              height={graphDims.height}
              backgroundColor="#0d0d14"
              nodeCanvasObject={nodeCanvasObject}
              nodePointerAreaPaint={nodePointerAreaPaint}
              nodeLabel={() => ""}
              linkColor={getLinkColor}
              linkWidth={getLinkWidth}
              onNodeClick={handleNodeClick}
              onEngineStop={handleEngineStop}
              cooldownTicks={100}
              d3AlphaDecay={0.02}
              d3VelocityDecay={0.3}
              linkDirectionalParticles={2}
              linkDirectionalParticleWidth={getLinkParticleWidth}
              linkDirectionalParticleColor={() => "rgba(167,139,250,0.8)"}
            />
          )
        )}
      </div>

      {/* Node detail bottom sheet */}
      {selectedNode && (
        <div
          style={{
            position: "fixed",
            inset: 0,
            background: "rgba(0,0,0,0.55)",
            zIndex: 200,
            display: "flex",
            alignItems: "flex-end",
          }}
          onClick={() => setSelectedNode(null)}
        >
          <div
            style={{
              background: "var(--bg-card)",
              borderRadius: "20px 20px 0 0",
              border: "1px solid var(--purple-border)",
              padding: "16px 20px",
              paddingBottom: "calc(var(--nav-total) + 20px)",
              width: "100%",
              maxHeight: "60vh",
              overflow: "auto",
            }}
            onClick={(e) => e.stopPropagation()}
          >
            {/* Drag handle */}
            <div
              style={{
                width: 36,
                height: 4,
                background: "var(--text3)",
                borderRadius: 2,
                margin: "0 auto 20px",
              }}
            />

            {/* Header */}
            <div
              style={{
                display: "flex",
                alignItems: "center",
                gap: 14,
                marginBottom: 16,
              }}
            >
              <div
                style={{
                  width: 48,
                  height: 48,
                  borderRadius: "50%",
                  background: nodeColor(selectedNode),
                  display: "flex",
                  alignItems: "center",
                  justifyContent: "center",
                  fontSize: 20,
                  fontWeight: 700,
                  color: "#fff",
                  flexShrink: 0,
                  boxShadow:
                    selectedNode.type === "self" || selectedNode.strength > 0.6
                      ? "0 0 12px rgba(124,58,237,0.5)"
                      : "none",
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
                <div style={{ display: "flex", gap: 6, flexWrap: "wrap" }}>
                  {selectedNode.type === "self" && (
                    <span className="badge badge-gray">Вы</span>
                  )}
                </div>
              </div>
            </div>

            <div className="divider" />

            {/* Stats */}
            <div
              style={{
                display: "flex",
                flexDirection: "column",
                gap: 12,
                marginTop: 12,
              }}
            >
              <InfoRow label="Сообщений" value={selectedNode.message_count} />
              {selectedNode.trust_score !== null && (
                <InfoRow
                  label="Доверие"
                  value={`${selectedNode.trust_score} / 100`}
                />
              )}
            </div>

            {/* Strength bar */}
            {selectedNode.type !== "self" && (
              <div style={{ marginTop: 16 }}>
                <div
                  style={{
                    display: "flex",
                    justifyContent: "space-between",
                    marginBottom: 4,
                  }}
                >
                  <span style={{ fontSize: 12, color: "var(--text2)" }}>
                    Сила связи
                  </span>
                  <span style={{ fontSize: 12, fontWeight: 600 }}>
                    {Math.round(selectedNode.strength * 100)}%
                  </span>
                </div>
                <div
                  style={{
                    height: 4,
                    background: "var(--bg-card2)",
                    borderRadius: 2,
                  }}
                >
                  <div
                    style={{
                      height: "100%",
                      borderRadius: 2,
                      width: `${selectedNode.strength * 100}%`,
                      background:
                        selectedNode.strength > 0.6
                          ? "linear-gradient(90deg, #7c3aed, #a78bfa)"
                          : "var(--purple-d)",
                      boxShadow:
                        selectedNode.strength > 0.6
                          ? "0 0 8px var(--purple-glow)"
                          : "none",
                    }}
                  />
                </div>
              </div>
            )}
          </div>
        </div>
      )}

      {/* Graph settings bottom sheet */}
      {settingsOpen && (
        <div
          style={{
            position: "fixed",
            inset: 0,
            background: "rgba(0,0,0,0.55)",
            zIndex: 200,
            display: "flex",
            alignItems: "flex-end",
          }}
          onClick={() => setSettingsOpen(false)}
        >
          <div
            style={{
              background: "var(--bg-card)",
              borderRadius: "20px 20px 0 0",
              border: "1px solid var(--purple-border)",
              padding: "16px 20px",
              paddingBottom: "calc(var(--nav-total) + 20px)",
              width: "100%",
              maxHeight: "80vh",
              overflow: "auto",
            }}
            onClick={(e) => e.stopPropagation()}
          >
            {/* Drag handle */}
            <div
              style={{
                width: 36,
                height: 4,
                background: "var(--text3)",
                borderRadius: 2,
                margin: "0 auto 20px",
              }}
            />

            {/* Title */}
            <div
              style={{
                fontWeight: 700,
                fontSize: 17,
                marginBottom: 24,
                color: "var(--text)",
              }}
            >
              Настройки графа
            </div>

            {/* Sliders */}
            <SettingSlider
              label="Плотность связей"
              value={settings.repulsion}
              onChange={(v) => updateSetting("repulsion", v)}
            />
            <SettingSlider
              label="Размер узлов"
              value={settings.nodeSize}
              onChange={(v) => updateSetting("nodeSize", v)}
            />
            <SettingSlider
              label="Толщина рёбер"
              value={settings.linkWidth}
              onChange={(v) => updateSetting("linkWidth", v)}
            />

            <div className="divider" />

            {/* Show labels toggle */}
            <div
              style={{
                display: "flex",
                justifyContent: "space-between",
                alignItems: "center",
                padding: "4px 0 20px",
              }}
            >
              <div>
                <div style={{ fontSize: 14, color: "var(--text)", fontWeight: 500 }}>
                  Показывать подписи
                </div>
                <div style={{ fontSize: 12, color: "var(--text3)", marginTop: 2 }}>
                  Имена контактов под узлами
                </div>
              </div>
              <button
                onClick={() => updateSetting("showLabels", !settings.showLabels)}
                style={{
                  width: 50,
                  height: 28,
                  borderRadius: 14,
                  background: settings.showLabels
                    ? "var(--purple)"
                    : "rgba(255,255,255,0.1)",
                  border: "none",
                  cursor: "pointer",
                  position: "relative",
                  transition: "background 0.2s",
                  flexShrink: 0,
                  WebkitTapHighlightColor: "transparent",
                }}
                aria-label="Переключить подписи"
              >
                <span
                  style={{
                    position: "absolute",
                    top: 3,
                    left: settings.showLabels ? 25 : 3,
                    width: 22,
                    height: 22,
                    borderRadius: "50%",
                    background: "#fff",
                    boxShadow: "0 1px 4px rgba(0,0,0,0.35)",
                    transition: "left 0.2s",
                    display: "block",
                  }}
                />
              </button>
            </div>

            {/* Reset button */}
            <button
              className="btn btn-secondary"
              onClick={() => {
                const defaults = { ...DEFAULT_SETTINGS };
                setSettings(defaults);
                persistSettings(defaults);
              }}
            >
              Сбросить настройки
            </button>
          </div>
        </div>
      )}
    </div>
  );
}

// ── Helpers ───────────────────────────────────────────────────────────────────

function InfoRow({ label, value }: { label: string; value: string | number }) {
  return (
    <div
      style={{
        display: "flex",
        justifyContent: "space-between",
        alignItems: "center",
      }}
    >
      <span style={{ color: "var(--text2)", fontSize: 14 }}>{label}</span>
      <span style={{ fontWeight: 600, fontSize: 14 }}>{value}</span>
    </div>
  );
}

function SettingSlider({
  label,
  value,
  onChange,
}: {
  label: string;
  value: number;
  onChange: (v: number) => void;
}) {
  const pct = value; // value is already 0–100
  return (
    <div style={{ marginBottom: 22 }}>
      <div
        style={{
          display: "flex",
          justifyContent: "space-between",
          alignItems: "baseline",
          marginBottom: 10,
        }}
      >
        <span style={{ fontSize: 14, color: "var(--text)", fontWeight: 500 }}>
          {label}
        </span>
        <span
          style={{
            fontSize: 13,
            color: "var(--purple-l)",
            fontWeight: 600,
            minWidth: 28,
            textAlign: "right",
          }}
        >
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
            background: `linear-gradient(to right, var(--purple-l) 0%, var(--purple-l) ${pct}%, var(--bg-card2) ${pct}%, var(--bg-card2) 100%)`,
          }}
        />
      </div>
    </div>
  );
}
