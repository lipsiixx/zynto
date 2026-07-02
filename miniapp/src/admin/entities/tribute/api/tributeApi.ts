import { req } from '@/admin/shared/api/adminApi'
import type { TributeFetchResponse, TributeProduct, TributeProductsResponse } from '../model/types'

export function getTributeProducts(): Promise<TributeProductsResponse> {
  return req('GET', '/tribute')
}

/** 503 "tribute_key_missing" если TRIBUTE_API_KEY не настроен в .env. Не сохраняет — только читает список Tribute. */
export function fetchTributeProducts(): Promise<TributeFetchResponse> {
  return req('POST', '/tribute/fetch')
}

/** Сохраняет весь список целиком — фронт сам собирает финальный массив (добавление/правка/удаление). */
export function saveTributeProducts(products: TributeProduct[]): Promise<TributeProductsResponse> {
  return req('PUT', '/tribute/products', { products })
}
