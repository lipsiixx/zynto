import { req } from '@/shared/api'
import type { Tariff } from '../model/types'

export async function getTariffs(): Promise<{ data: Tariff[] }> {
  return req('GET', '/tariffs')
}

export async function buyTariff(tariffId: number): Promise<{ message: string }> {
  return req('POST', `/buy/${tariffId}`)
}
