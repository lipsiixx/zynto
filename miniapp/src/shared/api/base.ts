const BASE = '/v1/webapp'

let _token: string | null = null

export function setToken(t: string) {
  _token = t
  localStorage.setItem('zynto_token', t)
}

export function loadToken(): string | null {
  _token = localStorage.getItem('zynto_token')
  return _token
}

export function getToken(): string | null {
  return _token || localStorage.getItem('zynto_token')
}

export async function req<T>(
  method: string,
  path: string,
  body?: unknown,
): Promise<T> {
  const headers: Record<string, string> = { 'Content-Type': 'application/json' }
  if (_token) headers['Authorization'] = `Bearer ${_token}`

  const res = await fetch(`${BASE}${path}`, {
    method,
    headers,
    body: body !== undefined ? JSON.stringify(body) : undefined,
  })

  if (res.status === 401) {
    _token = null
    localStorage.removeItem('zynto_token')
    throw new Error('unauthorized')
  }

  if (!res.ok) {
    const err = await res.json().catch(() => ({}))
    throw new Error((err as { detail?: string }).detail || `HTTP ${res.status}`)
  }

  return res.json() as Promise<T>
}
