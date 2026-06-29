import { useEffect, useState, createContext, useContext, useCallback } from 'react'
import { HashRouter, Routes, Route, Navigate } from 'react-router-dom'
import { auth, getMe, loadToken } from './api'
import type { Me } from './types'
import { BottomNav } from './components/BottomNav'
import { Toast } from './components/Toast'
import { Home } from './pages/Home'
import { Contacts } from './pages/Contacts'
import { ContactDetail } from './pages/ContactDetail'
import { Subscription } from './pages/Subscription'
import { Activate } from './pages/Activate'
import { Referral } from './pages/Referral'

// ── Context ───────────────────────────────────────────────────────────────

interface AppCtx {
  me: Me | null
  refreshMe: () => Promise<void>
  showToast: (msg: string, type?: 'success' | 'error' | 'info') => void
}

const Ctx = createContext<AppCtx>({ me: null, refreshMe: async () => {}, showToast: () => {} })
export const useApp = () => useContext(Ctx)

// ── Toast state ───────────────────────────────────────────────────────────

export interface ToastItem { id: number; msg: string; type: string }

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
        const initData = tg?.initData || ''
        if (!initData) {
          setError('Мини-апп должен быть открыт из Telegram')
          setReady(true)
          return
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
          <Route path="/" element={<Home />} />
          <Route path="/contacts" element={<Contacts />} />
          <Route path="/contacts/:chatId" element={<ContactDetail />} />
          <Route path="/subscription" element={<Subscription />} />
          <Route path="/activate" element={<Activate />} />
          <Route path="/referral" element={<Referral />} />
          <Route path="*" element={<Navigate to="/" replace />} />
        </Routes>
        <BottomNav />
        <Toast toasts={toasts} />
      </HashRouter>
    </Ctx.Provider>
  )
}
