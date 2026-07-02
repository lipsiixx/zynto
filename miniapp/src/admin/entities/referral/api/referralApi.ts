import { req } from '@/admin/shared/api/adminApi'
import type { ReferralOut, ReferralPayload, ReferralSettingsOut } from '../model/types'

export function getReferral(page = 1, limit = 20): Promise<ReferralOut> {
  return req('GET', `/referral?page=${page}&limit=${limit}`)
}

/** Ответ — без rewards/total_rewards (только настройки). */
export function updateReferral(payload: ReferralPayload): Promise<ReferralSettingsOut> {
  return req('PUT', '/referral', payload)
}
