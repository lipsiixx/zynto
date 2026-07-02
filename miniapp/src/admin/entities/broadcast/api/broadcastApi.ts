import { req, reqForm } from '@/admin/shared/api/adminApi'
import type { BroadcastStartResponse, BroadcastStatus, RecipientsCountResponse } from '../model/types'

export function getBroadcastStatus(): Promise<BroadcastStatus> {
  return req('GET', '/broadcast/status')
}

export function getBroadcastRecipientsCount(): Promise<RecipientsCountResponse> {
  return req('GET', '/broadcast/recipients-count')
}

/** 409 "already_running" — уже идёт другая рассылка (одна задача за раз). */
export function startBroadcast(text: string, photo: File | null): Promise<BroadcastStartResponse> {
  const form = new FormData()
  form.set('text', text)
  if (photo) form.set('photo', photo)
  return reqForm('POST', '/broadcast', form)
}
