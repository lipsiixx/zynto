import { useEffect, useRef, useState } from 'react'
import { getToken, wsUrl } from '@/admin/shared/api/adminApi'
import type { WsEvent } from '@/admin/entities/stats'

/**
 * Подписка на GET /v1/ws — реалтайм-события бота (message.new/updated/deleted,
 * stats.refresh, cache.invalidated). Автопереподключение через 3с после
 * закрытия сокета — порт поведения Dashboard.jsx из старого admin-panel.
 */
export function useAdminWs(onEvent: (ev: WsEvent) => void): boolean {
  const [connected, setConnected] = useState(false)
  const onEventRef = useRef(onEvent)
  onEventRef.current = onEvent

  useEffect(() => {
    const token = getToken()
    if (!token) return

    let ws: WebSocket | null = null
    let reconnectTimer: ReturnType<typeof setTimeout> | null = null
    let cancelled = false

    const connect = () => {
      if (cancelled) return
      try {
        ws = new WebSocket(wsUrl(token))
      } catch {
        reconnectTimer = setTimeout(connect, 3000)
        return
      }

      ws.onopen = () => {
        if (!cancelled) setConnected(true)
      }
      ws.onmessage = (e) => {
        try {
          const ev = JSON.parse(e.data) as WsEvent
          onEventRef.current(ev)
        } catch {
          // игнорируем не-JSON пакеты (keepalive и т.п.)
        }
      }
      ws.onclose = () => {
        if (cancelled) return
        setConnected(false)
        reconnectTimer = setTimeout(connect, 3000)
      }
      ws.onerror = () => {
        ws?.close()
      }
    }

    connect()

    return () => {
      cancelled = true
      if (reconnectTimer) clearTimeout(reconnectTimer)
      ws?.close()
    }
  }, [])

  return connected
}
