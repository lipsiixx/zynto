import { req } from '@/admin/shared/api/adminApi'
import type { UserProfileOut, UserSubscriptionsResponse } from '../model/types'

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
