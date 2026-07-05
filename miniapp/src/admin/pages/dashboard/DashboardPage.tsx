import { useCallback, useEffect, useState } from 'react'
import { mediaUrl, reqLegacy } from '@/admin/shared/api/adminApi'
import { useAdminWs } from '@/admin/shared/lib/useAdminWs'
import {
  formatBytes,
  formatRelTime,
  formatUptime,
  MSG_TYPE_ICON,
  MSG_TYPE_LABEL,
  proxyStateLabel,
} from '@/admin/shared/lib/format'
import {
  getGlobalUserStats,
  getProxyStats,
  getServerStats,
  type FeedEvent,
  type GlobalUserStats,
  type ProxyStats,
  type ServerStats,
  type WsEvent,
} from '@/admin/entities/stats'
import { getOverview, type OverviewOut } from '@/admin/entities/overview'

const EVENT_LABELS: Record<string, { label: string; cls: string }> = {
  'message.new': { label: 'Новое сообщение', cls: 'new' },
  'message.updated': { label: 'Изменено', cls: 'updated' },
  'message.deleted': { label: 'Удалено', cls: 'deleted' },
  'stats.refresh': { label: 'Очистка данных', cls: 'system' },
  'cache.invalidated': { label: 'Сброс кэша', cls: 'system' },
}

const MAX_EVENTS = 50
const SERVER_POLL_MS = 15000

let _feedIdCounter = 0

