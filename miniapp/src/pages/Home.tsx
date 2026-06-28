import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { useApp } from '../App'
import { getInstructionPhotoUrl } from '../api'

// ── Countdown ─────────────────────────────────────────────────────────────

function calcRemaining(expiresAt: string): { d: number; h: number; m: number; s: number; total: number } {
  const diff = Math.max(0, new Date(expiresAt).getTime() - Date.now())
  const total = Math.floor(diff / 1000)
  const d = Math.floor(total / 86400)
  const h = Math.floor((total % 86400) / 3600)
  const m = Math.floor((total % 3600) / 60)
  const s = total % 60
  return { d, h, m, s, total }
}

function pad(n: number) { return String(n).padStart(2, '0') }

function Countdown({ expiresAt }: { expiresAt: string }) {
  const [rem, setRem] = useState(() => calcRemaining(expiresAt))

  useEffect(() => {
    const id = setInterval(() => setRem(calcRemaining(expiresAt)), 1000)
    return () => clearInterval(id)
  }, [expiresAt])

  if (rem.total <= 0) {
    return <div className="countdown-expired">Подписка истекла</div>
  }

  // Больше 3 суток — показываем только дни
  if (rem.d >= 3) {
    return (
      <div className="countdown-wrap">
        <div className="countdown-label">До истечения подписки</div>
        <div className="countdown-days">
          {rem.d} {rem.d % 10 === 1 && rem.d !== 11 ? 'день' : rem.d % 10 <= 4 && (rem.d < 11 || rem.d > 14) ? 'дня' : 'дней'}
          {rem.h > 0 && <span className="countdown-days-h"> {rem.h} ч</span>}
        </div>
      </div>
    )
  }

  // Меньше 3 суток — тикающий таймер HH:MM:SS
  return (
    <div className="countdown-wrap">
      <div className="countdown-label">До истечения подписки</div>
      {rem.d > 0 && (
        <div className="countdown-days-sm">{rem.d} д </div>
      )}
      <div className={`countdown-clock${rem.d === 0 && rem.h === 0 && rem.m < 30 ? ' countdown-urgent' : ''}`}>
        {rem.d > 0 ? `${pad(rem.h)}:${pad(rem.m)}:${pad(rem.s)}` : `${pad(rem.h)}:${pad(rem.m)}:${pad(rem.s)}`}
      </div>
    </div>
  )
}

function LifetimeBadge() {
  return (
    <div className="countdown-wrap">
      <div className="countdown-label">Статус подписки</div>
      <div className="countdown-lifetime">♾ Навсегда</div>
    </div>
  )
}

function HowToConnect() {
  const [open, setOpen] = useState(false)
  const [imgError, setImgError] = useState(false)

  return (
    <div className="card" style={{ marginBottom: 12 }}>
      <button
        className="how-connect-toggle"
        onClick={() => setOpen(o => !o)}
      >
        <span>📋 Как подключить бота?</span>
        <span className="how-connect-chevron">{open ? '▲' : '▼'}</span>
      </button>

      {open && (
        <div className="how-connect-body">
          {!imgError && (
            <img
              src={getInstructionPhotoUrl()}
              alt="Инструкция по подключению"
              className="how-connect-photo"
              onError={() => setImgError(true)}
              loading="lazy"
            />
          )}
          <div className="how-connect-steps">
            <div className="how-connect-step">
              <span className="step-num">1</span>
              <span>Открой <b>Настройки → Аккаунт</b><br /><span style={{color:'var(--text3)',fontSize:12}}>iOS: Профиль → Изменить</span></span>
            </div>
            <div className="how-connect-step">
              <span className="step-num">2</span>
              <span>Найди раздел <b>«Автоматизация чатов»</b></span>
            </div>
            <div className="how-connect-step">
              <span className="step-num">3</span>
              <span>Добавь <b>@zynto_bot</b> и нажми <b>«Добавить»</b></span>
            </div>
          </div>
          <div className="text-xs text3" style={{marginTop:8}}>
            ✅ После подключения бот пришлёт подтверждение
          </div>
        </div>
      )}
    </div>
  )
}

function NoSubBlock() {
  const navigate = useNavigate()
  return (
    <div className="no-sub-block">
      <div className="no-sub-emoji">😔</div>
      <div className="no-sub-title">Подписка не оформлена</div>
      <div className="no-sub-text">
        Без подписки удалённые и изменённые сообщения не сохраняются.<br />
        Оформи подписку — и больше ничего не потеряешь.
      </div>
      <button className="btn btn-primary" style={{ marginTop: 20 }} onClick={() => navigate('/subscription')}>
        💳 Оформить подписку
      </button>
    </div>
  )
}

// ── Main ──────────────────────────────────────────────────────────────────

export function Home() {
  const { me, refreshMe } = useApp()
  const navigate = useNavigate()

  useEffect(() => { refreshMe() }, [refreshMe])

  if (!me) {
    return <div className="loading-center"><div className="spinner" /></div>
  }

  const { summary, subscription, monitoring_active } = me
  const initials = me.full_name
    ? me.full_name.split(' ').slice(0, 2).map(w => w[0]).join('').toUpperCase()
    : '?'

  const hasActive = subscription.has_active
  const isLifetime = subscription.status === 'lifetime'

  return (
    <div className="page">
      {/* Profile */}
      <div className="card card-glow" style={{ display: 'flex', alignItems: 'center', gap: 14 }}>
        <div className="avatar" style={{ width: 56, height: 56, fontSize: 20 }}>{initials}</div>
        <div style={{ flex: 1, minWidth: 0 }}>
          <div className="bold truncate" style={{ fontSize: 17 }}>{me.full_name}</div>
          {me.username && <div className="text-sm text3">@{me.username}</div>}
        </div>
      </div>

      {/* Subscription countdown / no-sub */}
      {hasActive && isLifetime && <LifetimeBadge />}
      {hasActive && !isLifetime && subscription.expires_at && (
        <div className="card">
          <Countdown expiresAt={subscription.expires_at} />
          <button
            className="btn btn-secondary"
            style={{ marginTop: 14, fontSize: 13 }}
            onClick={() => navigate('/subscription')}
          >
            Продлить подписку
          </button>
        </div>
      )}
      {!hasActive && <NoSubBlock />}

      {/* Monitoring status */}
      {hasActive && (
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
      )}

      {/* How to connect — показываем когда мониторинг не активен */}
      {hasActive && !monitoring_active && <HowToConnect />}

      {/* Stats */}
      {hasActive && (
        <>
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 10, marginBottom: 12 }}>
            <StatCard label="Контактов" value={summary.contacts} icon="👥" />
            <StatCard label="Сообщений" value={summary.total_messages} icon="💬" />
            <StatCard label="Удалено" value={summary.deleted} icon="🗑" accent="var(--red)" />
            <StatCard label="Изменено" value={summary.edited} icon="✏️" accent="var(--yellow)" />
          </div>
          <button className="btn btn-primary" onClick={() => navigate('/contacts')}>
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <path d="M17 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2" />
              <circle cx="9" cy="7" r="4" />
            </svg>
            Открыть историю
          </button>
        </>
      )}
    </div>
  )
}

function StatCard({ label, value, icon, accent }: {
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
