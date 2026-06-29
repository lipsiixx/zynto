export interface Subscription {
  status: 'none' | 'active' | 'lifetime' | 'expired'
  has_active: boolean
  expires_at: string | null
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

export interface Contact {
  chat_id: number
  chat_title: string | null
  total_messages: number
  deleted_count: number
  edited_count: number
  auto_score: number
  manual_score: number | null
  trust_score: number
  last_message_at: string | null
}

export interface MessageEvent {
  id: number
  message_id: number
  is_outgoing: boolean
  is_deleted: boolean
  is_edited: boolean
  message_type: string
  text_content: string | null
  original_text: string | null
  file_id: string | null
  file_unique_id: string | null
  mime_type: string | null
  duration_seconds: number | null
  width: number | null
  height: number | null
  received_at: string | null
  deleted_at: string | null
  edited_at: string | null
}

export interface MutualRating {
  id?: number
  status: 'none' | 'pending' | 'active' | 'declined' | 'cancelled'
  direction?: 'outgoing' | 'incoming'
  requester_id?: number
  target_id?: number
  requester_score?: number | null
  target_score?: number | null
  mutual_score?: number | null
  target_in_bot?: boolean
  target_connected?: boolean
  requester_name?: string
  created_at?: string | null
}

export interface DayStat {
  day: string
  total: number
  deleted: number
  edited: number
}

export interface ReferralStats {
  link: string
  reward_days: number
  enabled: boolean
  total_referred: number
  total_converted: number
  total_rewards: number
  total_days_earned: number
}

export interface Tariff {
  id: number
  name: string
  description: string | null
  duration_days: number | null
  price_stars: number
}
