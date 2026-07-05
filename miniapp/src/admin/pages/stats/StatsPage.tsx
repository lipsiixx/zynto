import { useCallback, useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import {
  getDailyStats,
  getGlobalUserStats,
  getTopUsers,
  type DailyStatItem,
  type GlobalUserStats,
  type TopUserItem,
} from '@/admin/entities/stats'
import { listManagedUsers, type ManagedUsersListResponse } from '@/admin/entities/manage-user'
import { Paginator, SubBadge } from '@/admin/shared/ui'
import { CHART_COLORS, GrantsChart, MessagesChart, RankRow, SingleBarChart } from './charts'

const RANGES = [7, 30, 90] as const
const POLL_MS = 15000
const LIST_LIMIT = 10

// Аналитика бота: динамика по дням + список пользователей с переходом в
// подробную статистику (/a/stats/user/:tid). Сервер/прокси живут на Дашборде.
export function StatsPage() {
  const navigate = useNavigate()
  const [userStats, setUserStats] = useState<GlobalUserStats | null>(null)
  const [days, setDays] = useState<number>(30)
  const [daily, setDaily] = useState<DailyStatItem[]>([])
  const [dailyLoading, setDailyLoading] = useState(true)
  const [topUsers, setTopUsers] = useState<TopUserItem[]>([])

  const [qInput, setQInput] = useState('')
  const [q, setQ] = useState('')
  const [page, setPage] = useState(1)
  const [list, setList] = useState<ManagedUsersListResponse | null>(null)
  const [listLoading, setListLoading] = useState(true)

  // Счётчики обновляются сами — та же частота, что у Дашборда, чтобы данные
  // не выглядели «старее».
  useEffect(() => {
    const tick = () => getGlobalUserStats().then(setUserStats).catch(() => {})
    tick()
    const t = setInterval(tick, POLL_MS)
    return () => clearInterval(t)
  }, [])

  const loadDaily = useCallback(() => {
    setDailyLoading(true)
    Promise.all([
      getDailyStats(days).then(res => setDaily(res.items)).catch(() => {}),
      getTopUsers(days).then(res => setTopUsers(res.items)).catch(() => {}),
    ]).finally(() => setDailyLoading(false))
  }, [days])

  useEffect(() => {
    loadDaily()
  }, [loadDaily])

  useEffect(() => {
    const t = setTimeout(() => setQ(qInput), 300)
    return () => clearTimeout(t)
  }, [qInput])

  useEffect(() => {
    setPage(1)
  }, [q])

  useEffect(() => {
    setListLoading(true)
    listManagedUsers({ q: q || undefined, page, limit: LIST_LIMIT })
      .then(setList)
      .catch(() => {})
      .finally(() => setListLoading(false))
  }, [q, page])

  return (
    <div className="admin-page">
      <div className="admin-page-header">
        <h1 style={{ marginBottom: 0 }}>Статистика</h1>
        <button className="admin-icon-btn" onClick={loadDaily} disabled={dailyLoading}>
          {dailyLoading ? '...' : '↻ Обновить'}
        </button>
      </div>

      <div className="admin-grid-4" style={{ marginBottom: 4 }}>
        <StatCard label="Всего" value={userStats?.total} />
        <StatCard label="Онлайн" value={userStats?.online} color="var(--green)" />
        <StatCard label="Новых сегодня" value={userStats?.newToday} color="var(--purple-l)" />
        <StatCard label="Новых за неделю" value={userStats?.newThisWeek} color="var(--purple-l)" />
        <StatCard label="Активных подписок" value={userStats?.activeSubscribers} color="var(--green)" />
        <StatCard label="Пришли по ссылке" value={userStats?.referralUsers} color="var(--purple-l)" />
      </div>

      <div className="tabs" style={{ marginTop: 12 }}>
        {RANGES.map(r => (
          <button key={r} className={`tab${days === r ? ' active' : ''}`} onClick={() => setDays(r)}>
            {r} дней
          </button>
        ))}
      </div>

      <div className="admin-section-title">Новые пользователи</div>
      <div className="card">
        <SingleBarChart data={daily} dataKey="new_users" name="Новые пользователи" color={CHART_COLORS.messages} />
      </div>

      <div className="admin-section-title">Сообщения</div>
      <div className="card">
        <MessagesChart data={daily} />
      </div>

      <div className="admin-section-title">Подписки</div>
      <div className="card">
        <GrantsChart data={daily} />
      </div>

      {topUsers.length > 0 && (
        <>
          <div className="admin-section-title">Топ активных пользователей</div>
          <div className="card">
            {topUsers.map((u, i) => (
              <RankRow
                key={u.telegram_id}
                rank={i + 1}
                label={u.full_name || 'Без имени'}
                sublabel={u.username ? `@${u.username}` : String(u.telegram_id)}
                value={u.messages}
                max={topUsers[0]?.messages ?? 0}
                onClick={() => navigate(`/a/stats/user/${u.telegram_id}`)}
              />
            ))}
          </div>
        </>
      )}

      <div className="admin-section-title">Статистика по пользователям</div>
      <div className="search-wrap" style={{ marginBottom: 10 }}>
        <input
          className="input"
          placeholder="Имя, @username или Telegram ID…"
          value={qInput}
          onChange={e => setQInput(e.target.value)}
        />
      </div>

      {listLoading ? (
        <div className="loading-center">
          <div className="spinner" />
        </div>
      ) : !list?.items.length ? (
        <div className="empty-state">
          <div className="icon">👥</div>
          <div>Пользователи не найдены</div>
        </div>
      ) : (
        <>
          <div className="card admin-table-wrap">
            <table className="admin-table">
              <tbody>
                {list.items.map(u => (
                  <tr key={u.telegram_id} className="admin-row-clickable" onClick={() => navigate(`/a/stats/user/${u.telegram_id}`)}>
                    <td>
                      <div className="semibold">{u.full_name || 'Без имени'}</div>
                      <div className="text-xs text2">{u.username ? `@${u.username}` : u.telegram_id}</div>
                    </td>
                    <td style={{ textAlign: 'right' }}>
                      <SubBadge status={u.subscription_status} expiresAt={u.subscription_expires_at} />
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          <Paginator page={page} totalPages={list.pages} onChange={setPage} />
        </>
      )}
    </div>
  )
}

function StatCard({ label, value, color }: { label: string; value: number | undefined; color?: string }) {
  return (
    <div className="admin-stat-card">
      <div className="admin-stat-label">{label}</div>
      <div className="admin-stat-value" style={color ? { color } : undefined}>
        {value ?? '—'}
      </div>
    </div>
  )
}
