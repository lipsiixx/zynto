import { getToken } from '@/shared/api'

export function getMediaUrl(fileUniqueId: string): string {
  const token = getToken() || ''
  return `/v1/webapp/media/${encodeURIComponent(fileUniqueId)}?token=${encodeURIComponent(token)}`
}

export function getInstructionPhotoUrl(): string {
  const token = getToken() || ''
  return `/v1/webapp/instruction-photo?token=${encodeURIComponent(token)}`
}
