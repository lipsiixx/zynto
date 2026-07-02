import { useCallback, useEffect, useState, type FormEvent } from 'react'
import type { AdminOut } from '@/admin/entities/admins'
import { addAdmin, listAdmins, removeAdmin } from '@/admin/entities/admins'
import { useAdminCtx } from '@/admin/shared/lib/AdminCtx'
import { fmtDate } from '@/admin/shared/lib/format'
import { ConfirmButton } from '@/admin/shared/ui'

// Доступ ограничен на уровне маршрута в AdminApp.tsx (require_webapp_superadmin
// на бэкенде отдаёт 404 всем остальным — фронт лишь скрывает пункт меню).
export function AdminsPage() {
  const { showToast } = useAdminCtx()
  const [items, setItems] = useState<AdminOut[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [identifier, setIdentifier] = useState('')
  const [adding, setAdding] = useState(false)

  const load = useCallback(() => {
    setLoading(true)
    setError('')
    listAdmins()
      .then(res => setItems(res.items))
      .catch(e => setError((e as Error).message))
      .finally(() => setLoading(false))
  }, [])

  useEffect(() => {
    load()
  }, [load])

  const handleAdd = (e: FormEvent) => {
    e.preventDefault()
    if (!identifier.trim()) return
    setAdding(true)
    addAdmin(identifier.trim())
      .then(created => {
        setItems(prev => [...prev, created])
        setIdentifier('')
        showToast('Админ добавлен', 'success')
      })
      .catch(e => {
        const msg = (e as Error).message
        showToast(msg === 'user_not_found' ? 'Пользователь не найден (не запускал бота)' : msg, 'error')
      })
      .finally(() => setAdding(false))
  }

  const handleRemove = (telegramId: number) => {
    removeAdmin(telegramId)
      .then(() => {
        setItems(prev => prev.filter(a => a.telegram_id !== telegramId))
        showToast('Админ удалён', 'success')
      })
      .catch(e => showToast((e as Error).message, 'error'))
  }

  return (
    <div className="admin-page">
      <div className="admin-page-header">
        <h1>Админы</h1>
      </div>

      <form className="card admin-form" onSubmit={handleAdd}>
        <div className="admin-form-row">
          <label className="text-sm text2">Добавить админа (@username или Telegram ID)</label>
          <div className="row gap-8">
            <input className="input" style={{ flex: 1 }} value={identifier} onChange={e => setIdentifier(e.target.value)} />
            <button className="btn btn-primary" style={{ width: 'auto' }} type="submit" disabled={adding || !identifier.trim()}>
              {adding ? '…' : 'Добавить'}
            </button>
          </div>
        </div>
      </form>

      {error && <div className="admin-error-msg">{error}</div>}

      {loading ? (
        <div className="loading-center">
          <div className="spinner" />
        </div>
      ) : !items.length ? (
        <div className="empty-state">
          <div className="icon">🛡</div>
          <div>Обычных админов нет</div>
        </div>
      ) : (
        <div className="admin-card-list">
          {items.map(a => (
            <div key={a.telegram_id} className="card">
              <div className="row" style={{ justifyContent: 'space-between', alignItems: 'flex-start' }}>
                <div>
                  <div className="semibold">{a.full_name || 'Без имени'}</div>
                  <div className="row gap-8 text-xs text2" style={{ marginTop: 2, flexWrap: 'wrap' }}>
                    {a.username && <span>@{a.username}</span>}
                    <span className="admin-mono">{a.telegram_id}</span>
                  </div>
                  <div className="text-xs text2" style={{ marginTop: 4 }}>Добавлен: {fmtDate(a.added_at)}</div>
                </div>
                <ConfirmButton label="Удалить" onConfirm={() => handleRemove(a.telegram_id)} />
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  )
}
