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
