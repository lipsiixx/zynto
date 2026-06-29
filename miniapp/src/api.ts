import type { Contact, DayStat, Me, MessageEvent, MutualRating, ReferralStats, Tariff } from './types'

const BASE = '/v1/webapp'

let _token: string | null = null

export function setToken(t: string) {
  _token = t
  localStorage.setItem('zynto_token', t)
}

export function loadToken(): string | null {
  _token = localStorage.getItem('zynto_token')
  return _token
}

async function req<T>(
  method: string,
  path: string,
  body?: unknown,
): Promise<T> {
  const headers: Record<string, string> = { 'Content-Type': 'application/json' }
  if (_token) headers['Authorization'] = `Bearer ${_token}`

  const res = await fetch(`${BASE}${path}`, {
    method,
    headers,
    body: body !== undefined ? JSON.stringify(body) : undefined,
  })

  if (res.status === 401) {
    _token = null
    localStorage.removeItem('zynto_token')
    throw new Error('unauthorized')
  }

  if (!res.ok) {
    const err = await res.json().catch(() => ({}))
    throw new Error((err as { detail?: string }).detail || `HTTP ${res.status}`)
  }

  return res.json() as Promise<T>
}

export async function auth(initData: string): Promise<{ token: string; user: object }> {
  const data = await req<{ token: string; expiresAt: string; user: object }>('POST', '/auth', { initData })
  setToken(data.token)
  return data
}

export async function getMe(): Promise<Me> {
  return req('GET', '/me')
}

export async function getContacts(params?: {
  q?: string
  page?: number
}): Promise<{ data: Contact[]; total: number }> {
  const p = new URLSearchParams()
  if (params?.q) p.set('q', params.q)
  if (params?.page) p.set('page', String(params.page))
  return req('GET', `/contacts?${p}`)
}

export async function getContactEvents(
  chatId: number,
  params?: { flt?: string; page?: number },
): Promise<{ data: MessageEvent[]; total: number; page: number }> {
  const p = new URLSearchParams()
  if (params?.flt) p.set('flt', params.flt)
  if (params?.page) p.set('page', String(params.page))
  return req('GET', `/contacts/${chatId}/events?${p}`)
}

export async function getContactStats(chatId: number): Promise<{ data: DayStat[] }> {
  return req('GET', `/contacts/${chatId}/stats`)
}

export async function setTrust(chatId: number, score: number | null): Promise<void> {
  await req('PUT', `/trust/${chatId}`, { score })
}

export async function getTariffs(): Promise<{ data: Tariff[] }> {
  return req('GET', '/tariffs')
}

export async function buyTariff(tariffId: number): Promise<{ message: string }> {
  return req('POST', `/buy/${tariffId}`)
}

export async function activateCode(code: string): Promise<{ type: string; message: string }> {
  return req('POST', '/activate', { code })
}

export function getMediaUrl(fileUniqueId: string): string {
  const token = _token || localStorage.getItem('zynto_token') || ''
  return `/v1/webapp/media/${encodeURIComponent(fileUniqueId)}?token=${encodeURIComponent(token)}`
}

// ── Mutual Rating ──────────────────────────────────────────────────────────

export async function getMutualRating(chatId: number): Promise<MutualRating> {
  return req('GET', `/contacts/${chatId}/mutual-rating`)
}

export async function getMRPending(): Promise<{ data: MutualRating[]; total: number }> {
  return req('GET', '/mutual-rating/pending')
}

export async function sendMRRequest(chatId: number, myScore: number): Promise<MutualRating> {
  return req('POST', `/contacts/${chatId}/mutual-rating`, { my_score: myScore })
}

export async function acceptMR(chatId: number, score: number): Promise<MutualRating> {
  return req('POST', `/contacts/${chatId}/mutual-rating/accept`, { score })
}

export async function declineMR(chatId: number): Promise<MutualRating> {
  return req('POST', `/contacts/${chatId}/mutual-rating/decline`)
}

export async function cancelMR(chatId: number): Promise<MutualRating> {
  return req('DELETE', `/contacts/${chatId}/mutual-rating`)
}

export async function getReferral(): Promise<ReferralStats> {
  return req('GET', '/referral')
}

export function getInstructionPhotoUrl(): string {
  const token = _token || localStorage.getItem('zynto_token') || ''
  return `/v1/webapp/instruction-photo?token=${encodeURIComponent(token)}`
}
