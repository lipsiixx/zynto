import { reqLegacy } from '@/admin/shared/api/adminApi'
import type { MediaListResponse, MessagesListResponse } from '../model/types'

export function getChatMessages(
  chatId: number,
  params: { userId: number; before?: number; limit?: number },
): Promise<MessagesListResponse> {
  const p = new URLSearchParams()
  p.set('user_id', String(params.userId))
  if (params.before) p.set('before', String(params.before))
  p.set('limit', String(params.limit ?? 50))
  return reqLegacy('GET', `/chats/${chatId}/messages?${p}`)
}

export function getChatMedia(
  chatId: number,
  params: { userId: number; mimeType?: string; page?: number; limit?: number },
): Promise<MediaListResponse> {
  const p = new URLSearchParams()
  p.set('user_id', String(params.userId))
  if (params.mimeType) p.set('mime_type', params.mimeType)
  p.set('page', String(params.page ?? 1))
  p.set('limit', String(params.limit ?? 30))
  return reqLegacy('GET', `/chats/${chatId}/media?${p}`)
}
