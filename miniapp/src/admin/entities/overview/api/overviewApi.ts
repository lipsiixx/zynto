import { req } from '@/admin/shared/api/adminApi'
import type { OverviewOut } from '../model/types'

export function getOverview(): Promise<OverviewOut> {
  return req('GET', '/overview')
}
