import { req } from '@/shared/api'
import type { NetworkGraph, NetworkStatus } from '../model/types'

export async function getNetworkStatus(): Promise<NetworkStatus> {
  return req('GET', '/network/status')
}

export async function joinNetwork(visible: boolean): Promise<NetworkStatus> {
  return req('POST', '/network/join', { visible })
}

export async function updateNetworkSettings(visible: boolean): Promise<{ visible: boolean }> {
  return req('PUT', '/network/settings', { visible })
}

export async function getNetworkGraph(): Promise<NetworkGraph> {
  return req('GET', '/network/graph')
}
