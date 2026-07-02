import { useEffect, useState } from 'react'
import type { NudgeMsgOut, NudgeSettingsOut } from '@/admin/entities/nudge'
import {
  clearNudgeMessageMedia,
  createNudgeMessage,
  deleteNudgeMessage,
  getNudge,
  previewNudgeMessage,
  toggleNudgeMessage,
  updateNudgeMessage,
  updateNudgeSettings,
} from '@/admin/entities/nudge'
import { useAdminCtx, type ToastFn } from '@/admin/shared/lib/AdminCtx'
import { ConfirmButton, Toggle } from '@/admin/shared/ui'

// Порт services/nudge_sender.py + handlers/admin/nudge_settings.py.
export function NudgeTab() {
  const { showToast } = useAdminCtx()
  const [data, setData] = useState<NudgeSettingsOut | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [savingSettings, setSavingSettings] = useState(false)
  const [showNewForm, setShowNewForm] = useState(false)

  const load = () => {
    setLoading(true)
    setError('')
    getNudge()
      .then(setData)
      .catch(e => setError((e as Error).message))
      .finally(() => setLoading(false))
  }

  useEffect(load, [])

  const saveSettings = (patch: Partial<Pick<NudgeSettingsOut, 'enabled' | 'interval_days' | 'grace_days'>>) => {
    setSavingSettings(true)
    updateNudgeSettings(patch)
      .then(setData)
      .catch(e => showToast((e as Error).message, 'error'))
      .finally(() => setSavingSettings(false))
  }

  const replaceMessage = (msg: NudgeMsgOut) => {
    setData(prev => (prev ? { ...prev, messages: prev.messages.map(m => (m.id === msg.id ? msg : m)) } : prev))
  }

  const removeMessage = (id: number) => {
    setData(prev => (prev ? { ...prev, messages: prev.messages.filter(m => m.id !== id) } : prev))
  }

  if (loading) return <div className="loading-center"><div className="spinner" /></div>
  if (error || !data) return <div className="admin-error-msg">{error || 'Ошибка загрузки'}</div>

  return (
    <div>
      <div className="card">
        <div className="admin-form-row">
          <Toggle checked={data.enabled} onChange={v => saveSettings({ enabled: v })} label="Напоминания включены" disabled={savingSettings} />
        </div>
        <div className="admin-grid-2">
          <NumberField
            label="Интервал, дней"
            value={data.interval_days}
            onCommit={v => saveSettings({ interval_days: v })}
            disabled={savingSettings}
          />
          <NumberField
            label="Грейс-период, дней"
            value={data.grace_days}
            onCommit={v => saveSettings({ grace_days: v })}
            disabled={savingSettings}
          />
        </div>
      </div>

      <div className="admin-page-header" style={{ marginTop: 20 }}>
        <span className="semibold">Сообщения</span>
        <button className="admin-icon-btn" onClick={() => setShowNewForm(v => !v)}>
          {showNewForm ? 'Отмена' : '+ Добавить'}
        </button>
      </div>

      {showNewForm && (
        <NudgeMessageForm
          submitLabel="Добавить"
          onSubmit={(text, media) =>
            createNudgeMessage(text, media).then(created => {
              setData(prev => (prev ? { ...prev, messages: [...prev.messages, created] } : prev))
              setShowNewForm(false)
              showToast('Сообщение добавлено', 'success')
            })
          }
        />
      )}

      {!data.messages.length ? (
        <div className="empty-state"><div>Сообщений нет</div></div>
      ) : (
        <div className="admin-card-list">
          {data.messages.map(m => (
            <NudgeMessageCard key={m.id} msg={m} onReplace={replaceMessage} onDelete={removeMessage} showToast={showToast} />
          ))}
        </div>
      )}
    </div>
  )
}

function NumberField({
  label,
  value,
  onCommit,
  disabled,
}: {
  label: string
  value: number
  onCommit: (v: number) => void
  disabled?: boolean
}) {
  const [local, setLocal] = useState(String(value))

  useEffect(() => setLocal(String(value)), [value])

  return (
    <div className="admin-form-row">
      <label className="text-sm text2">{label}</label>
      <input
        className="input"
        type="number"
        min={0}
        value={local}
        disabled={disabled}
        onChange={e => setLocal(e.target.value)}
        onBlur={() => {
          const n = Number(local)
          if (!Number.isNaN(n) && n >= 0 && n !== value) onCommit(n)
          else setLocal(String(value))
        }}
      />
    </div>
  )
}

