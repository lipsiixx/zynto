import { useState } from 'react'
import type { MessageEvent } from '../types'
import { getMediaUrl } from '../api'

function fmtDate(iso: string | null) {
  if (!iso) return ''
  const d = new Date(iso)
  return d.toLocaleDateString('ru', { day: '2-digit', month: 'short' }) +
    ' ' + d.toLocaleTimeString('ru', { hour: '2-digit', minute: '2-digit' })
}

function fmtDuration(sec: number | null) {
  if (!sec) return ''
  const m = Math.floor(sec / 60)
  const s = sec % 60
  return `${m}:${String(s).padStart(2, '0')}`
}

const TYPE_LABEL: Record<string, string> = {
  text: 'Текст',
  photo: '📷 Фото',
  video: '🎥 Видео',
  audio: '🎵 Аудио',
  voice: '🎤 Голос',
  document: '📄 Файл',
  sticker: '🎭 Стикер',
  video_note: '⭕ Видео-кружок',
  animation: '🎞 GIF',
}

const MEDIA_TYPES = new Set(['photo', 'video', 'audio', 'voice', 'video_note', 'animation', 'sticker'])

function MediaBlock({ event }: { event: MessageEvent }) {
  const [expanded, setExpanded] = useState(false)
  const [errored, setErrored] = useState(false)

  if (!event.file_unique_id || !MEDIA_TYPES.has(event.message_type)) return null

  const url = getMediaUrl(event.file_unique_id)
  const type = event.message_type

  if (errored) {
    return (
      <div className="media-unavailable">
        <span>⚠️ Файл недоступен</span>
      </div>
    )
  }

  if (type === 'photo') {
    return (
      <div className="media-block" onClick={() => setExpanded(e => !e)}>
        <img
          src={url}
          alt="фото"
          className={`media-img${expanded ? ' media-img-full' : ''}`}
          onError={() => setErrored(true)}
          loading="lazy"
        />
      </div>
    )
  }

  if (type === 'video' || type === 'animation') {
    return (
      <div className="media-block">
        <video
          src={url}
          controls
          className="media-video"
          preload="metadata"
          onError={() => setErrored(true)}
          playsInline
        />
        {event.duration_seconds ? (
          <div className="media-meta">{fmtDuration(event.duration_seconds)}</div>
        ) : null}
      </div>
    )
  }

  if (type === 'video_note') {
    return (
      <div className="media-block">
        <video
          src={url}
          controls
          className="media-video media-video-circle"
          preload="metadata"
          onError={() => setErrored(true)}
          playsInline
        />
        {event.duration_seconds ? (
          <div className="media-meta">{fmtDuration(event.duration_seconds)}</div>
        ) : null}
      </div>
    )
  }

  if (type === 'audio' || type === 'voice') {
    return (
      <div className="media-block">
        <audio
          src={url}
          controls
          className="media-audio"
          preload="metadata"
          onError={() => setErrored(true)}
        />
        {event.duration_seconds ? (
          <div className="media-meta">{fmtDuration(event.duration_seconds)}</div>
        ) : null}
      </div>
    )
  }

  // sticker — показываем как картинку (webp)
  if (type === 'sticker') {
    return (
      <div className="media-block">
        <img
          src={url}
          alt="стикер"
          className="media-sticker"
          onError={() => setErrored(true)}
          loading="lazy"
        />
      </div>
    )
  }

  return null
}

export function MessageCard({ event }: { event: MessageEvent }) {
  const classes = ['msg-card']
  if (event.is_deleted) classes.push('deleted')
  else if (event.is_edited) classes.push('edited')
  if (event.is_outgoing) classes.push('outgoing')

  const when = event.is_deleted
    ? fmtDate(event.deleted_at)
    : event.is_edited
      ? fmtDate(event.edited_at)
      : fmtDate(event.received_at)

  const typeLabel = TYPE_LABEL[event.message_type] || event.message_type
  const hasMedia = !!event.file_unique_id && MEDIA_TYPES.has(event.message_type)

  return (
    <div className={classes.join(' ')}>
      <div className="msg-meta">
        {event.is_deleted && <span className="msg-tag del">Удалено</span>}
        {event.is_edited && !event.is_deleted && <span className="msg-tag edit">Изменено</span>}
        {event.is_outgoing && <span className="msg-tag out">Исходящее</span>}
        {event.message_type !== 'text' && (
          <span style={{ color: 'var(--text2)' }}>{typeLabel}</span>
        )}
        <span style={{ marginLeft: 'auto' }}>{when}</span>
      </div>

      <MediaBlock event={event} />

      {event.text_content && (
        <div className="msg-text">{event.text_content}</div>
      )}

      {!event.text_content && !hasMedia && (
        <div className="msg-text" style={{ color: 'var(--text3)', fontStyle: 'italic' }}>
          {event.is_deleted ? '[Удалено без текста]' : typeLabel}
        </div>
      )}

      {event.is_edited && event.original_text && (
        <div className="msg-original">
          Было: {event.original_text}
        </div>
      )}
    </div>
  )
}
