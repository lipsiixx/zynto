export interface BroadcastStatus {
  running: boolean
  total: number
  sent: number
  failed: number
  blocked: number
  finished_at: string | null
}

export interface BroadcastStartResponse {
  started: true
  total: number
}

export interface RecipientsCountResponse {
  count: number
}
