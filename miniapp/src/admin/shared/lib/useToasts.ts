import { useCallback, useState } from 'react'
import type { AdminToastItem } from '@/admin/shared/ui/AdminToast'
import type { ToastFn, ToastType } from './AdminCtx'

// Тот же паттерн, что showToast в src/app/App.tsx — продублирован намеренно
// (см. комментарий в AdminToast.tsx про изоляцию бандлов).
export function useToasts(): { toasts: AdminToastItem[]; showToast: ToastFn } {
  const [toasts, setToasts] = useState<AdminToastItem[]>([])

  const showToast = useCallback((msg: string, type: ToastType = 'info') => {
    const id = Date.now() + Math.random()
    setToasts(t => [...t, { id, msg, type }])
    setTimeout(() => setToasts(t => t.filter(x => x.id !== id)), 3000)
  }, [])

  return { toasts, showToast }
}
