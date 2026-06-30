import { req } from '@/shared/api'
import type { MutualRating } from '../model/types'

export async function getMutualRating(chatId: number): Promise<MutualRating> {
  return req('GET', `/contacts/${chatId}/mutual-rating`)
}

export async function getMRPending(): Promise<{ data: MutualRating[]; total: number }> {
  return req('GET', '/mutual-rating/pending')
}

export async function sendMRRequest(chatId: number, myScore: number): Promise<MutualRating> {
  return req('POST', `/contacts/${chatId}/mutual-rating`, { my_score: myScore })
}

export async function acceptMR(chatId: number, score: number): Promise<MutualRating> {
  return req('POST', `/contacts/${chatId}/mutual-rating/accept`, { score })
}

export async function declineMR(chatId: number): Promise<MutualRating> {
  return req('POST', `/contacts/${chatId}/mutual-rating/decline`)
}

export async function cancelMR(chatId: number): Promise<MutualRating> {
  return req('DELETE', `/contacts/${chatId}/mutual-rating`)
}
