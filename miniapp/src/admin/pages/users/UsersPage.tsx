import { useCallback, useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import type { AdminUser, UsersListResponse } from '@/admin/entities/user'
import { getUsers } from '@/admin/entities/user'
import { mediaUrl } from '@/admin/shared/api/adminApi'
import { initials, relTime } from '@/admin/shared/lib/format'
import { Paginator, SubBadge } from '@/admin/shared/ui'

const STATUSES: { value: string; label: string }[] = [
  { value: '', label: 'Все статусы' },
  { value: 'active', label: 'Активна' },
  { value: 'lifetime', label: 'Навсегда' },
  { value: 'expired', label: 'Истекла' },
  { value: 'none', label: 'Нет' },
]

const LIMIT = 25

// Порт Users.jsx (C:\projects\admin-panel\src\pages\Users.jsx) на конвенции
// этого репозитория: fetch-on-mount через useState/useEffect (как в
// pages/contacts/ui/ContactsPage.tsx), а не через хук useData.js.
export function UsersPage() {
  const navigate = useNavigate()
  const [qInput, setQInput] = useState('')
  const [q, setQ] = useState('')
  const [status, setStatus] = useState('')
  const [page, setPage] = useState(1)
  const [data, setData] = useState<UsersListResponse | null>(null)
  const [loading, setLoading] = useState(true)

  // Дебаунс поиска — без него запрос улетал бы на каждое нажатие клавиши.
  useEffect(() => {
    const t = setTimeout(() => setQ(qInput), 300)
    return () => clearTimeout(t)
  }, [qInput])

  useEffect(() => {
    setPage(1)
  }, [q, status])

  const load = useCallback(async () => {
    setLoading(true)
    try {
      const res = await getUsers({ q: q || undefined, status: status || undefined, page, limit: LIMIT })
      setData(res)
    } catch {
      setData(null)
    } finally {
      setLoading(false)
    }
  }, [q, status, page])

  useEffect(() => {
    load()
  }, [load])

  const total = data?.pagination.total ?? 0
  const totalPages = data?.pagination.totalPages ?? 1

  return (
    <div className="admin-page">
      <div className="admin-page-header">
        <h1>Пользователи</h1>
        {!loading && <span className="text2 text-sm">{total} записей</span>}
      </div>

      <div className="admin-search-row">
        <div className="search-wrap">
          <input
            className="input"
            placeholder="Имя, @username или Telegram ID…"
            value={qInput}
            onChange={e => setQInput(e.target.value)}
          />
        </div>
        <select className="admin-select" value={status} onChange={e => setStatus(e.target.value)}>
          {STATUSES.map(s => (
            <option key={s.value} value={s.value}>
              {s.label}
            </option>
          ))}
        </select>
      </div>

      <div className="card admin-table-wrap">
        {loading ? (
          <div className="loading-center">
            <div className="spinner" />
          </div>
        ) : !data?.data.length ? (
          <div className="empty-state">
            <div className="icon">👥</div>
            <div>Пользователи не найдены</div>
          </div>
        ) : (
          <table className="admin-table">
            <thead>
              <tr>
                <th />
                <th>Пользователь</th>
                <th>Telegram ID</th>
                <th>Подписка</th>
                <th>Последняя активность</th>
                <th />
              </tr>
            </thead>
            <tbody>
              {data.data.map(u => (
                <tr key={u.id} className="admin-row-clickable" onClick={() => navigate(`/a/users/${u.id}`)}>
                  <td>
                    <div className="row gap-8">
                      <div className={`admin-online-dot${u.isOnline ? ' online' : ''}`} />
                      <UserAvatar user={u} />
                    </div>
                  </td>
                  <td>
                    <div className="semibold">{u.fullName}</div>
                    {u.username && <div className="text-xs text2">@{u.username}</div>}
                  </td>
                  <td>
                    <span className="admin-mono">{u.telegramId}</span>
                  </td>
                  <td>
                    <SubBadge status={u.subscriptionStatus} expiresAt={u.subscriptionExpiresAt} />
                    {u.isBanned && (
                      <span className="badge badge-red" style={{ marginLeft: 4 }}>
                        Бан
                      </span>
                    )}
                  </td>
                  <td className="text-xs text2">{relTime(u.lastActiveAt)} назад</td>
                  <td className="admin-row-arrow">→</td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>

      <Paginator page={page} totalPages={totalPages} onChange={setPage} />
    </div>
  )
}

function UserAvatar({ user }: { user: AdminUser }) {
  const [err, setErr] = useState(false)
  if (user.avatarFileUniqueId && !err) {
    return (
      <div className="admin-avatar">
        <img src={mediaUrl(user.avatarFileUniqueId)} onError={() => setErr(true)} alt="" />
      </div>
    )
  }
  return <div className="admin-avatar">{initials(user.fullName)}</div>
}
