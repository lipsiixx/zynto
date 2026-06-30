import { req, setToken } from '@/shared/api'
import type { Me } from '../model/types'

export async function auth(initData: string): Promise<{ token: string; user: object }> {
  const data = await req<{ token: string; expiresAt: string; user: object }>('POST', '/auth', { initData })
  setToken(data.token)
  return data
}

export async function getMe(): Promise<Me> {
  return req('GET', '/me')
}

export async function activateCode(code: string): Promise<{ type: string; message: string }> {
  return req('POST', '/activate', { code })
}