export function DashboardPage() {
  const [userStats, setUserStats] = useState<GlobalUserStats | null>(null)
  const [serverStats, setServerStats] = useState<ServerStats | null>(null)
  const [serverLoading, setServerLoading] = useState(true)
  const [proxyStats, setProxyStats] = useState<ProxyStats | null>(null)
  const [events, setEvents] = useState<FeedEvent[]>([])
  const [invalidating, setInvalidating] = useState(false)
  const [overview, setOverview] = useState<OverviewOut | null>(null)

  const loadServerStats = useCallback(() => {
    setServerLoading(true)
    getServerStats()
      .then(setServerStats)
      .catch(() => {})
      .finally(() => setServerLoading(false))
  }, [])

  useEffect(() => {
    getGlobalUserStats().then(setUserStats).catch(() => {})
    getProxyStats().then(setProxyStats).catch(() => {})
    getOverview().then(setOverview).catch(() => {})
    loadServerStats()

    const interval = setInterval(loadServerStats, SERVER_POLL_MS)
    return () => clearInterval(interval)
  }, [loadServerStats])

  const handleWsEvent = useCallback((ev: WsEvent) => {
    setEvents((prev) => [{ ...ev, _id: ++_feedIdCounter, _receivedAt: Date.now() }, ...prev].slice(0, MAX_EVENTS))
  }, [])
  const wsConnected = useAdminWs(handleWsEvent)

  const invalidateCache = useCallback(() => {
    setInvalidating(true)
    reqLegacy('POST', '/cache/invalidate', { scope: 'all' })
      .catch(() => {})
      .finally(() => setInvalidating(false))
  }, [])

  const proxyInfo = proxyStats?.active
  const proxyState = proxyInfo?.state ?? (proxyStats?.noProxy ? 'no_proxy' : 'unknown')

  return (
    <div className="admin-page">
      <div className="admin-page-header">
        <div>
          <h1 style={{ marginBottom: 2 }}>Дашборд</h1>
          <p className="text2 text-sm">Общее состояние бота @zynto_bot</p>
        </div>
        <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
          <span className={`admin-dot ${wsConnected ? 'ok' : 'down'}`} />
          <span className="text2 text-sm">{wsConnected ? 'WS подключён' : 'WS отключён'}</span>
        </div>
      </div>

      {/* Stat cards */}
      <div className="admin-grid-4" style={{ marginBottom: 20 }}>
        <StatCard label="Всего пользователей" value={userStats?.total} />
        <StatCard label="Онлайн сейчас" value={userStats?.online} color="var(--green)" />
        <StatCard label="Новых сегодня" value={userStats?.newToday} />
        <StatCard label="Активных подписок" value={userStats?.activeSubscribers} color="var(--purple-l)" />
      </div>

      <div className="admin-grid-2" style={{ marginBottom: 20 }}>
        {/* Server strip */}
        <div className="card">
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 12 }}>
            <span style={{ fontWeight: 600, fontSize: 14 }}>Сервер</span>
            {serverLoading && <div className="spinner" style={{ width: 16, height: 16, borderWidth: 2 }} />}
          </div>
          {serverStats ? (
            <>
              <MiniBar label="CPU" pct={serverStats.cpu.usagePercent} suffix={`${serverStats.cpu.cores} ядер`} />
              <MiniBar
                label="RAM"
                pct={(serverStats.memory.usedBytes / serverStats.memory.totalBytes) * 100}
                suffix={`${formatBytes(serverStats.memory.usedBytes)} / ${formatBytes(serverStats.memory.totalBytes)}`}
              />
              <MiniBar
                label="Диск"
                pct={(serverStats.disk.usedBytes / serverStats.disk.totalBytes) * 100}
                suffix={`${formatBytes(serverStats.disk.usedBytes)} / ${formatBytes(serverStats.disk.totalBytes)}`}
              />
              <div className="text-sm text2" style={{ marginTop: 4 }}>
                Uptime: {formatUptime(serverStats.uptimeSeconds)}
              </div>
            </>
          ) : (
            <div className="text-sm text2">Загрузка...</div>
          )}
        </div>

        {/* Proxy */}
        <div className="card">
          <div style={{ fontWeight: 600, fontSize: 14, marginBottom: 12 }}>Прокси</div>
          {proxyInfo ? (
            <>
              <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 10 }}>
                <span className={`admin-dot ${proxyState}`} />
                <span style={{ fontSize: 13, fontWeight: 600 }}>{proxyStateLabel(proxyState)}</span>
              </div>
              <div
                className="text-sm text2"
                style={{ wordBreak: 'break-all', fontFamily: 'monospace', marginBottom: 10 }}
              >
                {proxyInfo.proxy}
              </div>
              <div className="admin-grid-2" style={{ gap: 10 }}>
                <MiniStat
                  label="Задержка"
                  value={proxyInfo.avgLatencySeconds ? `${(proxyInfo.avgLatencySeconds * 1000).toFixed(0)} мс` : '—'}
                />
                <MiniStat label="Сбоев (окно)" value={proxyInfo.failsInWindow} />
              </div>
              {proxyInfo.lastCheckedSecondsAgo != null && (
                <div className="text-sm text2" style={{ marginTop: 8 }}>
                  Проверен {formatRelTime(proxyInfo.lastCheckedSecondsAgo * 1000)} назад
                </div>
              )}
            </>
          ) : proxyStats?.noProxy ? (
            <div className="text-sm text2">Прокси не настроен</div>
          ) : (
            <div className="text-sm text2">Загрузка...</div>
          )}
        </div>
      </div>

      {/* Overview (GET /v1/webapp/admin/overview — services.stats.collect_stats) */}
      {overview && (
        <>
          <div className="admin-section-title">Обзор бота</div>
          <div className="admin-grid-4" style={{ marginBottom: 20 }}>
            <StatCard label="Подписок активно" value={overview.sub_active} color="var(--green)" />
            <StatCard label="Подписок навсегда" value={overview.sub_lifetime} color="var(--purple-l)" />
            <StatCard label="Подписок истекло" value={overview.sub_expired} color="var(--red)" />
            <StatCard label="Бизнес-подключений" value={overview.biz_connected} />
            <StatCard label="Сообщений всего" value={overview.messages_total} />
            <StatCard label="Удалено сообщений" value={overview.messages_deleted} color="var(--red)" />
            <StatCard label="Изменено сообщений" value={overview.messages_edited} color="var(--yellow)" />
            <StatCard label="Промокодов создано" value={overview.promo_total} color="var(--purple-l)" />
            <StatCard label="Промокодов использовано" value={overview.promo_used} />
          </div>
        </>
      )}

      {/* Live events */}
      <div className="card">
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 12 }}>
          <span style={{ fontWeight: 600, fontSize: 14 }}>Live-события</span>
          <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
            <span className="text-sm text2">{events.length} событий</span>
            <button className="admin-icon-btn" onClick={invalidateCache} disabled={invalidating}>
              {invalidating ? '...' : '↻ Сбросить кэш'}
            </button>
          </div>
        </div>
        {events.length === 0 ? (
          <div className="empty-state" style={{ padding: '24px 0' }}>
            <div style={{ fontSize: 13, color: 'var(--text2)' }}>Ожидание событий...</div>
            <div className="text-sm text3" style={{ marginTop: 4 }}>
              Сообщения появятся при активности пользователей
            </div>
          </div>
        ) : (
          <div className="admin-event-feed">
            {events.map((ev) => (
              <FeedItem key={ev._id} ev={ev} />
            ))}
          </div>
        )}
      </div>
    </div>
  )
}

