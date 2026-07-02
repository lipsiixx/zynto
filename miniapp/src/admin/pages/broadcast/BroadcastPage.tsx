import { useCallback, useEffect, useRef, useState } from 'react'
import type { BroadcastStatus } from '@/admin/entities/broadcast'
import { getBroadcastRecipientsCount, getBroadcastStatus, startBroadcast } from '@/admin/entities/broadcast'
import { useAdminCtx } from '@/admin/shared/lib/AdminCtx'
import { fmtDateTime } from '@/admin/shared/lib/format'

const POLL_MS = 2000

// Порт handlers/admin/broadcast.py cb_confirm — прогресс идёт через
// services/broadcast_job.py (фоновая задача на бэкенде), здесь только опрос.
export function BroadcastPage() {
  const { showToast } = useAdminCtx()
  const [text, setText] = useState('')
  const [photo, setPhoto] = useState<File | null>(null)
  const [photoPreview, setPhotoPreview] = useState<string | null>(null)
  const [recipients, setRecipients] = useState<number | null>(null)
  const [status, setStatus] = useState<BroadcastStatus | null>(null)
  const [starting, setStarting] = useState(false)
  const [error, setError] = useState('')
  const intervalRef = useRef<ReturnType<typeof setInterval> | null>(null)

  const loadStatus = useCallback(() => {
    getBroadcastStatus()
      .then(s => setStatus(s))
      .catch(() => {})
  }, [])

  useEffect(() => {
    getBroadcastRecipientsCount()
      .then(r => setRecipients(r.count))
      .catch(() => {})
    loadStatus()
  }, [loadStatus])

  useEffect(() => {
    if (status?.running && !intervalRef.current) {
      intervalRef.current = setInterval(loadStatus, POLL_MS)
    }
    if (!status?.running && intervalRef.current) {
      clearInterval(intervalRef.current)
      intervalRef.current = null
    }
    return () => {
      if (intervalRef.current) {
        clearInterval(intervalRef.current)
        intervalRef.current = null
      }
    }
  }, [status?.running, loadStatus])

  const handlePhotoChange = (file: File | null) => {
    setPhoto(file)
    if (photoPreview) URL.revokeObjectURL(photoPreview)
    setPhotoPreview(file ? URL.createObjectURL(file) : null)
  }

  const handleStart = async () => {
    if (!text.trim()) {
      setError('Введи текст рассылки')
      return
    }
    setError('')
    setStarting(true)
    try {
      const res = await startBroadcast(text, photo)
      showToast(`Рассылка запущена: ${res.total} получателей`, 'success')
      loadStatus()
    } catch (e) {
      const msg = (e as Error).message
      setError(msg === 'already_running' ? 'Рассылка уже выполняется' : msg)
    } finally {
      setStarting(false)
    }
  }

  const running = status?.running ?? false
  const pct = status && status.total ? Math.min(100, ((status.sent + status.failed) / status.total) * 100) : 0

  return (
    <div className="admin-page">
      <div className="admin-page-header">
        <h1>Рассылка</h1>
      </div>

      <div className="card admin-form">
        <div className="admin-form-row">
          <label className="text-sm text2">Текст (HTML-разметка Telegram)</label>
          <textarea
            className="input"
            rows={6}
            placeholder="<b>Привет!</b> Текст рассылки…"
            value={text}
            onChange={e => setText(e.target.value)}
            disabled={running}
          />
        </div>

        <div className="admin-form-row">
          <label className="text-sm text2">Фото (необязательно)</label>
          <input
            type="file"
            accept="image/*"
            disabled={running}
            onChange={e => handlePhotoChange(e.target.files?.[0] ?? null)}
          />
          {photoPreview && (
            <div style={{ marginTop: 8 }}>
              <img src={photoPreview} alt="" style={{ maxWidth: '100%', maxHeight: 200, borderRadius: 10 }} />
              <button className="admin-icon-btn" style={{ marginTop: 6 }} onClick={() => handlePhotoChange(null)} disabled={running}>
                Убрать фото
              </button>
            </div>
          )}
        </div>

        <div className="text-sm text2" style={{ marginBottom: 12 }}>
          Получателей: {recipients ?? '…'}
        </div>

        {error && <div className="admin-error-msg">{error}</div>}

        <button className="btn btn-primary" onClick={handleStart} disabled={starting || running}>
          {running ? 'Рассылка идёт…' : starting ? 'Запуск…' : 'Отправить'}
        </button>
      </div>

      {status && (status.running || status.total > 0) && (
        <div className="card">
          <div className="row" style={{ justifyContent: 'space-between', marginBottom: 8 }}>
            <span className="semibold">{status.running ? 'Идёт рассылка' : 'Последняя рассылка'}</span>
            {status.running && <div className="spinner" style={{ width: 16, height: 16, borderWidth: 2 }} />}
          </div>
          <div className="admin-progress-bar" style={{ marginBottom: 8 }}>
            <div className="admin-progress-fill" style={{ width: `${pct}%` }} />
          </div>
          <div className="admin-grid-4">
            <MiniStat label="Всего" value={status.total} />
            <MiniStat label="Отправлено" value={status.sent} />
            <MiniStat label="Ошибок" value={status.failed} />
            <MiniStat label="Заблокировали" value={status.blocked} />
          </div>
          {status.finished_at && (
            <div className="text-sm text2" style={{ marginTop: 10 }}>Завершено: {fmtDateTime(status.finished_at)}</div>
          )}
        </div>
      )}
    </div>
  )
}

function MiniStat({ label, value }: { label: string; value: number }) {
  return (
    <div>
      <div className="text-xs text2">{label}</div>
      <div className="bold" style={{ fontSize: 16 }}>{value}</div>
    </div>
  )
}
