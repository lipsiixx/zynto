import { useEffect, useState } from 'react'
import type { CourseOut } from '@/admin/entities/course'
import { getCourse, updateCourse, uploadCourseVideo } from '@/admin/entities/course'
import { useAdminCtx } from '@/admin/shared/lib/AdminCtx'
import { Toggle } from '@/admin/shared/ui'

// Порт настройки курса — видео хранится как Telegram file_id (см. CLAUDE.md,
// раздел "Курс"), здесь только текстовые настройки + загрузка нового видео.
export function CourseTab() {
  const { showToast } = useAdminCtx()
  const [data, setData] = useState<CourseOut | null>(null)
  const [caption, setCaption] = useState('')
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [saving, setSaving] = useState(false)
  const [video, setVideo] = useState<File | null>(null)
  const [uploading, setUploading] = useState(false)

  useEffect(() => {
    getCourse()
      .then(d => {
        setData(d)
        setCaption(d.caption)
      })
      .catch(e => setError((e as Error).message))
      .finally(() => setLoading(false))
  }, [])

  const handleSave = () => {
    if (!data) return
    setSaving(true)
    updateCourse({ enabled: data.enabled, caption })
      .then(d => {
        setData(d)
        setCaption(d.caption)
        showToast('Сохранено', 'success')
      })
      .catch(e => showToast((e as Error).message, 'error'))
      .finally(() => setSaving(false))
  }

  const handleToggleEnabled = (enabled: boolean) => {
    if (!data) return
    setData({ ...data, enabled })
    updateCourse({ enabled })
      .then(setData)
      .catch(e => {
        showToast((e as Error).message, 'error')
        setData(prev => (prev ? { ...prev, enabled: !enabled } : prev))
      })
  }

  const handleUploadVideo = () => {
    if (!video) return
    setUploading(true)
    uploadCourseVideo(video)
      .then(() => {
        showToast('Видео загружено', 'success')
        setVideo(null)
        return getCourse().then(setData)
      })
      .catch(e => showToast((e as Error).message, 'error'))
      .finally(() => setUploading(false))
  }

  if (loading) return <div className="loading-center"><div className="spinner" /></div>
  if (error || !data) return <div className="admin-error-msg">{error || 'Ошибка загрузки'}</div>

  return (
    <div>
      <div className="card">
        <div className="admin-form-row">
          <Toggle checked={data.enabled} onChange={handleToggleEnabled} label="Курс доступен пользователям" />
        </div>
        <div className="admin-form-row">
          <label className="text-sm text2">Подпись к видео</label>
          <textarea className="input" rows={4} value={caption} onChange={e => setCaption(e.target.value)} />
        </div>
        <button className="btn btn-primary" onClick={handleSave} disabled={saving}>
          {saving ? 'Сохранение…' : 'Сохранить'}
        </button>
      </div>

      <div className="card">
        <div className="text-sm" style={{ marginBottom: 10 }}>
          Видео: {data.has_video ? <span style={{ color: 'var(--green)' }}>загружено ✓</span> : <span className="text2">не загружено</span>}
        </div>
        <div className="admin-form-row">
          <label className="text-sm text2">Загрузить новое видео</label>
          <input type="file" accept="video/*" onChange={e => setVideo(e.target.files?.[0] ?? null)} />
        </div>
        <button className="btn btn-secondary" onClick={handleUploadVideo} disabled={!video || uploading} style={{ width: 'auto' }}>
          {uploading ? 'Загрузка…' : 'Загрузить видео'}
        </button>
      </div>
    </div>
  )
}
