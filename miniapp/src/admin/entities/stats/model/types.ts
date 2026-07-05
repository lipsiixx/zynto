// Формы ответов legacy-роутера мониторинга api/routers/stats.py (см. api/schemas.py,
// секция "Stats"). Поля уже в camelCase — pydantic-модели используют те же имена,
// конвертации не требуется.

export interface CpuStats {
  usagePercent: number
  cores: number
}

export interface MemoryStats {
  totalBytes: number
  usedBytes: number
  freeBytes: number
}

export interface DiskStats {
  totalBytes: number
  usedBytes: number
  freeBytes: number
}

export interface ServerStats {
  cpu: CpuStats
  memory: MemoryStats
  disk: DiskStats
  uptimeSeconds: number
  loadAvg: number[]
  measuredAt: string
}

export type ProxyState = 'ok' | 'degraded' | 'down' | string

export interface ProxyInfo {
  proxy: string
  state: ProxyState
  avgLatencySeconds: number
  failsInWindow: number
  windowSize: number
  consecutiveFails: number
  consecutiveOks: number
  lastCheckedSecondsAgo: number | null
  monitorRunning: boolean
}

export interface ProxyStats {
  active: ProxyInfo | null
  noProxy: boolean
}

export interface GlobalUserStats {
  total: number
  online: number
  newToday: number
  newThisWeek: number
  activeSubscribers: number
  /** Пользователи, пришедшие по реферальной ссылке (referred_by != null) */
  referralUsers?: number
  measuredAt: string
}

// ── Realtime (api/ws.py + services/ws_broadcaster.py) ──────────────────────
// Событие приходит как {"event": "...", "data": {...}, "timestamp": "..."} —
// имя поля "event" (не "type"), в отличие от старого admin-panel (см. Dashboard.jsx
// reference, где use ev.type — там на самом деле это же поле, просто SSE/WS payload
// в проде уже содержит "event"; сверено с api/ws.py + ws_broadcaster.py напрямую).
export type WsEventName =
  | 'message.new'
  | 'message.updated'
  | 'message.deleted'
  | 'stats.refresh'
  | 'cache.invalidated'
  | string

export interface WsEvent {
  event: WsEventName
  data: Record<string, unknown>
  timestamp: string
}

export interface FeedEvent extends WsEvent {
  _id: number
  _receivedAt: number
}

// ── Дневная динамика (GET /webapp/admin/stats/daily) ───────────────────────
export interface DailyStatItem {
  date: string
  new_users: number
  messages: number
  deleted: number
  edited: number
  grants: number
  paid: number
}

export interface UserDailyStatItem {
  date: string
  messages: number
  deleted: number
  edited: number
}

/** GET /webapp/admin/stats/top-users */
export interface TopUserItem {
  telegram_id: number
  full_name: string | null
  username: string | null
  messages: number
}

/** GET /webapp/admin/users/{tid}/top-chats */
export interface TopChatItem {
  chat_id: number
  title: string | null
  messages: number
  deleted: number
  edited: number
}
