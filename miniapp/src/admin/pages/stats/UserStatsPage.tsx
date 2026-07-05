import { useCallback, useEffect, useState } from 'react'
import { useNavigate, useParams } from 'react-router-dom'
import { getUserDailyStats, getUserTopChats, type TopChatItem, type UserDailyStatItem } from '@/admin/entities/stats'
import {
  findUser,
  getUserStats,
  getUserSubscriptions,
  type UserProfileOut,
  type UserStatsOut,
  type UserSubscriptionItem,
} from '@/admin/entities/manage-user'
import { fmtDate, fmtDateTime } from '@/admin/shared/lib/format'
import { SubBadge } from '@/admin/shared/ui'
import { MessagesChart, RankRow } from './charts'

const RANGES = [7, 30, 90] as const

const PAYMENT_METHOD_LABEL: Record<string, string> = {
  stars: 'Stars',
  promo_code: 'промокод',
  gift: 'подарок',
  gift_purchase: 'покупка подарка',
  manual: 'вручную',
  referral: 'реферальная',
  tribute_sbp: 'СБП',
}

// Подробная статистика одного пользователя: карточки, график сообщений по
// дням, рефералы/оплаты, история подписок. Открывается из списка на /a/stats.
export function UserStatsPage() {
  const { tid } = useParams<{ tid: string }>()
  const navigate = useNavigate()
  const [profile, setProfile] = useState<UserProfileOut | null>(null)
  const [stats, setStats] = useState<UserStatsOut | null>(null)
  const [subs, setSubs] = useState<UserSubscriptionItem[]>([])
  const [days, setDays] = useState<number>(30)
  const [daily, setDaily] = useState<UserDailyStatItem[]>([])
  const [topChats, setTopChats] = useState<TopChatItem[]>([])
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(true)

  const telegramId = Number(tid)

  useEffect(() => {
    if (!telegramId) return
    setLoading(true)
    findUser(String(telegramId))
      .then(p => {
        setProfile(p)
        getUserStats(telegramId).then(setStats).catch(() => {})
        getUserSubscriptions(telegramId).then(res => setSubs(res.items)).catch(() => {})
        getUserTopChats(telegramId).then(res => setTopChats(res.items)).catch(() => {})
      })
      .catch(e => setError((e as Error).message === 'user_not_found' ? 'Пользователь не найден' : (e as Error).message))
      .finally(() => setLoading(false))
  }, [telegramId])

  const loadDaily = useCallback(() => {
    if (!telegramId) return
    getUserDailyStats(telegramId, days)
      .then(res => setDaily(res.items))
      .catch(() => {})
  }, [telegramId, days])

  useEffect(() => {
    loadDaily()
  }, [loadDaily])

  return (
    <div className="admin-page">
      <div className="admin-page-header">
        <h1 style={{ marginBottom: 0 }}>Статистика пользователя</h1>
        <button className="admin-icon-btn" onClick={() => navigate('/a/stats')}>
          ← Назад
        </button>
      </div>

      {error && <div className="admin-error-msg">{error}</div>}

      {loading ? (
        <div className="loading-center">
          <div className="spinner" />
        </div>
      ) : profile && (
        <>
          <div className="card">
            <div className="row" style={{ justifyContent: 'space-between', alignItems: 'flex-start' }}>
              <div>
                <div className="semibold" style={{ fontSize: 16 }}>{profile.full_name || 'Без имени'}</div>
                <div className="row gap-8 text-xs text2" style={{ marginTop: 4, flexWrap: 'wrap' }}>
                  {profile.username && <span>@{profile.username}</span>}
                  <span className="admin-mono">{profile.telegram_id}</span>
                  <span>с {fmtDate(profile.created_at)}</span>
                </div>
              </div>
              <div className="row gap-4" style={{ flexDirection: 'column', alignItems: 'flex-end' }}>
                <SubBadge status={profile.subscription_status} expiresAt={profile.subscription_expires_at} />
                {profile.is_banned && <span className="badge badge-red">Забанен</span>}
              </div>
            </div>
          </div>

          {stats && (
            <div className="admin-grid-4" style={{ marginTop: 12 }}>
              <MiniStat label="Контактов" value={stats.summary.contacts} />
              <MiniStat label="Сообщений" value={stats.summary.total_messages} />
              <MiniStat label="Удалённых" value={stats.summary.deleted} color="var(--red)" />
              <MiniStat label="Изменённых" value={stats.summary.edited} color="var(--yellow)" />
              <MiniStat label="Рефералов" value={stats.referral.total_referred} />
              <MiniStat label="Рефералов с оплатой" value={stats.referral.total_converted} />
              <MiniStat label="Дней за рефералов" value={stats.referral.total_days_earned} />
              <MiniStat label="Оплат / выдач" value={stats.payments.total} color="var(--green)" />
            </div>
          )}

          <div className="tabs" style={{ marginTop: 12 }}>
            {RANGES.map(r => (
              <button key={r} className={`tab${days === r ? ' active' : ''}`} onClick={() => setDays(r)}>
                {r} дней
              </button>
            ))}
          </div>

          <div className="admin-section-title">Сообщения по дням</div>
          <div className="card">
            <MessagesChart data={daily} />
          </div>

          {topChats.length > 0 && (
            <>
              <div className="admin-section-title">С кем общается больше всего</div>
              <div className="card">
                {topChats.map((c, i) => (
                  <RankRow
                    key={c.chat_id}
                    rank={i + 1}
                    label={c.title || `Чат ${c.chat_id}`}
                    value={c.messages}
                    max={topChats[0]?.messages ?? 0}
                    extra={c.deleted || c.edited ? `удал. ${c.deleted} · изм. ${c.edited}` : undefined}
                  />
                ))}
              </div>
            </>
          )}

          {stats && Object.keys(stats.payments.by_method).length > 0 && (
            <div className="text-xs text2" style={{ marginTop: 10 }}>
              Оплаты по способам:{' '}
              {Object.entries(stats.payments.by_method)
                .map(([m, n]) => `${PAYMENT_METHOD_LABEL[m] ?? m}: ${n}`)
                .join(', ')}
            </div>
          )}

          <div className="admin-section-title">История подписок</div>
          {!subs.length ? (
            <div className="empty-state"><div>Подписок ещё не было</div></div>
          ) : (
            <div className="card admin-table-wrap">
              <table className="admin-table">
                <thead>
                  <tr>
                    <th>Способ</th>
                    <th>Выдана</th>
                    <th>Истекает</th>
                  </tr>
                </thead>
                <tbody>
                  {subs.map((s, i) => (
                    <tr key={i}>
                      <td>{PAYMENT_METHOD_LABEL[s.payment_method] ?? s.payment_method}</td>
                      <td className="text-xs text2">{fmtDateTime(s.created_at)}</td>
                      <td className="text-xs text2">{s.expires_at ? fmtDateTime(s.expires_at) : 'навсегда'}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </>
      )}
    </div>
  )
}

function MiniStat({ label, value, color }: { label: string; value: number; color?: string }) {
  return (
    <div className="admin-stat-card">
      <div className="admin-stat-label">{label}</div>
      <div className="admin-stat-value" style={color ? { color } : undefined}>{value}</div>
    </div>
  )
}
