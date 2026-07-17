import { useState } from 'react'
import { AdminApp } from '@/admin/app/AdminApp'

interface Props {
  token: string
  fullAccess: boolean
  onDismiss: () => void
}

// Показывается при каждой холодной загрузке админ-бандла (см. main.tsx).
export function RoleChooser({ token, fullAccess, onDismiss }: Props) {
  const [asAdmin, setAsAdmin] = useState(false)

  if (asAdmin) {
    return <AdminApp token={token} fullAccess={fullAccess} />
  }

  return (
    <div className="admin-overlay">
      <div className="admin-chooser-card">
        <div className="admin-chooser-title">Zynto</div>
        <div className="admin-chooser-subtitle">Выберите режим входа</div>
        <button className="btn btn-primary" onClick={() => setAsAdmin(true)}>
          Войти как Админ
        </button>
        <button className="btn btn-secondary" onClick={onDismiss}>
          Войти как Пользователь
        </button>
      </div>
    </div>
  )
}
