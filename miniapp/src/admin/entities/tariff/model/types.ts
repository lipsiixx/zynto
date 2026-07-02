export interface TariffOut {
  id: number
  name: string
  description: string | null
  /** null = lifetime. */
  duration_days: number | null
  price_stars: number
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
