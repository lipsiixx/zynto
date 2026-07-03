import { useEffect, useState, type FormEvent } from 'react'
import type { UserProfileOut, UserStatsOut, UserSubscriptionItem } from '@/admin/entities/manage-user'
import {
  banUser,
  findUser,
  getUserStats,
  getUserSubscriptions,
  grantTariff,
  setSubscription,
  unbanUser,
} from '@/admin/entities/manage-user'
import type { TariffOut } from '@/admin/entities/tariff'
import { listTariffs } from '@/admin/entities/tariff'
import { useAdminCtx } from '@/admin/shared/lib/AdminCtx'
import { fmtDate, fmtDateTime } from '@/admin/shared/lib/format'
import { ConfirmButton, SubBadge } from '@/admin/shared/ui'

const PAYMENT_METHOD_LABEL: Record<string, string> = {
  stars: 'Stars',
  promo_code: 'промокод',
  gift: 'подарок',
  gift_purchase: 'покупка подарка',
  manual: 'вручную',
  tribute_sbp: 'СБП',
}

// Порт handlers/admin/users_mgmt.py на карточку профиля мини-аппа.
export function ManageUsersPage() {
  const { showToast } = useAdminCtx()
  const [q, setQ] = useState('')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')
  const [profile, setProfile] = useState<UserProfileOut | null>(null)
  const [subs, setSubs] = useState<UserSubscriptionItem[]>([])
  const [stats, setStats] = useState<UserStatsOut | null>(null)
  const [tariffs, setTariffs] = useState<TariffOut[]>([])

  useEffect(() => {
    listTariffs()
      .then(res => setTariffs(res.items.filter(t => t.is_active)))
      .catch(() => {})
  }, [])

  const loadExtras = (telegramId: number) => {
    getUserSubscriptions(telegramId)
      .then(res => setSubs(res.items))
      .catch(() => {})
    getUserStats(telegramId)
      .then(setStats)
      .catch(() => {})
  }

  const search = (e: FormEvent) => {
    e.preventDefault()
    if (!q.trim()) return
    setLoading(true)
    setError('')
    setProfile(null)
    setSubs([])
    setStats(null)
    findUser(q.trim())
      .then(p => {
        setProfile(p)
        loadExtras(p.telegram_id)
      })
      .catch(e => setError((e as Error).message === 'user_not_found' ? 'Пользователь не найден' : (e as Error).message))
      .finally(() => setLoading(false))
  }

  return (
    <div className="admin-page">
      <div className="admin-page-header">
        <h1>Пользователи</h1>
      </div>

      <form className="admin-search-row" onSubmit={search}>
        <div className="search-wrap">
          <input
            className="input"
            placeholder="@username или Telegram ID…"
            value={q}
            onChange={e => setQ(e.target.value)}
          />
        </div>
        <button className="btn btn-primary" style={{ width: 'auto' }} type="submit" disabled={loading}>
          {loading ? '…' : 'Найти'}
        </button>
      </form>

      {error && <div className="admin-error-msg">{error}</div>}

      {loading && (
        <div className="loading-center">
          <div className="spinner" />
        </div>
      )}

      {profile && (
        <UserProfileCard
          profile={profile}
          subs={subs}
          stats={stats}
          tariffs={tariffs}
          onUpdated={p => {
            setProfile(p)
            loadExtras(p.telegram_id)
          }}
          showToast={showToast}
        />
      )}
    </div>
  )
}

function UserStatsCard({ stats }: { stats: UserStatsOut }) {
  const methods = Object.entries(stats.payments.by_method)
    .map(([m, n]) => `${PAYMENT_METHOD_LABEL[m] ?? m}: ${n}`)
    .join(', ')

  return (
    <div className="card">
      <div className="admin-stats-grid">
        <div>
          <div className="text-xs text2">Контактов</div>
          <div className="bold">{stats.summary.contacts}</div>
        </div>
        <div>
          <div className="text-xs text2">Сообщений</div>
          <div className="bold">{stats.summary.total_messages}</div>
        </div>
        <div>
          <div className="text-xs text2">Удалённых</div>
          <div className="bold">{stats.summary.deleted}</div>
        </div>
        <div>
          <div className="text-xs text2">Изменённых</div>
          <div className="bold">{stats.summary.edited}</div>
        </div>
        <div>
          <div className="text-xs text2">Приглашено рефералов</div>
          <div className="bold">{stats.referral.total_referred}</div>
        </div>
        <div>
          <div className="text-xs text2">Рефералов с оплатой</div>
          <div className="bold">{stats.referral.total_converted}</div>
        </div>
        <div>
          <div className="text-xs text2">Дней за рефералов</div>
          <div className="bold">{stats.referral.total_days_earned}</div>
        </div>
        <div>
          <div className="text-xs text2">Оплат / выдач</div>
          <div className="bold">{stats.payments.total}</div>
        </div>
      </div>
      {methods && (
        <div className="text-xs text2" style={{ marginTop: 10 }}>По способам: {methods}</div>
      )}
    </div>
  )
}

