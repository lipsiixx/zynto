import { useEffect, useState, useCallback, useRef } from 'react'
import { useNavigate } from 'react-router-dom'
import type { Contact } from '@/entities/contact'
import { getContacts, TrustBar } from '@/entities/contact'
import { haptics } from '@/shared/lib/haptics'
import { Skeleton } from '@/shared/ui'

function fmtRelative(iso: string | null) {
  if (!iso) return ''
  const diff = Date.now() - new Date(iso).getTime()
  const m = Math.floor(diff / 60000)
  if (m < 1) return 'только что'
  if (m < 60) return `${m} мин назад`
  const h = Math.floor(m / 60)
  if (h < 24) return `${h} ч назад`
  const d = Math.floor(h / 24)
  if (d < 30) return `${d} дн назад`
  return new Date(iso).toLocaleDateString('ru', { day: '2-digit', month: 'short' })
}

function initials(title: string | null) {
  if (!title) return '?'
  return title.split(' ').slice(0, 2).map(w => w[0]).join('').toUpperCase()
}

export function ContactsPage() {
  const navigate = useNavigate()
  const [contacts, setContacts] = useState<Contact[]>([])
  const [loading, setLoading] = useState(true)
  const [q, setQ] = useState('')
  const [filter, setFilter] = useState<'all' | 'deleted' | 'edited'>('all')
  // Stagger-анимация только для первого показа списка; фильтры/поиск — без неё
  const firstAnim = useRef(true)
  const searchTimer = useRef<ReturnType<typeof setTimeout> | null>(null)

  const load = useCallback(async (query = '') => {
    setLoading(true)
    try {
      const res = await getContacts({ q: query || undefined })
      setContacts(res.data)
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => { load() }, [load])

  useEffect(() => {
    if (!loading && firstAnim.current) {
      const t = setTimeout(() => { firstAnim.current = false }, 700)
      return () => clearTimeout(t)
    }
  }, [loading])

  const handleSearch = (v: string) => {
    setQ(v)
    if (searchTimer.current) clearTimeout(searchTimer.current)
    searchTimer.current = setTimeout(() => load(v), 300)
  }

  const filtered = contacts.filter(c => {
    if (filter === 'deleted') return c.deleted_count > 0
    if (filter === 'edited') return c.edited_count > 0
    return true
  })

  return (
    <div className="page">
      <div className="page-header">
        <h1>Контакты</h1>
        <span className="badge badge-gray" style={{ marginLeft: 'auto' }}>
          {contacts.length}
        </span>
      </div>

      {/* Search */}
      <div className="search-wrap">
        <span className="icon">
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
            <circle cx="11" cy="11" r="8" /><line x1="21" y1="21" x2="16.65" y2="16.65" />
          </svg>
        </span>
        <input
          className="input"
          placeholder="Поиск контакта…"
          value={q}
          onChange={e => handleSearch(e.target.value)}
        />
      </div>

      {/* Filter tabs */}
      <div className="tabs">
        {(['all', 'deleted', 'edited'] as const).map(f => (
          <button
            key={f}
            className={`tab${filter === f ? ' active' : ''}`}
            onClick={() => { haptics.select(); setFilter(f) }}
          >
            {f === 'all' ? 'Все' : f === 'deleted' ? '🗑 Удалённые' : '✏️ Изменённые'}
          </button>
        ))}
      </div>

      {loading ? (
        <ContactsSkeleton />
      ) : filtered.length === 0 ? (
        <div className="empty-state">
          <div className="icon">📭</div>
          <div>Контактов не найдено</div>
        </div>
      ) : (
        filtered.map((c, i) => (
          <ContactRow
            key={c.chat_id}
            contact={c}
            animDelay={firstAnim.current ? Math.min(i, 8) * 30 : null}
            onClick={() => { haptics.tap(); navigate(`/contacts/${c.chat_id}`) }}
          />
        ))
      )}
    </div>
  )
}

function ContactsSkeleton() {
  return (
    <>
      {[0, 1, 2, 3, 4].map(i => (
        <div key={i} className="card" style={{ padding: '12px 14px' }}>
          <div className="row">
            <Skeleton h={40} w={40} r="50%" />
            <div style={{ flex: 1 }}>
              <Skeleton h={14} w="60%" />
              <Skeleton h={10} w="40%" style={{ marginTop: 8 }} />
            </div>
          </div>
        </div>
      ))}
    </>
  )
}

function ContactRow({ contact: c, animDelay, onClick }: { contact: Contact; animDelay: number | null; onClick: () => void }) {
  return (
    <div
      className={`card card-tap${animDelay !== null ? ' anim-rise' : ''}`}
      style={{
        cursor: 'pointer',
        padding: '12px 14px',
        ...(animDelay ? { animationDelay: `${animDelay}ms` } : {}),
      }}
      onClick={onClick}
    >
      <div className="row">
        <div className="avatar">{initials(c.chat_title)}</div>
        <div style={{ flex: 1, minWidth: 0 }}>
          <div className="row-between">
            <span className="semibold truncate" style={{ fontSize: 15 }}>
              {c.chat_title || `Чат ${c.chat_id}`}
            </span>
            <span className="text-xs text3" style={{ flexShrink: 0, marginLeft: 8 }}>
              {fmtRelative(c.last_message_at)}
            </span>
          </div>
          <div className="row gap-8 mt-8" style={{ flexWrap: 'wrap' }}>
            {c.deleted_count > 0 && (
              <span className="text-xs" style={{ color: 'var(--red)' }}>🗑 {c.deleted_count}</span>
            )}
            {c.edited_count > 0 && (
              <span className="text-xs" style={{ color: 'var(--yellow)' }}>✏️ {c.edited_count}</span>
            )}
            <span className="text-xs text3">💬 {c.total_messages}</span>
          </div>
        </div>
      </div>
      <div className="mt-8">
        <TrustBar score={c.trust_score} compact />
      </div>
    </div>
  )
}
