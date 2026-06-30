import { createContext, useContext } from 'react'
import type { Me } from '@/entities/user'

export interface AppCtx {
  me: Me | null
  refreshMe: () => Promise<void>
  showToast: (msg: string, type?: 'success' | 'error' | 'info') => void
}

export const Ctx = createContext<AppCtx>({ me: null, refreshMe: async () => {}, showToast: () => {} })
export const useApp = () => useContext(Ctx)

export type { ToastItem } from '@/shared/ui'