function NudgeMessageCard({
  msg,
  onReplace,
  onDelete,
  showToast,
}: {
  msg: NudgeMsgOut
  onReplace: (m: NudgeMsgOut) => void
  onDelete: (id: number) => void
  showToast: ToastFn
}) {
  const [editing, setEditing] = useState(false)
  const [busy, setBusy] = useState(false)

  const handleToggle = () => {
    setBusy(true)
    toggleNudgeMessage(msg.id).then(onReplace).catch(e => showToast((e as Error).message, 'error')).finally(() => setBusy(false))
  }

  const handleClearMedia = () => {
    setBusy(true)
    clearNudgeMessageMedia(msg.id).then(onReplace).catch(e => showToast((e as Error).message, 'error')).finally(() => setBusy(false))
  }

  const handlePreview = () => {
    setBusy(true)
    previewNudgeMessage(msg.id)
      .then(() => showToast('Отправлено тебе в чат с ботом', 'success'))
      .catch(e => showToast((e as Error).message, 'error'))
      .finally(() => setBusy(false))
  }

  const handleDelete = () => {
    setBusy(true)
    deleteNudgeMessage(msg.id)
      .then(() => {
        onDelete(msg.id)
        showToast('Сообщение удалено', 'success')
      })
      .catch(e => showToast((e as Error).message, 'error'))
      .finally(() => setBusy(false))
  }

  if (editing) {
    return (
      <NudgeMessageForm
        submitLabel="Сохранить"
        initialText={msg.text ?? ''}
        onSubmit={(text, media) =>
          updateNudgeMessage(msg.id, text, media).then(updated => {
            onReplace(updated)
            setEditing(false)
            showToast('Сообщение обновлено', 'success')
          })
        }
        onCancel={() => setEditing(false)}
      />
    )
  }

  return (
    <div className="card">
      <div className="row" style={{ justifyContent: 'space-between', alignItems: 'flex-start' }}>
        <div style={{ minWidth: 0 }}>
          <div className="text-sm" style={{ whiteSpace: 'pre-wrap', wordBreak: 'break-word' }}>
            {msg.text || <span className="text2">без текста</span>}
          </div>
          <div className="row gap-8 text-xs text2" style={{ marginTop: 6 }}>
            {msg.has_media && <span className="badge badge-purple">{msg.media_type === 'video' ? '🎬 видео' : '🖼 фото'}</span>}
            <span className={`badge ${msg.is_active ? 'badge-green' : 'badge-gray'}`}>{msg.is_active ? 'Активно' : 'Выключено'}</span>
          </div>
        </div>
      </div>
      <div className="row gap-8" style={{ flexWrap: 'wrap', marginTop: 10 }}>
        <button className="admin-icon-btn" onClick={() => setEditing(true)} disabled={busy}>Редактировать</button>
        <button className="admin-icon-btn" onClick={handleToggle} disabled={busy}>{msg.is_active ? 'Выключить' : 'Включить'}</button>
        <button className="admin-icon-btn" onClick={handlePreview} disabled={busy}>Просмотр</button>
        {msg.has_media && (
          <button className="admin-icon-btn" onClick={handleClearMedia} disabled={busy}>Убрать медиа</button>
        )}
        <ConfirmButton label="Удалить" onConfirm={handleDelete} disabled={busy} />
      </div>
    </div>
  )
}

function NudgeMessageForm({
  submitLabel,
  initialText = '',
  onSubmit,
  onCancel,
}: {
  submitLabel: string
  initialText?: string
  onSubmit: (text: string, media: File | null) => Promise<unknown>
  onCancel?: () => void
}) {
  const [text, setText] = useState(initialText)
  const [media, setMedia] = useState<File | null>(null)
  const [submitting, setSubmitting] = useState(false)
  const [error, setError] = useState('')

  const handleSubmit = async () => {
    setError('')
    if (!text.trim() && !media) {
      setError('Укажи текст или прикрепи медиа')
      return
    }
    setSubmitting(true)
    try {
      await onSubmit(text.trim(), media)
    } catch (e) {
      setError((e as Error).message)
    } finally {
      setSubmitting(false)
    }
  }

  return (
    <div className="card admin-form">
      <div className="admin-form-row">
        <label className="text-sm text2">Текст</label>
        <textarea className="input" rows={3} value={text} onChange={e => setText(e.target.value)} />
      </div>
      <div className="admin-form-row">
        <label className="text-sm text2">Медиа (фото/видео, заменит текущее)</label>
        <input type="file" accept="image/*,video/*" onChange={e => setMedia(e.target.files?.[0] ?? null)} />
      </div>
      {error && <div className="admin-error-msg">{error}</div>}
      <div className="row gap-8">
        <button className="btn btn-primary" onClick={handleSubmit} disabled={submitting}>
          {submitting ? 'Сохранение…' : submitLabel}
        </button>
        {onCancel && (
          <button className="btn btn-secondary" style={{ width: 'auto' }} onClick={onCancel}>Отмена</button>
        )}
      </div>
    </div>
  )
}
