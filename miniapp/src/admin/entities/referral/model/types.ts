export interface ReferralRewardItem {
  referrer_id: number
  referrer_name: string | null
  referred_name: string | null
  days_granted: number
  created_at: string
}

export interface ReferralOut {
  enabled: boolean
  reward_days: number
  rewards: ReferralRewardItem[]
  total_rewards: number
}

export interface ReferralSettingsOut {
  enabled: boolean
  reward_days: number
}

export interface ReferralPayload {
  enabled?: boolean
  reward_days?: number
}
