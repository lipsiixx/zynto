export type {
  CpuStats,
  DiskStats,
  FeedEvent,
  GlobalUserStats,
  MemoryStats,
  ProxyInfo,
  ProxyState,
  ProxyStats,
  ServerStats,
  WsEvent,
  WsEventName,
} from './model/types'
export { getGlobalUserStats, getProxyStats, getServerStats } from './api/statsApi'
