import {
  Bar,
  BarChart,
  CartesianGrid,
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts'

// Палитра прогнана через валидатор dataviz-скилла на поверхности --bg-card
// (#14142a, dark): lightness band / chroma / CVD-разделение / контраст — PASS.
// Семантика совпадает с остальной админкой: удалённые — красный, изменённые — жёлтый.
export const CHART_COLORS = {
  messages: '#9f7aea',
  deleted: '#e53e3e',
  edited: '#c08a1e',
  paid: '#38a169',
} as const

const GRID_STROKE = 'rgba(157, 147, 192, 0.15)'
const TICK_STYLE = { fill: 'var(--text2)', fontSize: 11 }

export function fmtTickDate(iso: string): string {
  // "2026-07-03" → "03.07"
  return `${iso.slice(8, 10)}.${iso.slice(5, 7)}`
}

function fmtFullDate(iso: string): string {
  return new Date(`${iso}T00:00:00`).toLocaleDateString('ru-RU', {
    day: 'numeric',
    month: 'long',
  })
}

export const tooltipProps = {
  contentStyle: {
    background: 'var(--bg-card2)',
    border: '1px solid var(--purple-border)',
    borderRadius: 10,
    fontSize: 12,
    padding: '8px 10px',
  },
  labelStyle: { color: 'var(--text)', fontWeight: 600, marginBottom: 4 },
  itemStyle: { color: 'var(--text2)', padding: 0 },
  labelFormatter: (label: string) => fmtFullDate(label),
  cursor: { stroke: GRID_STROKE },
} as const

/** Легенда своими руками: recharts красит текст цветом серии, а текст должен
    носить текстовые токены — цвет несёт только маркер рядом. */
export function ChartLegend({ items }: { items: { label: string; color: string }[] }) {
  return (
    <div className="row gap-8" style={{ flexWrap: 'wrap', marginTop: 8 }}>
      {items.map(it => (
        <span key={it.label} className="row text-xs text2" style={{ gap: 5, alignItems: 'center' }}>
          <span style={{ width: 8, height: 8, borderRadius: '50%', background: it.color, flexShrink: 0 }} />
          {it.label}
        </span>
      ))}
    </div>
  )
}

interface MsgPoint {
  date: string
  messages: number
  deleted: number
  edited: number
}

/** Линии сообщений/удалённых/изменённых по дням — общий график для глобальной
    статистики и страницы пользователя. */
export function MessagesChart({ data }: { data: MsgPoint[] }) {
  return (
    <>
      <div style={{ width: '100%', height: 220 }}>
        <ResponsiveContainer>
          <LineChart data={data} margin={{ top: 8, right: 8, bottom: 0, left: -18 }}>
            <CartesianGrid stroke={GRID_STROKE} vertical={false} />
            <XAxis dataKey="date" tickFormatter={fmtTickDate} tick={TICK_STYLE} axisLine={false} tickLine={false} minTickGap={28} />
            <YAxis tick={TICK_STYLE} axisLine={false} tickLine={false} allowDecimals={false} />
            <Tooltip {...tooltipProps} />
            <Line type="monotone" dataKey="messages" name="Сообщения" stroke={CHART_COLORS.messages} strokeWidth={2} dot={false} activeDot={{ r: 4 }} />
            <Line type="monotone" dataKey="deleted" name="Удалённые" stroke={CHART_COLORS.deleted} strokeWidth={2} dot={false} activeDot={{ r: 4 }} />
            <Line type="monotone" dataKey="edited" name="Изменённые" stroke={CHART_COLORS.edited} strokeWidth={2} dot={false} activeDot={{ r: 4 }} />
          </LineChart>
        </ResponsiveContainer>
      </div>
      <ChartLegend
        items={[
          { label: 'Сообщения', color: CHART_COLORS.messages },
          { label: 'Удалённые', color: CHART_COLORS.deleted },
          { label: 'Изменённые', color: CHART_COLORS.edited },
        ]}
      />
    </>
  )
}

/** Столбцы одной серии (новые пользователи) — легенда не нужна, серию называет
    заголовок карточки. */
export function SingleBarChart<T extends { date: string }>({ data, dataKey, name, color }: {
  data: T[]
  dataKey: keyof T & string
  name: string
  color: string
}) {
  return (
    <div style={{ width: '100%', height: 200 }}>
      <ResponsiveContainer>
        <BarChart data={data} margin={{ top: 8, right: 8, bottom: 0, left: -18 }} barCategoryGap="25%">
          <CartesianGrid stroke={GRID_STROKE} vertical={false} />
          <XAxis dataKey="date" tickFormatter={fmtTickDate} tick={TICK_STYLE} axisLine={false} tickLine={false} minTickGap={28} />
          <YAxis tick={TICK_STYLE} axisLine={false} tickLine={false} allowDecimals={false} />
          <Tooltip {...tooltipProps} cursor={{ fill: 'rgba(157, 147, 192, 0.08)' }} />
          <Bar dataKey={dataKey} name={name} fill={color} radius={[4, 4, 0, 0]} maxBarSize={16} />
        </BarChart>
      </ResponsiveContainer>
    </div>
  )
}

interface GrantPoint {
  date: string
  grants: number
  paid: number
}

/** Сгруппированные столбцы: все выдачи против реальных оплат (Stars/СБП). */
export function GrantsChart({ data }: { data: GrantPoint[] }) {
  return (
    <>
      <div style={{ width: '100%', height: 200 }}>
        <ResponsiveContainer>
          <BarChart data={data} margin={{ top: 8, right: 8, bottom: 0, left: -18 }} barCategoryGap="20%" barGap={2}>
            <CartesianGrid stroke={GRID_STROKE} vertical={false} />
            <XAxis dataKey="date" tickFormatter={fmtTickDate} tick={TICK_STYLE} axisLine={false} tickLine={false} minTickGap={28} />
            <YAxis tick={TICK_STYLE} axisLine={false} tickLine={false} allowDecimals={false} />
            <Tooltip {...tooltipProps} cursor={{ fill: 'rgba(157, 147, 192, 0.08)' }} />
            <Bar dataKey="grants" name="Все выдачи" fill={CHART_COLORS.messages} radius={[4, 4, 0, 0]} maxBarSize={12} />
            <Bar dataKey="paid" name="Оплаты" fill={CHART_COLORS.paid} radius={[4, 4, 0, 0]} maxBarSize={12} />
          </BarChart>
        </ResponsiveContainer>
      </div>
      <ChartLegend
        items={[
          { label: 'Все выдачи (промо, вручную, подарки)', color: CHART_COLORS.messages },
          { label: 'Оплаты (Stars / СБП)', color: CHART_COLORS.paid },
        ]}
      />
    </>
  )
}

/** Рейтинговая строка: имя + горизонтальный бар, ширина пропорциональна max. */
export function RankRow({ rank, label, sublabel, value, max, extra, onClick }: {
  rank: number
  label: string
  sublabel?: string
  value: number
  max: number
  extra?: string
  onClick?: () => void
}) {
  const pct = max > 0 ? Math.max(2, (value / max) * 100) : 0
  return (
    <div
      onClick={onClick}
      style={{ padding: '8px 0', cursor: onClick ? 'pointer' : undefined }}
    >
      <div className="row" style={{ justifyContent: 'space-between', alignItems: 'baseline', gap: 8 }}>
        <span className="text-sm" style={{ minWidth: 0, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
          <span className="text2" style={{ marginRight: 6 }}>{rank}.</span>
          <span className="semibold">{label}</span>
          {sublabel && <span className="text-xs text2" style={{ marginLeft: 6 }}>{sublabel}</span>}
        </span>
        <span className="text-sm semibold" style={{ flexShrink: 0 }}>
          {value}
          {extra && <span className="text-xs text2" style={{ marginLeft: 6 }}>{extra}</span>}
        </span>
      </div>
      <div className="admin-progress-bar" style={{ height: 4, marginTop: 5 }}>
        <div className="admin-progress-fill" style={{ width: `${pct}%`, background: CHART_COLORS.messages }} />
      </div>
    </div>
  )
}
