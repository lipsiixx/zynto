import { req, reqLegacy } from '@/admin/shared/api/adminApi'
import type { DailyStatItem, GlobalUserStats, ProxyStats, ServerStats, UserDailyStatItem } from '../model/types'

export async function getServerStats(): Promise<ServerStats> {
  return reqLegacy('GET', '/stats/server')
}

export async function getProxyStats(): Promise<ProxyStats> {
  return reqLegacy('GET', '/stats/proxy')
}

export async function getGlobalUserStats(): Promise<GlobalUserStats> {
  return reqLegacy('GET', '/stats/users')
}

export async function getDailyStats(days: number): Promise<{ items: DailyStatItem[] }> {
  return req('GET', `/stats/daily?days=${days}`)
}

export async function getUserDailyStats(tid: number, days: number): Promise<{ items: UserDailyStatItem[] }> {
  return req('GET', `/users/${tid}/stats/daily?days=${days}`)
}
