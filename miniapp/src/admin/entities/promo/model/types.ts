// Форма ответов api/routers/webapp_admin.py (Phase 2, контракт см. задачу) —
// в отличие от entities/user (legacy /v1/users, camelCase), новый роутер
// /v1/webapp/admin/* отдаёт snake_case как остальной /v1/webapp/* (см.
// entities/user/model/types.ts основного приложения).

export type PromoCodeType = 'access' | 'discount'
export type PromoStatus = 'active' | 'exhausted' | 'expired'
export type PromoFilter = 'all' | 'active' | 'used'

export interface PromoOut {
  id: number
  code: string
  code_type: PromoCodeType
  duration_label: string | null
  duration_minutes: number | null
  discount_stars: number | null
  discount_tariff_id: number | null
  max_uses: number | null
  uses_count: number
  /** telegram_id использовавшего (legacy-поле, значимо только для max_uses === 1). */
  used_by: number | null
  code_expires_at: string | null
  note: string | null
  created_at: string
  status: PromoStatus
}

export interface PromoListResponse {
  items: PromoOut[]
}

export interface CreatePromoPayload {
  code_type: PromoCodeType
  minutes?: number | null
  label?: string
  discount_stars?: number
  discount_tariff_id?: number | null
  max_uses: number | null
  code_expires_at?: string | null
  note?: string | null
}

/** DURATION_MAP из handlers/admin/promo.py — минуты + человекочитаемый label. */
export const PROMO_DURATION_PRESETS: { value: string; minutes: number | null; label: string }[] = [
  { value: 'm1', minutes: 1, label: '1 минута' },
  { value: 'h1', minutes: 60, label: '1 час' },
  { value: 'd1', minutes: 1440, label: '1 день' },
  { value: 'd7', minutes: 10080, label: '7 дней' },
  { value: 'd30', minutes: 43200, label: '1 месяц' },
  { value: 'd90', minutes: 129600, label: '3 месяца' },
  { value: 'life', minutes: null, label: 'Навсегда' },
  { value: 'custom', minutes: 0, label: 'Свой срок (дни)' },
]

export const PROMO_MAX_USES_PRESETS: { value: string; maxUses: number | null; label: string }[] = [
  { value: '1', maxUses: 1, label: '1 раз' },
  { value: '5', maxUses: 5, label: '5 раз' },
  { value: '10', maxUses: 10, label: '10 раз' },
  { value: '0', maxUses: null, label: 'Без лимита' },
]
