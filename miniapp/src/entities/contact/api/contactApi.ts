import { req } from '@/shared/api'
import type { MessageEvent } from '@/entities/message'
import type { Contact, DayStat } from '../model/types'

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
