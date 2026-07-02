import { useEffect, useState } from 'react'
import { useNavigate, useParams } from 'react-router-dom'
import type {
  AdminUser,
  ChatsListResponse,
  UserContactsResponse,
  UserStats,
} from '@/admin/entities/user'
import { getUser, getUserChats, getUserContacts, getUserStats } from '@/admin/entities/user'
import { mediaUrl } from '@/admin/shared/api/adminApi'
import { fmtDate, initials, relTime } from '@/admin/shared/lib/format'
import { Paginator, SubBadge } from '@/admin/shared/ui'

// Порт UserDetail.jsx (C:\projects\admin-panel\src\pages\UserDetail.jsx).
// Вкладка «Контакты» в Phase 1 — простая таблица (интерактивный граф связей —
// GraphPage.tsx, отдельная задача).
export function UserDetailPage() {
  const { id } = useParams<{ id: string }>()
  const navigate = useNavigate()
  const userId = Number(id)

  const [tab, setTab] = useState<'chats' | 'contacts'>('chats')
  const [user, setUser] = useState<AdminUser | null>(null)
  const [stats, setStats] = useState<UserStats | null>(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    let cancelled = false
    setLoading(true)
    setUser(null)
    getUser(userId)
      .then(u => {
        if (!cancelled) setUser(u)
      })
      .catch(() => {
        if (!cancelled) setUser(null)
      })
      .finally(() => {
        if (!cancelled) setLoading(false)
      })
    return () => {
      cancelled = true
    }
  }, [userId])

  useEffect(() => {
    if (!user) return
    let cancelled = false
    getUserStats(user.id)
      .then(s => {
        if (!cancelled) setStats(s)
      })
      .catch(() => {
        /* статистика не критична для отображения карточки */
      })
    return () => {
      cancelled = true
    }
  }, [user])

  if (loading) {
    return (
      <div className="admin-page">
        <div className="loading-center">
          <div className="spinner" />
        </div>
      </div>
    )
  }

  if (!user) {
    return (
      <div className="admin-page">
        <div className="empty-state">
          <div>Пользователь не найден</div>
        </div>
      </div>
    )
  }

  return (
    <div className="admin-page">
      <div className="admin-breadcrumb">
        <span className="admin-breadcrumb-link" onClick={() => navigate('/a/users')}>
          Пользователи
        </span>
        <span className="admin-breadcrumb-sep">/</span>
        <span>{user.fullName}</span>
      </div>

      <div className="card admin-user-card">
        <div className="row admin-user-card-top">
          <UserAvatarLg user={user} />
          <div style={{ flex: 1, minWidth: 0 }}>
            <div className="row gap-8" style={{ flexWrap: 'wrap' }}>
              <span className="bold" style={{ fontSize: 18 }}>
                {user.fullName}
              </span>
              <SubBadge status={user.subscriptionStatus} expiresAt={user.subscriptionExpiresAt} />
              {user.isBanned && <span className="badge badge-red">Заблокирован</span>}
              {user.isBlocked && <span className="badge badge-gray">Бот заблокирован</span>}
            </div>
            <div className="row gap-8 mt-8 text-xs text2" style={{ flexWrap: 'wrap' }}>
              {user.username && <span>@{user.username}</span>}
              <span className="admin-mono">{user.telegramId}</span>
              {user.phone && <span>{user.phone}</span>}
              <span>{user.languageCode}</span>
            </div>
          </div>
          <div className="text-xs text2 admin-user-meta">
            <div className="row gap-4" style={{ justifyContent: 'flex-end' }}>
              <div className={`admin-online-dot${user.isOnline ? ' online' : ''}`} />
              {user.isOnline ? <span style={{ color: 'var(--green)' }}>Онлайн</span> : 'Оффлайн'}
            </div>
            <div>Активен: {relTime(user.lastActiveAt)} назад</div>
            <div>Регистрация: {fmtDate(user.createdAt)}</div>
          </div>
        </div>

        {stats && (
          <>
            <div className="divider" />
            <div className="admin-stats-grid">
              {[
                { label: 'Сообщений', val: stats.totalMessages },
                { label: 'Удалено', val: stats.deletedMessages, color: 'var(--red)' },
                { label: 'Изменено', val: stats.editedMessages, color: 'var(--yellow)' },
                { label: 'Медиафайлов', val: stats.totalMedia },
                { label: 'Чатов', val: stats.totalChats },
              ].map(s => (
                <div key={s.label}>
                  <div className="text-xs text2">{s.label}</div>
                  <div className="bold" style={{ fontSize: 18, color: s.color || 'var(--text)' }}>
                    {s.val}
                  </div>
                </div>
              ))}
            </div>
          </>
        )}
      </div>

      <div className="tabs">
        <button className={`tab${tab === 'chats' ? ' active' : ''}`} onClick={() => setTab('chats')}>
          Чаты
        </button>
        <button className={`tab${tab === 'contacts' ? ' active' : ''}`} onClick={() => setTab('contacts')}>
          Контакты
        </button>
      </div>

      {tab === 'chats' && <ChatsTab user={user} />}
      {tab === 'contacts' && <ContactsTab user={user} />}
    </div>
  )
}

