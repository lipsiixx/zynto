interface Props {
  score: number
  size?: number
  isManual?: boolean
}

function trustColor(score: number): string {
  if (score >= 70) return '#7c3aed'
  if (score >= 45) return '#d69e2e'
  return '#e53e3e'
}

export function TrustCircle({ score, size = 80, isManual = false }: Props) {
  const r = (size - 10) / 2
  const circ = 2 * Math.PI * r
  const fill = (score / 100) * circ
  const color = trustColor(score)

  return (
    <div className="trust-wrap">
      <div className="trust-circle" style={{ width: size, height: size }}>
        <svg width={size} height={size}>
          <circle
            cx={size / 2} cy={size / 2} r={r}
            fill="none" stroke="rgba(255,255,255,0.07)" strokeWidth={6}
          />
          <circle
            cx={size / 2} cy={size / 2} r={r}
            fill="none" stroke={color} strokeWidth={6}
            strokeDasharray={`${fill} ${circ - fill}`}
            strokeLinecap="round"
            style={{ filter: `drop-shadow(0 0 6px ${color}88)`, transition: 'stroke-dasharray 0.4s ease' }}
          />
        </svg>
        <div className="score-text" style={{ color }}>
          {score}
          <span className="score-label">{isManual ? 'ручной' : 'авто'}</span>
        </div>
      </div>
    </div>
  )
}

interface BarProps {
  score: number
  compact?: boolean
}

export function TrustBar({ score, compact = false }: BarProps) {
  const color = trustColor(score)
  if (compact) {
    return (
      <div className="trust-bar-wrap">
        <div className="trust-bar">
          <div className="trust-bar-fill" style={{ width: `${score}%`, background: color }} />
        </div>
        <span className="trust-score-num" style={{ color }}>{score}</span>
      </div>
    )
  }
  return (
    <div style={{ width: '100%' }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 6 }}>
        <span style={{ fontSize: 12, color: 'var(--text2)' }}>Кредит доверия</span>
        <span style={{ fontSize: 12, fontWeight: 700, color }}>{score}/100</span>
      </div>
      <div className="trust-bar" style={{ height: 8 }}>
        <div className="trust-bar-fill" style={{ width: `${score}%`, background: color }} />
      </div>
    </div>
  )
}