// Строка Live-ленты: «кто → кому» + содержимое (текст или медиа с миниатюрой).
// Старые события без обогащённых полей падают обратно на user:/chat:-идентификаторы.
function FeedItem({ ev }: { ev: FeedEvent }) {
  const meta = EVENT_LABELS[ev.event] || { label: ev.event, cls: 'system' }
  const d = ev.data
  const str = (v: unknown): string | null => (typeof v === 'string' && v ? v : null)

  const owner = str(d.ownerName)
  const sender = str(d.senderName)
  const chat = str(d.chatTitle)
  const mt = str(d.messageType)
  const text = str(d.text)
  const fuid = str(d.fileUniqueId)
  const mime = str(d.mimeType) || ''

  // Владелец пишет сам (isOutgoing) или сам правит/удаляет своё — стрелка от него к чату
  const ownerIsAuthor = d.isOutgoing === true || (sender !== null && sender === owner)
  const direction = owner
    ? ownerIsAuthor
      ? { from: owner, to: chat ?? 'собеседник' }
      : { from: sender ?? chat ?? 'собеседник', to: owner }
    : null

  const isImg = !!fuid && (mt === 'photo' || mt === 'sticker' || mime.startsWith('image/'))
  const mediaLabel = mt && mt !== 'text' ? `${MSG_TYPE_ICON[mt] || '📎'} ${MSG_TYPE_LABEL[mt] || mt}` : null

  return (
    <div className={`admin-event-item ${meta.cls}`}>
      <span className="admin-event-dot" />
      <div style={{ flex: 1, minWidth: 0 }}>
        <div className="admin-event-head">
          <span style={{ fontWeight: 500 }}>{meta.label}</span>
          {direction ? (
            <span className="text2">
              <span className="semibold">{direction.from}</span>
              {' → '}
              <span className="semibold">{direction.to}</span>
            </span>
          ) : (
            <span className="text3">
              {typeof d.telegramUserId !== 'undefined' && `user:${d.telegramUserId}`}
              {typeof d.chatId !== 'undefined' && ` chat:${d.chatId}`}
              {mt && ` (${mt})`}
            </span>
          )}
        </div>
        {(text || mediaLabel) && (
          <div className="admin-event-body">
            {isImg && fuid && (
              <img
                className="admin-event-thumb"
                src={mediaUrl(fuid)}
                alt=""
                loading="lazy"
                onError={(e) => {
                  e.currentTarget.style.display = 'none'
                }}
              />
            )}
            {mediaLabel && <span className="text2 admin-event-media">{mediaLabel}</span>}
            {text && <span className="admin-event-text">«{text}»</span>}
          </div>
        )}
      </div>
      <span className="text3">{new Date(ev._receivedAt).toLocaleTimeString('ru-RU')}</span>
    </div>
  )
}

function StatCard({ label, value, color }: { label: string; value: number | undefined; color?: string }) {
  return (
    <div className="admin-stat-card">
      <div className="admin-stat-label">{label}</div>
      <div className="admin-stat-value" style={color ? { color } : undefined}>
        {value ?? '—'}
      </div>
    </div>
  )
}

function MiniBar({ label, pct, suffix }: { label: string; pct: number; suffix?: string }) {
  const safe = Math.min(100, Math.max(0, pct || 0))
  const color = safe > 85 ? 'var(--red)' : safe > 60 ? 'var(--yellow)' : undefined
  return (
    <div className="admin-mini-bar">
      <div className="admin-mini-bar-row">
        <span className="text2">{label}</span>
        <span>
          {safe.toFixed(0)}%{suffix && <span className="text2"> · {suffix}</span>}
        </span>
      </div>
      <div className="admin-progress-bar">
        <div className="admin-progress-fill" style={{ width: `${safe}%`, background: color }} />
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
