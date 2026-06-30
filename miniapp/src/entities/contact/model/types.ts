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

export interface DayStat {
  day: string
  total: number
  deleted: number
  edited: number
}
