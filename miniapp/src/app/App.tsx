import { useEffect, useState, useCallback } from 'react'
import { HashRouter, Routes, Route, Navigate } from 'react-router-dom'
import { auth, getMe } from '@/entities/user'
import type { Me } from '@/entities/user'
import { loadToken } from '@/shared/api'
import { BottomNav } from '@/widgets/bottom-nav'
import { Toast } from '@/shared/ui'
import type { ToastItem } from '@/shared/ui'
import { HomePage } from '@/pages/home'
import { ContactsPage } from '@/pages/contacts'
import { ContactDetailPage } from '@/pages/contact-detail'
import { SubscriptionPage } from '@/pages/subscription'
import { ActivatePage } from '@/pages/activate'
import { ReferralPage } from '@/pages/referral'
import { NetworkPage } from '@/pages/network'
import { Ctx } from './AppContext'

// ── App ───────────────────────────────────────────────────────────────────

export default function App() {
  const [me, setMe] = useState<Me | null>(null)
  const [ready, setReady] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [toasts, setToasts] = useState<ToastItem[]>([])

  const showToast = useCallback((msg: string, type: 'success' | 'error' | 'info' = 'info') => {
    const id = Date.now()
    setToasts(t => [...t, { id, msg, type }])
    setTimeout(() => setToasts(t => t.filter(x => x.id !== id)), 3000)
  }, [])

  const refreshMe = useCallback(async () => {
    try {
      const data = await getMe()
      setMe(data)
    } catch {
      // ignore
    }
  }, [])

  useEffect(() => {
    const tg = window.Telegram?.WebApp
    if (tg) {
      tg.ready()
      tg.expand()

      const applyInsets = () => {
        const sa = tg.safeAreaInset
        const csa = tg.contentSafeAreaInset
        const top = (sa?.top ?? 0) + (csa?.top ?? 0)
        const bottom = (sa?.bottom ?? 0) + (csa?.bottom ?? 0)
        const root = document.documentElement
        // только если Telegram вернул реальные значения (>0), иначе CSS env() справится сам
        if (top > 0) root.style.setProperty('--tg-inset-top', top + 'px')
        if (bottom > 0) root.style.setProperty('--tg-inset-bottom', bottom + 'px')
      }

      applyInsets()
      tg.onEvent('safeAreaChanged', applyInsets)
      tg.onEvent('contentSafeAreaChanged', applyInsets)
    }

    async function init() {
      try {
        // Try cached token first
        const cached = loadToken()
        if (cached) {
          try {
            const data = await getMe()
            setMe(data)
            setReady(true)
            return
          } catch (e) {
            if ((e as Error).message !== 'unauthorized') {
              throw e
            }
            // Token expired, re-auth
          }
        }

        // Auth with initData
        let initData = tg?.initData || ''
        if (!initData) {
          const devId = import.meta.env.VITE_DEV_USER_ID
          if (import.meta.env.DEV && devId) {
            initData = JSON.stringify({ id: Number(devId) })
          } else {
            setError('Мини-апп должен быть открыт из Telegram')
            setReady(true)
            return
          }
        }

        await auth(initData)
        const data = await getMe()
        setMe(data)
      } catch (e) {
        setError((e as Error).message || 'Ошибка инициализации')
      } finally {
        setReady(true)
      }
    }

    init()
  }, [])

  if (!ready) {
    return (
      <div className="loading-center" style={{ height: '100vh' }}>
        <div className="spinner" />
      </div>
    )
  }

  if (error) {
    return (
      <div style={{ padding: 24, textAlign: 'center', paddingTop: 80 }}>
        <div style={{ fontSize: 40, marginBottom: 16 }}>⚠️</div>
        <div style={{ color: 'var(--red)', marginBottom: 8, fontWeight: 600 }}>Ошибка</div>
        <div style={{ color: 'var(--text2)', fontSize: 14 }}>{error}</div>
      </div>
    )
  }

  return (
    <Ctx.Provider value={{ me, refreshMe, showToast }}>
      <HashRouter>
        <Routes>
          <Route path="/" element={<HomePage />} />
          <Route path="/contacts" element={<ContactsPage />} />
          <Route path="/contacts/:chatId" element={<ContactDetailPage />} />
          <Route path="/subscription" element={<SubscriptionPage />} />
          <Route path="/activate" element={<ActivatePage />} />
          <Route path="/referral" element={<ReferralPage />} />
          <Route path="/network" element={<NetworkPage />} />
          <Route path="*" element={<Navigate to="/" replace />} />
        </Routes>
        <BottomNav />
        <Toast toasts={toasts} />
      </HashRouter>
    </Ctx.Provider>
  )
}
