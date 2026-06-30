import { req } from '@/shared/api'
import type { ReferralStats } from '../model/types'

export async function getReferral(): Promise<ReferralStats> {
  return req('GET', '/referral')
}
