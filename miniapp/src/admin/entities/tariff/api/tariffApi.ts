import { req } from '@/admin/shared/api/adminApi'
import type { TariffListResponse, TariffOut, TariffPatchPayload, TariffPayload } from '../model/types'

export function listTariffs(): Promise<TariffListResponse> {
  return req('GET', '/tariffs')
}

export function createTariff(payload: TariffPayload): Promise<TariffOut> {
  return req('POST', '/tariffs', payload)
}

export function updateTariff(id: number, payload: TariffPatchPayload): Promise<TariffOut> {
  return req('PATCH', `/tariffs/${id}`, payload)
}

export function toggleTariff(id: number): Promise<TariffOut> {
  return req('POST', `/tariffs/${id}/toggle`)
}

/** 409 "has_subscriptions" — тариф уже выдан хотя бы одному пользователю, удалить нельзя. */
export function deleteTariff(id: number): Promise<{ ok: true }> {
  return req('DELETE', `/tariffs/${id}`)
}

/** 404 — тариф не найден, 422 — цена невалидна или не ниже текущей. */
export function startTariffSale(id: number, newPriceStars: number): Promise<TariffOut> {
  return req('POST', `/tariffs/${id}/sale`, { new_price_stars: newPriceStars })
}

/** 404 — тариф не найден, 409 — на тарифе нет активной акции. */
export function endTariffSale(id: number): Promise<TariffOut> {
  return req('POST', `/tariffs/${id}/sale/end`)
}
