import { useEffect, useState } from 'react'
import type { CleanupOut } from '@/admin/entities/cleanup'
import { getCleanup, updateCleanup } from '@/admin/entities/cleanup'
import { useAdminCtx } from '@/admin/shared/lib/AdminCtx'

// Порт handlers/admin/cleanup.py — только суперадмин, гарда уже на уровне
// SettingsPage (вкладка не рендерится без flags.includes('superadmin')), но
// бэкенд всё равно ответит 404 не-суперадмину — это инвариант скрытности.
export function CleanupTab() {
  const { showToast } = useAdminCtx()
  const [data, setData] = useState<CleanupOut | null>(null)
  const [textDays, setTextDays] = useState('0')
  const [mediaDays, setMediaDays] = useState('0')
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [saving, setSaving] = useState(false)

  useEffect(() => {
    getCleanup()
      .then(d => {
        setData(d)
        setTextDays(String(d.text_retention_days))
        setMediaDays(String(d.media_retention_days))
      })
      .catch(e => setError((e as Error).message))
      .finally(() => setLoading(false))
  }, [])

  const handleSave = () => {
    const text = Number(textDays)
    const media = Number(mediaDays)
    if (Number.isNaN(text) || text < 0 || Number.isNaN(media) || media < 0) {
      showToast('Значения должны быть ≥ 0', 'error')
      return
    }
    setSaving(true)
    updateCleanup({ text_retention_days: text, media_retention_days: media })
      .then(d => {
        setData(d)
        showToast('Сохранено', 'success')
      })
      .catch(e => showToast((e as Error).message, 'error'))
      .finally(() => setSaving(false))
  }

  if (loading) return <div className="loading-center"><div className="spinner" /></div>
  if (error || !data) return <div className="admin-error-msg">{error || 'Ошибка загрузки'}</div>

  return (
    <div className="card">
      <div className="text-sm text2" style={{ marginBottom: 12 }}>0 = хранить вечно</div>
      <div className="admin-form-row">
        <label className="text-sm text2">Хранение текстов, дней</label>
        <input className="input" type="number" min={0} value={textDays} onChange={e => setTextDays(e.target.value)} />
      </div>
      <div className="admin-form-row">
        <label className="text-sm text2">Хранение медиафайлов, дней</label>
        <input className="input" type="number" min={0} value={mediaDays} onChange={e => setMediaDays(e.target.value)} />
      </div>
      <button className="btn btn-primary" onClick={handleSave} disabled={saving}>
        {saving ? 'Сохранение…' : 'Сохранить'}
      </button>
    </div>
  )
}
