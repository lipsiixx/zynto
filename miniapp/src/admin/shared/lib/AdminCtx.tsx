import { createContext, useContext } from 'react'

export type ToastType = 'success' | 'error' | 'info'
export type ToastFn = (msg: string, type?: ToastType) => void

interface AdminCtxValue {
  /** Флаг "superadmin" из GET /v1/webapp/me — скрывает AdminsPage и вкладку «Автоочистка». */
  isSuperadmin: boolean
  showToast: ToastFn
}

// Контекст один на всё дерево AdminApp — избавляет от прокидывания
// isSuperadmin/showToast через пропсы во все страницы/вкладки Settings.
export const AdminCtx = createContext<AdminCtxValue>({
  isSuperadmin: false,
  showToast: () => {},
})

export function useAdminCtx(): AdminCtxValue {
  return useContext(AdminCtx)
}
