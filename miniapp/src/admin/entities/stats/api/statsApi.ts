import { reqLegacy } from '@/admin/shared/api/adminApi'
import type { GlobalUserStats, ProxyStats, ServerStats } from '../model/types'

export async function getServerStats(): Promise<ServerStats> {
  return reqLegacy('GET', '/stats/server')
}

export async function getProxyStats(): Promise<ProxyStats> {
  return reqLegacy('GET', '/stats/proxy')
}

export async function getGlobalUserStats(): Promise<GlobalUserStats> {
  return reqLegacy('GET', '/stats/users')
}
