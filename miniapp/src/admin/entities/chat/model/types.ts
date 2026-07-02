// Соответствует api/schemas.py: MessageOut, MessageCursor, MediaOut.

import type { Pagination } from '@/admin/shared/api/types'

export interface ChatMessage {
  id: number
  messageId: number
  chatId: number
  userId: number
  businessConnectionId: string
  senderId: number | null
  senderName: string | null
  senderUsername: string | null
  isOutgoing: boolean
  messageType: string
  textContent: string | null
  originalText: string | null
  fileUniqueId: string | null
  fileSize: number | null
  mimeType: string | null
  width: number | null
  height: number | null
  durationSeconds: number | null
  isEdited: boolean
  isDeleted: boolean
  editCount: number
  editedAt: string | null
  deletedAt: string | null
  receivedAt: string
}

export interface MessageCursor {
  before: number | null
  hasMore: boolean
}

export interface MessagesListResponse {
  data: ChatMessage[]
  cursor: MessageCursor
}

export interface MediaItem {
  cacheId: number | null
  fileUniqueId: string
  fileType: string | null
  fileSize: number | null
  mimeType: string | null
  contentHash: string | null
  hasLocalFile: boolean
  cachedAt: string | null
  lastUsedAt: string | null
}

export interface MediaListResponse {
  data: MediaItem[]
  pagination: Pagination
}
