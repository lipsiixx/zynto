import type { SubscriptionStatus } from '@/admin/entities/user'
import { fmtDate } from '@/admin/shared/lib/format'

interface Props {
  status: SubscriptionStatus | string
  expiresAt: string | null
}

// Порт SubBadge из C:\projects\admin-panel\src\components\Badge.jsx — адаптирован
// под реальный набор статусов этого проекта: {none, active, lifetime, expired}
// (см. CLAUDE.md), "trial" в этом бэкенде не существует.
export function SubBadge({ status, expiresAt }: Props) {
  if (status === 'active') {
    const label = expiresAt ? `до ${fmtDate(expiresAt)}` : 'Активна'
    return <span className="badge badge-green">● {label}</span>
  }
  if (status === 'lifetime') {
    return <span className="badge badge-purple">∞ Навсегда</span>
  }
  if (status === 'expired') {
    const label = expiresAt ? `Истекла ${fmtDate(expiresAt)}` : 'Истекла'
    return <span className="badge badge-red">{label}</span>
  }
  return <span className="badge badge-gray">Нет</span>
}
