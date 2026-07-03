// Профиль пользователя из /v1/webapp/admin/users/* — НЕ путать с
// entities/user (legacy /v1/users мониторинга, camelCase). Папка называется
// manage-user, чтобы не конфликтовать по имени с существующим entities/user.
export type ManageUserSubStatus = 'none' | 'active' | 'lifetime' | 'expired'

export interface UserProfileOut {
  telegram_id: number
  username: string | null
  full_name: string | null
  created_at: string
  last_active_at: string | null
  subscription_status: ManageUserSubStatus
  subscription_expires_at: string | null
  is_banned: boolean
  ban_reason: string | null
  business_connected: boolean
  messages_count: number
}

export interface UserSubscriptionItem {
  payment_method: string
  expires_at: string | null
  created_at: string
}

export interface UserSubscriptionsResponse {
  items: UserSubscriptionItem[]
}

/** GET /users/{tid}/stats */
export interface UserStatsOut {
  summary: {
    contacts: number
    total_messages: number
    deleted: number
    edited: number
  }
  referral: {
    total_referred: number
    total_converted: number
    total_rewards: number
    total_days_earned: number
  }
  payments: {
    total: number
    by_method: Record<string, number>
  }
}

export type SubscriptionAction = 'days' | 'lifetime' | 'revoke'

/** GET /users — лёгкий ряд списка (полный профиль тянется по клику) */
export interface ManagedUserListItem {
  telegram_id: number
  username: string | null
  full_name: string | null
  subscription_status: ManageUserSubStatus
  subscription_expires_at: string | null
  is_banned: boolean
  last_active_at: string | null
  created_at: string
}

export interface ManagedUsersListResponse {
  items: ManagedUserListItem[]
  total: number
  page: number
  pages: number
}
