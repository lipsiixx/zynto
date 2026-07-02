export type NudgeMediaType = 'photo' | 'video' | null

export interface NudgeMsgOut {
  id: number
  text: string | null
  media_type: NudgeMediaType
  has_media: boolean
  is_active: boolean
}

export interface NudgeSettingsOut {
  enabled: boolean
  interval_days: number
  grace_days: number
  messages: NudgeMsgOut[]
}

export interface NudgeSettingsPayload {
  enabled?: boolean
  interval_days?: number
  grace_days?: number
}
