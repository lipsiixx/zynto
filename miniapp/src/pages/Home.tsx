import { useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import { useApp } from '../App'

function fmtDate(iso: string | null) {
  if (!iso) return ''
  return new Date(iso).toLocaleDateString('ru', { day: '2-digit', month: 'long', year: 'numeric' })
}

function SubBadge({ status, expiresAt }: { status: string; expiresAt: string | null }) {
  if (status === 'lifetime') return <span className="badge badge-purple">♾ Навсегда</span>
  if (status === 'active') {
    const d = expiresAt ? fmtDate(expiresAt) : ''
    return <span className="badge badge-green">✅ до {d}</span>
  }
  if (status === 'expired') return <span className="badge badge-red">Истекла</span>
  return <span className="badge badge-gray">Нет подписки</span>
}

export function Home() {
  const { me, refreshMe } = useApp()
  const navigate = useNavigate()

  useEffect(() => {
    refreshMe()
  }, [refreshMe])

  if (!me) {
    return <div className="loading-center"><div className="spinner" /></div>
  }

  const initials = me.full_name
    ? me.full_name.split(' ').slice(0, 2).map(w => w[0]).join('').toUpperCase()
    : '?'

  const { summary, subscription, monitoring_active } = me

  return (
    <div className="page">
      {/* Profile */}
      <div className="card card-glow" style={{ display: 'flex', alignItems: 'center', gap: 14 }}>
        <div className="avatar" style={{ width: 56, height: 56, fontSize: 20 }}>{initials}</div>
        <div style={{ flex: 1, minWidth: 0 }}>
          <div className="bold truncate" style={{ fontSize: 17 }}>{me.full_name}</div>
          {me.username && <div className="text-sm text3">@{me.username}</div>}
          <div className="mt-8">
            <SubBadge status={subscription.status} expiresAt={subscription.expires_at} />
          </div>
        </div>
      </div>

      {/* Monitoring status */}
      <div className="card" style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
        <div style={{
          width: 10, height: 10, borderRadius: '50%',
          background: monitoring_active ? 'var(--green)' : 'var(--text3)',
          boxShadow: monitoring_active ? '0 0 8px var(--green)' : 'none',
          flexShrink: 0,
        }} />
        <div>
          <div className="semibold text-sm">
            {monitoring_active ? 'Мониторинг активен' : 'Мониторинг не подключён'}
          </div>
          <div className="text-xs text3">
            {monitoring_active
              ? 'Слежу за удалёнными и изменёнными сообщениями'
              : 'Подключи бизнес-аккаунт в Telegram'}
          </div>
        </div>
      </div>

      {/* Stats */}
      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 10, marginBottom: 12 }}>
        <StatCard label="Контактов" value={summary.contacts} icon="👥" />
        <StatCard label="Сообщений" value={summary.total_messages} icon="💬" />
        <StatCard label="Удалено" value={summary.deleted} icon="🗑" accent="var(--red)" />
        <StatCard label="Изменено" value={summary.edited} icon="✏️" accent="var(--yellow)" />
      </div>

      {/* Actions */}
      {subscription.has_active && (
        <button className="btn btn-primary" onClick={() => navigate('/contacts')}>
          <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
            <path d="M17 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2" />
            <circle cx="9" cy="7" r="4" />
          </svg>
          Открыть историю
        </button>
      )}

      {!subscription.has_active && (
        <button className="btn btn-primary mt-8" onClick={() => navigate('/subscription')}>
          💳 Оформить подписку
        </button>
      )}
    </div>
  )
}

function StatCard({
  label, value, icon, accent,
}: {
  label: string; value: number; icon: string; accent?: string
}) {
  return (
    <div className="card" style={{ padding: '14px 16px' }}>
      <div style={{ fontSize: 22, marginBottom: 6 }}>{icon}</div>
      <div className="bold" style={{ fontSize: 22, color: accent || 'var(--text)' }}>
        {value.toLocaleString()}
      </div>
      <div className="text-xs text2">{label}</div>
    </div>
  )
}
