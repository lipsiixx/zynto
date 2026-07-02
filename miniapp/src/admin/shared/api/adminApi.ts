// HTTP-клиент админ-модуля. Тот же токен (Telegram-identity admin JWT), что
// хранится в localStorage['zynto_token'] основного приложения — сюда он
// приходит через ctx.token, переданный в mount(). Конвенции по обработке
// ошибок/заголовков — как в shared/api/base.ts, продублировано намеренно:
// админ-бандл собирается отдельным Vite-конфигом (vite.admin.config.ts) и не
// должен тянуть код основного приложения.

// Новые эндпоинты панели (Phase 2+), пока не существуют на бэкенде.
const BASE = '/v1/webapp/admin'

// Существующие 6 legacy-роутеров мониторинга (без префикса /webapp).
const LEGACY_BASE = '/v1'

// Основной webapp-роутер (не -admin) — нужен только для GET /me (флаги
// доступа, включая "superadmin"). Админ-бандл не может импортировать
// entities/user основного приложения (раздельные сборки), поэтому здесь
// продублирован минимальный вызов.
const WEBAPP_BASE = '/v1/webapp'

let _token: string | null = null

export function setToken(t: string) {
  _token = t
}

/** Текущий токен — нужен там, где нельзя пройти через request() (например WS). */
export function getToken(): string | null {
  return _token
}

async function request<T>(base: string, method: string, path: string, body?: unknown): Promise<T> {
  const headers: Record<string, string> = { 'Content-Type': 'application/json' }
  if (_token) headers['Authorization'] = `Bearer ${_token}`

  const res = await fetch(`${base}${path}`, {
    method,
    headers,
    body: body !== undefined ? JSON.stringify(body) : undefined,
  })

  if (res.status === 401) {
    throw new Error('unauthorized')
  }

  if (!res.ok) {
    const err = await res.json().catch(() => ({}))
    throw new Error((err as { detail?: string }).detail || `HTTP ${res.status}`)
  }

  return res.json() as Promise<T>
}

/** /v1/webapp/admin/* — Phase 2+, ещё не существует на бэкенде, только заготовка. */
export function req<T>(method: string, path: string, body?: unknown): Promise<T> {
  return request<T>(BASE, method, path, body)
}

/** /v1/{users,chats,stats,graph,media,cache} — существующие роутеры мониторинга. */
export function reqLegacy<T>(method: string, path: string, body?: unknown): Promise<T> {
  return request<T>(LEGACY_BASE, method, path, body)
}

/**
 * multipart/form-data-версия req() — для эндпоинтов рассылки/nudge/курса,
 * принимающих файлы. НЕ ставим Content-Type вручную: браузер сам подставит
 * "multipart/form-data; boundary=..." при body: FormData, ручной заголовок
 * без boundary сломает парсинг на бэкенде.
 */
export async function reqForm<T>(method: string, path: string, form: FormData): Promise<T> {
  const headers: Record<string, string> = {}
  if (_token) headers['Authorization'] = `Bearer ${_token}`

  const res = await fetch(`${BASE}${path}`, { method, headers, body: form })

  if (res.status === 401) {
    throw new Error('unauthorized')
  }

  if (!res.ok) {
    const err = await res.json().catch(() => ({}))
    throw new Error((err as { detail?: string }).detail || `HTTP ${res.status}`)
  }

  return res.json() as Promise<T>
}

/**
 * GET /v1/webapp/me с тем же токеном — единственный способ узнать флаги
 * доступа (в частности "superadmin") внутри админ-бандла: mount() передаёт
 * только token (см. src/app/App.tsx maybeLoadExtraModule), без флагов.
 */
export function fetchMe(): Promise<{ flags?: string[] }> {
  return request(WEBAPP_BASE, 'GET', '/me')
}

/**
 * URL для WebSocket-подключения к api/ws.py (GET /v1/ws?token=...). Не идёт
 * через request()/reqLegacy() — это отдельный протокол, вызывающий код сам
 * создаёт `new WebSocket(wsUrl(token))`. Схема (ws/wss) и хост берутся из
 * текущего origin — тот же паттерн, что api.wsUrl() в старом admin-panel
 * (src/api.js), но здесь без localStorage: токен приходит из ctx.token.
 */
export function wsUrl(token: string): string {
  const proto = window.location.protocol === 'https:' ? 'wss:' : 'ws:'
  return `${proto}//${window.location.host}${LEGACY_BASE}/ws?token=${encodeURIComponent(token)}`
}

/**
 * Прямая ссылка на GET /v1/media/:fileUniqueId для <img>/<video>/<audio> src —
 * тег не может выставить заголовок Authorization, поэтому токен передаётся
 * через ?token= (require_admin_any в api/deps.py принимает оба варианта).
 * Порт api.mediaUrl() из C:\projects\admin-panel\src\api.js.
 */
export function mediaUrl(fileUniqueId: string): string {
  return `${LEGACY_BASE}/media/${fileUniqueId}?token=${_token ? encodeURIComponent(_token) : ''}`
}
