import { req } from '@/admin/shared/api/adminApi'
import type { CleanupOut, CleanupPayload } from '../model/types'

/** Только суперадмин (require_webapp_superadmin) — 404 на любой отказ прав. */
export function getCleanup(): Promise<CleanupOut> {
  return req('GET', '/cleanup')
}

export function updateCleanup(payload: CleanupPayload): Promise<CleanupOut> {
  return req('PUT', '/cleanup', payload)
}
