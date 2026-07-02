/** Продукт, уже сохранённый в bot_settings.tribute_sbp_products. */
export interface TributeProduct {
  tribute_product_id: string | number
  name: string
  price: number | null
  currency: string | null
  web_link: string
  /** null/0 = навсегда (см. handlers/admin/tribute_settings.py: 0 → "навсегда"). */
  duration_days: number | null
}

export interface TributeProductsResponse {
  products: TributeProduct[]
}

/** Сырой ответ https://tribute.tg/api/v1/products (до выбора срока подписки). */
export interface TributeFetchedProduct {
  id: string | number
  name: string
  amount: number
  currency: string
  webLink: string
}

export interface TributeFetchResponse {
  products: TributeFetchedProduct[]
}
