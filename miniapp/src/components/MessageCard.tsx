import type { MessageEvent } from '../types'

function fmtDate(iso: string | null) {
  if (!iso) return ''
  const d = new Date(iso)
  return d.toLocaleDateString('ru', { day: '2-digit', month: 'short' }) +
    ' ' + d.toLocaleTimeString('ru', { hour: '2-digit', minute: '2-digit' })
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

      {event.text_content && (
        <div className="msg-text">{event.text_content}</div>
      )}

      {!event.text_content && !event.file_id && (
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
