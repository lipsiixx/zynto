import { req } from '@/shared/api'

export async function setHistoryRetention(
  hours: number,
): Promise<{ history_retention_hours: number }> {
  return req('PUT', '/settings/history-retention', { hours })
}
