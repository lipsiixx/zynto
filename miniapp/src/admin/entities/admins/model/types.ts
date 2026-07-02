export interface AdminOut {
  telegram_id: number
  username: string | null
  full_name: string | null
  added_at: string
}

export interface AdminListResponse {
  items: AdminOut[]
}
