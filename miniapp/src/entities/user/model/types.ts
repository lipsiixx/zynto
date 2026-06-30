export interface Subscription {
  status: 'none' | 'active' | 'lifetime' | 'expired'
  has_active: boolean
  expires_at: string | null
  started_at: string | null
}

export interface Summary {
  contacts: number
  total_messages: number
  deleted: number
  edited: number
}

export interface Me {
  telegram_id: number
  full_name: string
  username: string | null
  avatar_file_id: string | null
  subscription: Subscription
  monitoring_active: boolean
  summary: Summary
}
