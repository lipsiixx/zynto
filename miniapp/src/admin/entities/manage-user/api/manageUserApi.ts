import { req } from '@/admin/shared/api/adminApi'
import type {
  ManagedUsersListResponse,
  SubscriptionAction,
  UserProfileOut,
  UserStatsOut,
  UserSubscriptionsResponse,
} from '../model/types'

export function listManagedUsers(params: { q?: string; status?: string; page?: number; limit?: number }): Promise<ManagedUsersListResponse> {
  const sp = new URLSearchParams()
  if (params.q) sp.set('q', params.q)
  if (params.status) sp.set('status', params.status)
  if (params.page) sp.set('page', String(params.page))
  if (params.limit) sp.set('limit', String(params.limit))
  const qs = sp.toString()
  return req('GET', `/users${qs ? `?${qs}` : ''}`)
}

/** q — @username или telegram_id, как в _find_user (handlers/admin/users_mgmt.py). 404 "user_not_found". */
export function findUser(q: string): Promise<UserProfileOut> {
  return req('GET', `/users/find?q=${encodeURIComponent(q)}`)
}

export function banUser(telegramId: number, reason: string): Promise<UserProfileOut> {
  return req('POST', `/users/${telegramId}/ban`, { reason })
}

export function unbanUser(telegramId: number): Promise<UserProfileOut> {
  return req('POST', `/users/${telegramId}/unban`)
}

export function grantTariff(telegramId: number, tariffId: number): Promise<UserProfileOut> {
  return req('POST', `/users/${telegramId}/grant`, { tariff_id: tariffId })
}

export function getUserSubscriptions(telegramId: number): Promise<UserSubscriptionsResponse> {
  return req('GET', `/users/${telegramId}/subscriptions`)
}

export function getUserStats(telegramId: number): Promise<UserStatsOut> {
  return req('GET', `/users/${telegramId}/stats`)
}

/** action=days требует days (1–3650); lifetime/revoke — без параметров */
export function setSubscription(telegramId: number, action: SubscriptionAction, days?: number): Promise<UserProfileOut> {
  return req('POST', `/users/${telegramId}/subscription`, { action, days: days ?? null })
}
