import { req } from '@/shared/api'

export async function clearHistory(): Promise<{ history_cleared_at: string }> {
  return req('POST', '/settings/history-clear')
}
