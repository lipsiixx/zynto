import { reqLegacy } from '@/admin/shared/api/adminApi'
import type {
  AdminUser,
  ChatsListResponse,
  UserContactsResponse,
  UserStats,
  UsersListResponse,
} from '../model/types'

export function getUsers(params: {
  q?: string
  status?: string
  page?: number
  limit?: number
}): Promise<UsersListResponse> {
  const p = new URLSearchParams()
  if (params.q) p.set('q', params.q)
  if (params.status) p.set('status', params.status)
  p.set('page', String(params.page ?? 1))
  p.set('limit', String(params.limit ?? 25))
  return reqLegacy('GET', `/users?${p}`)
}

export function getUser(id: number): Promise<AdminUser> {
  return reqLegacy('GET', `/users/${id}`)
}

export function getUserChats(
  id: number,
  params: { q?: string; filter?: string; page?: number; limit?: number },
): Promise<ChatsListResponse> {
  const p = new URLSearchParams()
  if (params.q) p.set('q', params.q)
  if (params.filter) p.set('filter', params.filter)
  p.set('page', String(params.page ?? 1))
  p.set('limit', String(params.limit ?? 20))
  return reqLegacy('GET', `/users/${id}/chats?${p}`)
}

export function getUserContacts(
  id: number,
  params: { minWeight?: number; page?: number; limit?: number },
): Promise<UserContactsResponse> {
  const p = new URLSearchParams()
  p.set('min_weight', String(params.minWeight ?? 1))
  p.set('page', String(params.page ?? 1))
  p.set('limit', String(params.limit ?? 25))
  return reqLegacy('GET', `/users/${id}/contacts?${p}`)
}

/** userId здесь — users.id (внутренний), см. GET /stats/users/{user_id}. */
export function getUserStats(userId: number): Promise<UserStats> {
  return reqLegacy('GET', `/stats/users/${userId}`)
}
