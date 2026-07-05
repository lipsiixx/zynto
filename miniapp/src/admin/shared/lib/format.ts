// Мелкие форматтеры, общие для Dashboard/Stats — порт utils.js из admin-panel.

export function formatBytes(n: number): string {
  if (!n || n <= 0) return '0 Б'
  const units = ['Б', 'КБ', 'МБ', 'ГБ', 'ТБ']
  const i = Math.min(units.length - 1, Math.floor(Math.log(n) / Math.log(1024)))
  const val = n / 1024 ** i
  return `${val.toFixed(i === 0 ? 0 : 1)} ${units[i]}`
}

export function formatUptime(sec: number): string {
  const d = Math.floor(sec / 86400)
  const h = Math.floor((sec % 86400) / 3600)
  const m = Math.floor((sec % 3600) / 60)
  if (d) return `${d}д ${h}ч`
  if (h) return `${h}ч ${m}м`
  return `${m}м`
}

export function formatRelTime(ms: number): string {
  const sec = Math.max(0, Math.floor(ms / 1000))
  if (sec < 60) return `${sec} сек`
  const min = Math.floor(sec / 60)
  if (min < 60) return `${min} мин`
  const hrs = Math.floor(min / 60)
  if (hrs < 24) return `${hrs} ч`
  return `${Math.floor(hrs / 24)} дн`
}

export function pctColor(pct: number): string {
  if (pct > 85) return 'var(--red)'
  if (pct > 60) return 'var(--yellow)'
  return 'var(--green)'
}

export function proxyStateLabel(state: string): string {
  const map: Record<string, string> = {
    ok: 'Активен',
    degraded: 'Деградация',
    down: 'Недоступен',
    no_proxy: 'Нет прокси',
  }
  return map[state] || state
}

// ── Users / UserDetail / ChatMessages (Phase 1B) ────────────────────────────
// Отдельный набор хелперов — работают с ISO-датами (а не с "elapsed ms", как
// formatRelTime выше) и байтами файлов. Порт utils.js из admin-panel
// (relTime/fmtDate/fmtDateTime/bytes/initials/MSG_TYPE_ICON), имена не
// пересекаются с formatBytes/formatRelTime выше.

type DateInput = string | number | Date | null | undefined

function toDate(d: string | number | Date): Date {
  return typeof d === 'string' || typeof d === 'number' ? new Date(d) : d
}

export function relTime(d: DateInput): string {
  if (!d) return '—'
  const ms = toDate(d).getTime()
  const diff = (Date.now() - ms) / 1000
  if (diff < 60) return 'только что'
  if (diff < 3600) return `${Math.floor(diff / 60)} мин`
  if (diff < 86400) return `${Math.floor(diff / 3600)} ч`
  if (diff < 604800) return `${Math.floor(diff / 86400)} д`
  return fmtDate(d)
}

export function fmtDate(d: DateInput): string {
  if (!d) return '—'
  return toDate(d).toLocaleDateString('ru-RU', { day: '2-digit', month: 'short', year: 'numeric' })
}

export function fmtDateTime(d: DateInput): string {
  if (!d) return '—'
  return toDate(d).toLocaleString('ru-RU', { day: '2-digit', month: 'short', hour: '2-digit', minute: '2-digit' })
}

export function fmtTime(d: DateInput): string {
  if (!d) return ''
  return toDate(d).toLocaleTimeString('ru-RU', { hour: '2-digit', minute: '2-digit' })
}

export function bytes(n: number | null | undefined): string {
  if (!n) return '0 Б'
  const units = ['Б', 'КБ', 'МБ', 'ГБ', 'ТБ']
  let i = 0
  let v = n
  while (v >= 1024 && i < units.length - 1) {
    v /= 1024
    i++
  }
  return `${v.toFixed(i ? 1 : 0)} ${units[i]}`
}

export function initials(name: string | null | undefined): string {
  if (!name) return '?'
  return name
    .trim()
    .split(/\s+/)
    .slice(0, 2)
    .map(w => w[0]?.toUpperCase() ?? '')
    .join('')
}

export const MSG_TYPE_LABEL: Record<string, string> = {
  text: 'текст',
  photo: 'фото',
  video: 'видео',
  audio: 'аудио',
  voice: 'голосовое',
  document: 'документ',
  sticker: 'стикер',
  animation: 'GIF',
  video_note: 'кружок',
  contact: 'контакт',
  location: 'локация',
  poll: 'опрос',
}

export const MSG_TYPE_ICON: Record<string, string> = {
  text: '💬',
  photo: '🖼',
  video: '🎬',
  audio: '🎵',
  voice: '🎙',
  document: '📄',
  sticker: '🎭',
  animation: '🎞',
  video_note: '🎥',
  contact: '👤',
  location: '📍',
  poll: '📊',
}
