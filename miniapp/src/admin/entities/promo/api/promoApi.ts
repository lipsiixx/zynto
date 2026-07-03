import { req } from '@/admin/shared/api/adminApi'
import type { CreatePromoPayload, PromoFilter, PromoListResponse, PromoOut } from '../model/types'

export function listPromo(filter: PromoFilter = 'all'): Promise<PromoListResponse> {
  return req('GET', `/promo?filter=${filter}`)
}

export function createPromo(payload: CreatePromoPayload): Promise<PromoOut> {
  return req('POST', '/promo', payload)
}

export function deletePromo(id: number): Promise<{ ok: boolean }> {
  return req('DELETE', `/promo/${id}`)
}
