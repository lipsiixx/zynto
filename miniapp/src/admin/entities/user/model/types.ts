// Типы соответствуют camelCase-полям Pydantic-схем api/schemas.py (UserOut,
// ChatOut, ContactOut, UserStatsOut) — в отличие от основного приложения
// (entities/*), где backend отдаёт snake_case через /v1/webapp/*.

export type { Pagination } from '@/admin/shared/api/types'
import type { Pagination } from '@/admin/shared/api/types'

export type SubscriptionStatus = 'none' | 'active' | 'lifetime' | 'expired'

export interface AdminUser {
  id: number
  telegramId: number
  username: string | null
  fullName: string
  languageCode: string
  phone: string | null
  avatarFileUniqueId: string | null
  subscriptionStatus: SubscriptionStatus
  subscriptionExpiresAt: string | null
  isBanned: boolean
  isBlocked: boolean
  lastActiveAt: string
  isOnline: boolean
  createdAt: string
}

export interface UsersListResponse {
  data: AdminUser[]
  pagination: Pagination
}

export interface ChatSummary {
  chatId: number
  title: string | null
  userId: number
  messageCount: number
  deletedCount: number
  editedCount: number
  lastMessageAt: string | null
}

export interface ChatsListResponse {
  data: ChatSummary[]
  pagination: Pagination
}

export interface UserContact {
  senderId: number | null
  senderName: string | null
  senderUsername: string | null
  messageCount: number
  sharedChatsCount: number
}

export interface UserContactsResponse {
  data: UserContact[]
  pagination: Pagination
}

export interface UserStats {
  userId: number
  telegramId: number
  totalMessages: number
  deletedMessages: number
  editedMessages: number
  totalMedia: number
  totalChats: number
  firstMessageAt: string | null
  lastMessageAt: string | null
  isOnline: boolean
}
