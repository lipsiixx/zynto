export interface Tariff {
  id: number
  name: string
  description: string | null
  duration_days: number | null
  price_stars: number
}
