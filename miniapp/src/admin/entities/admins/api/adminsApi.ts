import { req } from '@/admin/shared/api/adminApi'
import type { AdminListResponse, AdminOut } from '../model/types'

/** Только суперадмин (require_webapp_superadmin) — 404 на любой отказ прав. */
export function listAdmins(): Promise<AdminListResponse> {
  return req('GET', '/admins')
}

/** identifier — "@username" или telegram_id строкой/числом. 404 "user_not_found" если юзер не запускал бота. */
export function addAdmin(identifier: string): Promise<AdminOut> {
  return req('POST', '/admins', { identifier })
}

export function removeAdmin(telegramId: number): Promise<{ ok: true }> {
  return req('DELETE', `/admins/${telegramId}`)
}
