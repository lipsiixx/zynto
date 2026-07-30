export interface TariffOut {
  id: number
  name: string
  description: string | null
  /** null = lifetime. */
  duration_days: number | null
  price_stars: number
  /** Старая цена — задана, только если на тарифе активна акция. */
  original_price_stars: number | null
  /** Процент скидки (например 30 = "-30%") — задан, только если акция активна. */
  discount_percent: number | null
  sort_order: number
  is_active: boolean
}

export interface TariffListResponse {
  items: TariffOut[]
}

export interface TariffPayload {
  name: string
  description?: string | null
  duration_days?: number | null
  price_stars: number
  sort_order: number
}

export type TariffPatchPayload = Partial<TariffPayload>
