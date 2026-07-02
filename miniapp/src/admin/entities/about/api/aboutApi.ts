import { req } from '@/admin/shared/api/adminApi'
import type { AboutOut, AboutPayload } from '../model/types'

export function getAbout(): Promise<AboutOut> {
  return req('GET', '/about')
}

export function updateAbout(payload: AboutPayload): Promise<AboutOut> {
  return req('PUT', '/about', payload)
}
