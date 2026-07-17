import { useEffect, useState } from 'react'
import { HashRouter, Routes, Route, Navigate } from 'react-router-dom'
import { AdminNav } from '@/admin/widgets/admin-nav/AdminNav'
import { fetchMe, setToken } from '@/admin/shared/api/adminApi'
import { AdminCtx } from '@/admin/shared/lib/AdminCtx'
import { useToasts } from '@/admin/shared/lib/useToasts'
import { AdminToast } from '@/admin/shared/ui'
import { DashboardPage } from '@/admin/pages/dashboard/DashboardPage'
import { UsersPage } from '@/admin/pages/users/UsersPage'
import { UserDetailPage } from '@/admin/pages/users/UserDetailPage'
import { ChatMessagesPage } from '@/admin/pages/chat-messages/ChatMessagesPage'
import { StatsPage } from '@/admin/pages/stats/StatsPage'
import { UserStatsPage } from '@/admin/pages/stats/UserStatsPage'
import { GraphPage } from '@/admin/pages/graph/GraphPage'
import { PromoPage } from '@/admin/pages/promo/PromoPage'
import { TariffsPage } from '@/admin/pages/tariffs/TariffsPage'
import { ManageUsersPage } from '@/admin/pages/manage-users/ManageUsersPage'
import { BroadcastPage } from '@/admin/pages/broadcast/BroadcastPage'
import { SettingsPage } from '@/admin/pages/settings/SettingsPage'
import { AdminsPage } from '@/admin/pages/admins/AdminsPage'

interface Props {
  token: string
  /** true — вход через /admin (?admin_entry=full): полный доступ. false — через
   *  Start/меню: скрыты «Пользователи» (AdminNav, роуты /a/users*) и Live-события
   *  дашборда (см. DashboardPage). */
  fullAccess: boolean
}

// Собственный HashRouter, отдельный от основного приложения (#root). Оба
// роутера слушают один и тот же window.location.hash — конфликт с редиректом
// основного каталога решён исключением "/a/*" в App.tsx (см. комментарий там).
export function AdminApp({ token, fullAccess }: Props) {
  const [isSuperadmin, setIsSuperadmin] = useState(false)
  const { toasts, showToast } = useToasts()

  useEffect(() => {
    setToken(token)
    // Единственный способ узнать флаг "superadmin" внутри админ-бандла —
    // mount() передаёт только token (см. src/app/App.tsx maybeLoadExtraModule).
    fetchMe()
      .then(me => setIsSuperadmin(!!me.flags?.includes('superadmin')))
      .catch(() => {})
  }, [token])

  return (
    <AdminCtx.Provider value={{ isSuperadmin, fullAccess, showToast }}>
      <div className="admin-app">
        <HashRouter>
          <AdminNav isSuperadmin={isSuperadmin} fullAccess={fullAccess} />
          <div className="admin-content">
            <Routes>
              <Route path="/a/dashboard" element={<DashboardPage />} />
              <Route
                path="/a/users"
                element={fullAccess ? <UsersPage /> : <Navigate to="/a/dashboard" replace />}
              />
              <Route
                path="/a/users/:id"
                element={fullAccess ? <UserDetailPage /> : <Navigate to="/a/dashboard" replace />}
              />
              <Route path="/a/chat/:userId/:chatId" element={<ChatMessagesPage />} />
              <Route path="/a/stats" element={<StatsPage />} />
              <Route path="/a/stats/user/:tid" element={<UserStatsPage />} />
              <Route
                path="/a/graph"
                element={fullAccess ? <GraphPage /> : <Navigate to="/a/dashboard" replace />}
              />
              <Route path="/a/promo" element={<PromoPage />} />
              <Route path="/a/tariffs" element={<TariffsPage />} />
              <Route path="/a/manage-users" element={<ManageUsersPage />} />
              <Route path="/a/broadcast" element={<BroadcastPage />} />
              <Route path="/a/settings" element={<SettingsPage />} />
              <Route
                path="/a/admins"
                element={isSuperadmin ? <AdminsPage /> : <Navigate to="/a/dashboard" replace />}
              />
              <Route path="*" element={<Navigate to="/a/dashboard" replace />} />
            </Routes>
          </div>
        </HashRouter>
        <AdminToast toasts={toasts} />
      </div>
    </AdminCtx.Provider>
  )
}
