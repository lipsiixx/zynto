import { req, reqForm } from '@/admin/shared/api/adminApi'
import type { NudgeMsgOut, NudgeSettingsOut, NudgeSettingsPayload } from '../model/types'

export function getNudge(): Promise<NudgeSettingsOut> {
  return req('GET', '/nudge')
}

export function updateNudgeSettings(payload: NudgeSettingsPayload): Promise<NudgeSettingsOut> {
  return req('PUT', '/nudge/settings', payload)
}

/** text и/или media — хотя бы одно обязательно. */
function buildNudgeForm(text: string, media: File | null): FormData {
  const form = new FormData()
  if (text) form.set('text', text)
  if (media) form.set('media', media)
  return form
}

export function createNudgeMessage(text: string, media: File | null): Promise<NudgeMsgOut> {
  return reqForm('POST', '/nudge/messages', buildNudgeForm(text, media))
}

export function updateNudgeMessage(id: number, text: string, media: File | null): Promise<NudgeMsgOut> {
  return reqForm('PATCH', `/nudge/messages/${id}`, buildNudgeForm(text, media))
}

export function toggleNudgeMessage(id: number): Promise<NudgeMsgOut> {
  return req('POST', `/nudge/messages/${id}/toggle`)
}

export function clearNudgeMessageMedia(id: number): Promise<NudgeMsgOut> {
  return req('POST', `/nudge/messages/${id}/clear-media`)
}

export function deleteNudgeMessage(id: number): Promise<{ ok: true }> {
  return req('DELETE', `/nudge/messages/${id}`)
}

/** Отправляет сообщение админу в чат ботом — просмотр медиа отдельным URL не поддержан. */
export function previewNudgeMessage(id: number): Promise<{ ok: true }> {
  return req('POST', `/nudge/messages/${id}/preview`)
}
