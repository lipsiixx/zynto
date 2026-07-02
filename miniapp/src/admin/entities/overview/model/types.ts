// Форма services.stats.collect_stats(db) (services/stats.py) — plain dict,
// отдаётся как есть + добавленный ключ "now". GET /server и GET /proxy
// нового /webapp/admin роутера сознательно НЕ продублированы здесь —
// DashboardPage уже покрывает тот же сервер/прокси через legacy
// entities/stats (reqLegacy), два независимых поллинга одного и того же не нужны.
export interface OverviewOut {
  users_total: number
  users_active_sub: number
  users_new_today: number
  users_new_week: number
  users_new_month: number
  sub_active: number
  sub_lifetime: number
  sub_expired: number
  biz_connected: number
  messages_total: number
  messages_deleted: number
  messages_edited: number
  promo_total: number
  promo_used: number
  now: string
}
