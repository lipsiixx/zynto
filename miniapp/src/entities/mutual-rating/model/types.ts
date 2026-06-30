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
