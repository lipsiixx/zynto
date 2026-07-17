import { createContext, useContext } from 'react'

export type ToastType = 'success' | 'error' | 'info'
export type ToastFn = (msg: string, type?: ToastType) => void

interface AdminCtxValue {
  /** Флаг "superadmin" из GET /v1/webapp/me — скрывает AdminsPage и вкладку «Автоочистка». */
  isSuperadmin: boolean
  /** true — вход через /admin (?admin_entry=full): полный доступ ко всем разделам.
   *  false — вход через Start/меню: скрыты «Пользователи» и Live-события дашборда. */
  fullAccess: boolean
  showToast: ToastFn
}

// Контекст один на всё дерево AdminApp — избавляет от прокидывания
// isSuperadmin/fullAccess/showToast через пропсы во все страницы/вкладки Settings.
export const AdminCtx = createContext<AdminCtxValue>({
  isSuperadmin: false,
  fullAccess: false,
  showToast: () => {},
})

export function useAdminCtx(): AdminCtxValue {
  return useContext(AdminCtx)
}
