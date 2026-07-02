import { useCallback, useEffect, useState } from 'react'
import { PolarAngleAxis, RadialBar, RadialBarChart, ResponsiveContainer } from 'recharts'
import { formatBytes, formatUptime, pctColor, proxyStateLabel } from '@/admin/shared/lib/format'
import {
  getGlobalUserStats,
  getProxyStats,
  getServerStats,
  type GlobalUserStats,
  type ProxyInfo,
  type ProxyStats,
  type ServerStats,
} from '@/admin/entities/stats'

export function StatsPage() {
  const [userStats, setUserStats] = useState<GlobalUserStats | null>(null)
  const [serverStats, setServerStats] = useState<ServerStats | null>(null)
  const [proxyStats, setProxyStats] = useState<ProxyStats | null>(null)
  const [loading, setLoading] = useState(true)

  const load = useCallback(() => {
    setLoading(true)
    Promise.all([
      getGlobalUserStats().then(setUserStats).catch(() => {}),
      getServerStats().then(setServerStats).catch(() => {}),
      getProxyStats().then(setProxyStats).catch(() => {}),
    ]).finally(() => setLoading(false))
  }, [])

  useEffect(() => {
    load()
  }, [load])

  return (
    <div className="admin-page">
      <div className="admin-page-header">
        <h1 style={{ marginBottom: 0 }}>Статистика</h1>
        <button className="admin-icon-btn" onClick={load} disabled={loading}>
          {loading ? '...' : '↻ Обновить'}
        </button>
      </div>

      {/* Users */}
      <div className="admin-section-title">Пользователи</div>
      <div className="admin-grid-4" style={{ marginBottom: 4 }}>
        <UserStat label="Всего" value={userStats?.total} />
        <UserStat label="Онлайн" value={userStats?.online} color="var(--green)" />
        <UserStat label="Новых сегодня" value={userStats?.newToday} color="var(--purple-l)" />
        <UserStat label="Новых за неделю" value={userStats?.newThisWeek} color="var(--purple-l)" />
        <UserStat label="Активных подписок" value={userStats?.activeSubscribers} color="var(--green)" />
      </div>

      {/* Server */}
      <div className="admin-section-title">Сервер</div>
      {serverStats ? (
        <div className="admin-grid-2">
          {/* CPU gauge */}
          <div className="card">
            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 8 }}>
              <span style={{ fontWeight: 600 }}>CPU</span>
              <span style={{ fontSize: 22, fontWeight: 700, color: pctColor(serverStats.cpu.usagePercent) }}>
                {serverStats.cpu.usagePercent.toFixed(1)}%
              </span>
            </div>
            <CpuGauge pct={serverStats.cpu.usagePercent} />
            <div className="text-sm text2" style={{ marginTop: 4 }}>
              {serverStats.cpu.cores} ядер · LA: {serverStats.loadAvg.map((x) => x.toFixed(2)).join(' / ')}
            </div>
          </div>

          {/* Memory + Disk */}
          <div className="card">
            <ResourceBar label="Оперативная память" used={serverStats.memory.usedBytes} total={serverStats.memory.totalBytes} />
            <div style={{ height: 14 }} />
            <ResourceBar label="Диск" used={serverStats.disk.usedBytes} total={serverStats.disk.totalBytes} />
            <div className="text-sm text2" style={{ marginTop: 14 }}>
              Uptime: {formatUptime(serverStats.uptimeSeconds)}
            </div>
          </div>
        </div>
      ) : (
        <div className="text-sm text2">Загрузка...</div>
      )}

      {/* Proxy */}
      <div className="admin-section-title">Прокси</div>
      <div className="card">
        {proxyStats?.noProxy ? (
          <div className="text-sm text2">Прокси не настроен</div>
        ) : proxyStats?.active ? (
          <ProxyCard info={proxyStats.active} />
        ) : (
          <div className="text-sm text2">Загрузка...</div>
        )}
      </div>
    </div>
  )
}

function UserStat({ label, value, color }: { label: string; value: number | undefined; color?: string }) {
  return (
    <div className="admin-stat-card">
      <div className="admin-stat-label">{label}</div>
      <div className="admin-stat-value" style={color ? { color } : undefined}>
        {value ?? '—'}
      </div>
    </div>
  )
}

function ResourceBar({ label, used, total }: { label: string; used: number; total: number }) {
  const pct = total ? (used / total) * 100 : 0
  const color = pct > 85 ? 'var(--red)' : pct > 60 ? 'var(--yellow)' : undefined
  return (
    <div>
      <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: 13, marginBottom: 6 }}>
        <span style={{ fontWeight: 500 }}>{label}</span>
        <span className="text2">
          {formatBytes(used)} / {formatBytes(total)}
        </span>
      </div>
      <div className="admin-progress-bar" style={{ height: 8 }}>
        <div className="admin-progress-fill" style={{ width: `${pct.toFixed(1)}%`, background: color }} />
      </div>
      <div className="text-sm text2" style={{ marginTop: 4, textAlign: 'right' }}>
        {pct.toFixed(1)}%
      </div>
    </div>
  )
}

function CpuGauge({ pct }: { pct: number }) {
  const data = [{ value: pct, fill: pctColor(pct) }]
  return (
    <div className="admin-gauge-wrap">
      <ResponsiveContainer width="100%" height="100%">
        <RadialBarChart innerRadius="65%" outerRadius="100%" startAngle={225} endAngle={-45} data={data} barSize={14}>
          <PolarAngleAxis type="number" domain={[0, 100]} angleAxisId={0} tick={false} />
          <RadialBar background={{ fill: 'var(--bg-card2)' }} dataKey="value" cornerRadius={6} angleAxisId={0} />
        </RadialBarChart>
      </ResponsiveContainer>
    </div>
  )
}

function ProxyCard({ info }: { info: ProxyInfo }) {
  const stateColors: Record<string, string> = { ok: 'var(--green)', degraded: 'var(--yellow)', down: 'var(--red)' }
  return (
    <div>
      <div style={{ display: 'flex', alignItems: 'center', gap: 10, marginBottom: 10 }}>
        <span className={`admin-dot ${info.state}`} />
        <span style={{ fontWeight: 600, color: stateColors[info.state] || 'var(--text)' }}>
          {proxyStateLabel(info.state)}
        </span>
        {info.monitorRunning && <span className="badge badge-purple">Мониторинг ✓</span>}
      </div>
      <div className="text2" style={{ fontFamily: 'monospace', fontSize: 12, wordBreak: 'break-all', marginBottom: 12 }}>
        {info.proxy}
      </div>
      <div className="admin-grid-4">
        <MiniStat label="Задержка" value={info.avgLatencySeconds ? `${(info.avgLatencySeconds * 1000).toFixed(0)} мс` : '—'} />
        <MiniStat label="Сбоев (окно)" value={info.failsInWindow} />
        <MiniStat label="Посл. успешных" value={info.consecutiveOks} />
        <MiniStat label="Посл. сбоев" value={info.consecutiveFails} />
      </div>
    </div>
  )
}

function MiniStat({ label, value }: { label: string; value: string | number }) {
  return (
    <div>
      <div className="text-sm text2">{label}</div>
      <div style={{ fontWeight: 600 }}>{value}</div>
    </div>
  )
}