function UserProfileCard({
  profile,
  subs,
  stats,
  tariffs,
  onUpdated,
  showToast,
}: {
  profile: UserProfileOut
  subs: UserSubscriptionItem[]
  stats: UserStatsOut | null
  tariffs: TariffOut[]
  onUpdated: (p: UserProfileOut) => void
  showToast: (msg: string, type?: 'success' | 'error' | 'info') => void
}) {
  const [banReason, setBanReason] = useState('')
  const [showBanForm, setShowBanForm] = useState(false)
  const [tariffId, setTariffId] = useState(tariffs[0] ? String(tariffs[0].id) : '')
  const [customDays, setCustomDays] = useState('')
  const [busy, setBusy] = useState(false)

  useEffect(() => {
    if (!tariffId && tariffs[0]) setTariffId(String(tariffs[0].id))
  }, [tariffs, tariffId])

  const handleBan = () => {
    if (!banReason.trim()) return
    setBusy(true)
    banUser(profile.telegram_id, banReason.trim())
      .then(p => {
        onUpdated(p)
        setShowBanForm(false)
        setBanReason('')
        showToast('Пользователь заблокирован', 'success')
      })
      .catch(e => showToast((e as Error).message, 'error'))
      .finally(() => setBusy(false))
  }

  const handleUnban = () => {
    setBusy(true)
    unbanUser(profile.telegram_id)
      .then(p => {
        onUpdated(p)
        showToast('Разбанен', 'success')
      })
      .catch(e => showToast((e as Error).message, 'error'))
      .finally(() => setBusy(false))
  }

  const handleGrant = () => {
    if (!tariffId) return
    setBusy(true)
    grantTariff(profile.telegram_id, Number(tariffId))
      .then(p => {
        onUpdated(p)
        showToast('Тариф выдан', 'success')
      })
      .catch(e => showToast((e as Error).message, 'error'))
      .finally(() => setBusy(false))
  }

  const handleGrantDays = () => {
    const days = Number(customDays)
    if (!days || days < 1 || days > 3650) {
      showToast('Укажи от 1 до 3650 дней', 'error')
      return
    }
    setBusy(true)
    setSubscription(profile.telegram_id, 'days', days)
      .then(p => {
        onUpdated(p)
        setCustomDays('')
        showToast(`Выдано ${days} дн.`, 'success')
      })
      .catch(e => showToast((e as Error).message, 'error'))
      .finally(() => setBusy(false))
  }

  const handleLifetime = () => {
    setBusy(true)
    setSubscription(profile.telegram_id, 'lifetime')
      .then(p => {
        onUpdated(p)
        showToast('Выдан бессрочный доступ', 'success')
      })
      .catch(e => showToast((e as Error).message, 'error'))
      .finally(() => setBusy(false))
  }

  const handleRevoke = () => {
    setBusy(true)
    setSubscription(profile.telegram_id, 'revoke')
      .then(p => {
        onUpdated(p)
        showToast('Подписка отозвана', 'success')
      })
      .catch(e => showToast((e as Error).message, 'error'))
      .finally(() => setBusy(false))
  }

  const hasSub = profile.subscription_status === 'active' || profile.subscription_status === 'lifetime'

  return (
    <>
      <div className="card">
        <div className="row" style={{ justifyContent: 'space-between', alignItems: 'flex-start' }}>
          <div>
            <div className="semibold" style={{ fontSize: 16 }}>{profile.full_name || 'Без имени'}</div>
            <div className="row gap-8 text-xs text2" style={{ marginTop: 4, flexWrap: 'wrap' }}>
              {profile.username && <span>@{profile.username}</span>}
              <span className="admin-mono">{profile.telegram_id}</span>
            </div>
          </div>
          <div className="row gap-4" style={{ flexDirection: 'column', alignItems: 'flex-end' }}>
            <SubBadge status={profile.subscription_status} expiresAt={profile.subscription_expires_at} />
            {profile.is_banned && <span className="badge badge-red">Забанен</span>}
          </div>
        </div>

        <div className="divider" />

        <div className="admin-stats-grid">
          <div>
            <div className="text-xs text2">Регистрация</div>
            <div className="bold">{fmtDate(profile.created_at)}</div>
          </div>
          <div>
            <div className="text-xs text2">Активность</div>
            <div className="bold">{profile.last_active_at ? fmtDate(profile.last_active_at) : '—'}</div>
          </div>
          <div>
            <div className="text-xs text2">Бизнес-подключение</div>
            <div className="bold">{profile.business_connected ? '✓ Да' : '—'}</div>
          </div>
          <div>
            <div className="text-xs text2">Сообщений</div>
            <div className="bold">{profile.messages_count}</div>
          </div>
        </div>

        {profile.is_banned && profile.ban_reason && (
          <div className="admin-error-msg" style={{ marginTop: 12 }}>Причина бана: {profile.ban_reason}</div>
        )}

        <div className="divider" />

        <div className="row gap-8" style={{ flexWrap: 'wrap' }}>
          {profile.is_banned ? (
            <button className="admin-icon-btn" onClick={handleUnban} disabled={busy}>Разбанить</button>
          ) : (
            <button className="admin-icon-btn" onClick={() => setShowBanForm(v => !v)} disabled={busy}>Забанить</button>
          )}
        </div>

        {showBanForm && (
          <div className="admin-form-row" style={{ marginTop: 10 }}>
            <input
              className="input"
              placeholder="Причина бана"
              value={banReason}
              onChange={e => setBanReason(e.target.value)}
            />
            <button className="btn btn-danger" style={{ marginTop: 8 }} onClick={handleBan} disabled={busy || !banReason.trim()}>
              Подтвердить блокировку
            </button>
          </div>
        )}

        <div className="divider" />

        <div className="admin-form-row">
          <label className="text-sm text2">Выдать тариф</label>
          <div className="row gap-8">
            <select className="admin-select" style={{ flex: 1 }} value={tariffId} onChange={e => setTariffId(e.target.value)}>
              {tariffs.map(t => (
                <option key={t.id} value={t.id}>{t.name} ({t.duration_days === null ? 'навсегда' : `${t.duration_days} дн.`})</option>
              ))}
            </select>
            <button className="btn btn-primary" style={{ width: 'auto' }} onClick={handleGrant} disabled={busy || !tariffId}>
              Выдать
            </button>
          </div>
        </div>

        <div className="divider" />

        <div className="admin-form-row">
          <label className="text-sm text2">Подписка вручную</label>
          <div className="row gap-8">
            <input
              className="input"
              style={{ flex: 1 }}
              type="number"
              min={1}
              max={3650}
              placeholder="Дней"
              value={customDays}
              onChange={e => setCustomDays(e.target.value)}
            />
            <button className="btn btn-primary" style={{ width: 'auto' }} onClick={handleGrantDays} disabled={busy || !customDays}>
              Выдать дни
            </button>
          </div>
          <div className="row gap-8" style={{ marginTop: 8, flexWrap: 'wrap' }}>
            <button className="admin-icon-btn" onClick={handleLifetime} disabled={busy}>
              Сделать бессрочной
            </button>
            {hasSub && (
              <ConfirmButton label="Забрать подписку" className="admin-icon-btn" onConfirm={handleRevoke} disabled={busy} />
            )}
          </div>
        </div>
      </div>

      {stats && (
        <>
          <div className="admin-section-title">Статистика</div>
          <UserStatsCard stats={stats} />
        </>
      )}

      <div className="admin-section-title">История подписок</div>
      {!subs.length ? (
        <div className="empty-state"><div>Подписок ещё не было</div></div>
      ) : (
        <div className="card admin-table-wrap">
          <table className="admin-table">
            <thead>
              <tr>
                <th>Способ оплаты</th>
                <th>Выдана</th>
                <th>Истекает</th>
              </tr>
            </thead>
            <tbody>
              {subs.map((s, i) => (
                <tr key={i}>
                  <td>{s.payment_method}</td>
                  <td className="text-xs text2">{fmtDateTime(s.created_at)}</td>
                  <td className="text-xs text2">{s.expires_at ? fmtDateTime(s.expires_at) : 'навсегда'}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </>
  )
}
