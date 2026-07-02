import { useEffect, useState, type FormEvent } from 'react'
import type { UserProfileOut, UserSubscriptionItem } from '@/admin/entities/manage-user'
import { banUser, findUser, getUserSubscriptions, grantTariff, unbanUser } from '@/admin/entities/manage-user'
import type { TariffOut } from '@/admin/entities/tariff'
import { listTariffs } from '@/admin/entities/tariff'
import { useAdminCtx } from '@/admin/shared/lib/AdminCtx'
import { fmtDate, fmtDateTime } from '@/admin/shared/lib/format'
import { SubBadge } from '@/admin/shared/ui'

// Порт handlers/admin/users_mgmt.py на карточку профиля мини-аппа.
export function ManageUsersPage() {
  const { showToast } = useAdminCtx()
  const [q, setQ] = useState('')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')
  const [profile, setProfile] = useState<UserProfileOut | null>(null)
  const [subs, setSubs] = useState<UserSubscriptionItem[]>([])
  const [tariffs, setTariffs] = useState<TariffOut[]>([])

  useEffect(() => {
    listTariffs()
      .then(res => setTariffs(res.items.filter(t => t.is_active)))
      .catch(() => {})
  }, [])

  const search = (e: FormEvent) => {
    e.preventDefault()
    if (!q.trim()) return
    setLoading(true)
    setError('')
    setProfile(null)
    setSubs([])
    findUser(q.trim())
      .then(p => {
        setProfile(p)
        return getUserSubscriptions(p.telegram_id)
          .then(res => setSubs(res.items))
          .catch(() => {})
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
          tariffs={tariffs}
          onUpdated={p => setProfile(p)}
          showToast={showToast}
        />
      )}
    </div>
  )
}

function UserProfileCard({
  profile,
  subs,
  tariffs,
  onUpdated,
  showToast,
}: {
  profile: UserProfileOut
  subs: UserSubscriptionItem[]
  tariffs: TariffOut[]
  onUpdated: (p: UserProfileOut) => void
  showToast: (msg: string, type?: 'success' | 'error' | 'info') => void
}) {
  const [banReason, setBanReason] = useState('')
  const [showBanForm, setShowBanForm] = useState(false)
  const [tariffId, setTariffId] = useState(tariffs[0] ? String(tariffs[0].id) : '')
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
      </div>

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
