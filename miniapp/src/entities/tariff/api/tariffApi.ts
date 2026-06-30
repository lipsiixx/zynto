import { req } from '@/shared/api'
import type { Tariff } from '../model/types'

export interface TributeProduct {
  tribute_product_id: number
  name: string
  price: number
  currency: string
  web_link: string
  duration_days: number
}

export async function getTariffs(): Promise<{ data: Tariff[] }> {
  return req('GET', '/tariffs')
}

export async function buyTariff(tariffId: number): Promise<{ message: string }> {
  return req('POST', `/buy/${tariffId}`)
}

export async function getTributeProducts(): Promise<TributeProduct[]> {
  return req('GET', '/tribute-products')
}
