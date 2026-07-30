export interface Tariff {
  id: number
  name: string
  description: string | null
  duration_days: number | null
  price_stars: number
  /** Старая цена — задана, только если на тарифе активна акция. */
  original_price_stars: number | null
  /** Процент скидки (например 30 = "-30%") — задан, только если акция активна. */
  discount_percent: number | null
}