function ChatsTab({ user }: { user: AdminUser }) {
  const navigate = useNavigate()
  const [qInput, setQInput] = useState('')
  const [q, setQ] = useState('')
  const [filter, setFilter] = useState('')
  const [page, setPage] = useState(1)
  const [data, setData] = useState<ChatsListResponse | null>(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    const t = setTimeout(() => setQ(qInput), 300)
    return () => clearTimeout(t)
  }, [qInput])

  useEffect(() => {
    setPage(1)
  }, [q, filter])

  useEffect(() => {
    let cancelled = false
    setLoading(true)
    getUserChats(user.id, { q: q || undefined, filter: filter || undefined, page, limit: 20 })
      .then(d => {
        if (!cancelled) setData(d)
      })
      .catch(() => {
        if (!cancelled) setData(null)
      })
      .finally(() => {
        if (!cancelled) setLoading(false)
      })
    return () => {
      cancelled = true
    }
  }, [user.id, q, filter, page])

  const totalPages = data?.pagination.totalPages ?? 1

  const openChat = (chatId: number, title: string | null) => {
    const p = new URLSearchParams()
    if (title) p.set('title', title)
    const qs = p.toString()
    navigate(`/a/chat/${user.id}/${chatId}${qs ? `?${qs}` : ''}`)
  }

  return (
    <>
      <div className="admin-search-row">
        <input className="input" placeholder="Поиск по чату…" value={qInput} onChange={e => setQInput(e.target.value)} />
        <select className="admin-select" value={filter} onChange={e => setFilter(e.target.value)}>
          <option value="">Все чаты</option>
          <option value="has_deleted">Есть удалённые</option>
          <option value="has_edited">Есть изменённые</option>
        </select>
      </div>

      <div className="card admin-table-wrap">
        {loading ? (
          <div className="loading-center">
            <div className="spinner" />
          </div>
        ) : !data?.data.length ? (
          <div className="empty-state">
            <div className="icon">💬</div>
            <div>Чаты не найдены</div>
          </div>
        ) : (
          <table className="admin-table">
            <thead>
              <tr>
                <th>Чат</th>
                <th>Сообщений</th>
                <th>Удалено</th>
                <th>Изменено</th>
                <th>Последнее</th>
                <th />
              </tr>
            </thead>
            <tbody>
              {data.data.map(c => (
                <tr key={c.chatId} className="admin-row-clickable" onClick={() => openChat(c.chatId, c.title)}>
                  <td>
                    <div className="semibold">{c.title || <span className="text2">Без названия</span>}</div>
                    <div className="text-xs admin-mono text2">{c.chatId}</div>
                  </td>
                  <td>{c.messageCount}</td>
                  <td style={{ color: c.deletedCount ? 'var(--red)' : 'var(--text3)' }}>{c.deletedCount || '—'}</td>
                  <td style={{ color: c.editedCount ? 'var(--yellow)' : 'var(--text3)' }}>{c.editedCount || '—'}</td>
                  <td className="text-xs text2">{c.lastMessageAt ? `${relTime(c.lastMessageAt)} назад` : '—'}</td>
                  <td className="admin-row-arrow">→</td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>
      <Paginator page={page} totalPages={totalPages} onChange={setPage} />
    </>
  )
}

function ContactsTab({ user }: { user: AdminUser }) {
  const [page, setPage] = useState(1)
  const [data, setData] = useState<UserContactsResponse | null>(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    let cancelled = false
    setLoading(true)
    getUserContacts(user.id, { minWeight: 1, page, limit: 25 })
      .then(d => {
        if (!cancelled) setData(d)
      })
      .catch(() => {
        if (!cancelled) setData(null)
      })
      .finally(() => {
        if (!cancelled) setLoading(false)
      })
    return () => {
      cancelled = true
    }
  }, [user.id, page])

  const totalPages = data?.pagination.totalPages ?? 1

  return (
    <div className="card admin-table-wrap">
      {loading ? (
        <div className="loading-center">
          <div className="spinner" />
        </div>
      ) : !data?.data.length ? (
        <div className="empty-state">
          <div className="icon">👥</div>
          <div>Контакты не найдены</div>
        </div>
      ) : (
        <>
          <table className="admin-table">
            <thead>
              <tr>
                <th>Контакт</th>
                <th>Telegram ID</th>
                <th>Сообщений</th>
                <th>Совместных чатов</th>
              </tr>
            </thead>
            <tbody>
              {data.data.map((c, i) => (
                <tr key={i}>
                  <td>
                    <div className="semibold">{c.senderName || <span className="text2">Неизвестно</span>}</div>
                    {c.senderUsername && <div className="text-xs text2">@{c.senderUsername}</div>}
                  </td>
                  <td>
                    <span className="admin-mono">{c.senderId ?? '—'}</span>
                  </td>
                  <td>{c.messageCount}</td>
                  <td>{c.sharedChatsCount}</td>
                </tr>
              ))}
            </tbody>
          </table>
          <Paginator page={page} totalPages={totalPages} onChange={setPage} />
        </>
      )}
    </div>
  )
}

function UserAvatarLg({ user }: { user: AdminUser }) {
  const [err, setErr] = useState(false)
  if (user.avatarFileUniqueId && !err) {
    return (
      <div className="admin-avatar admin-avatar-lg">
        <img src={mediaUrl(user.avatarFileUniqueId)} onError={() => setErr(true)} alt="" />
      </div>
    )
  }
  return <div className="admin-avatar admin-avatar-lg">{initials(user.fullName)}</div>
}
