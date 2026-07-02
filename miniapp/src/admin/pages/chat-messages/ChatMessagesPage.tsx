import { useCallback, useEffect, useRef, useState, type ReactElement, type SyntheticEvent } from 'react'
import { useNavigate, useParams, useSearchParams } from 'react-router-dom'
import type { ChatMessage, MediaItem, MediaListResponse } from '@/admin/entities/chat'
import { getChatMedia, getChatMessages } from '@/admin/entities/chat'
import { mediaUrl } from '@/admin/shared/api/adminApi'
import { bytes, fmtTime, MSG_TYPE_ICON } from '@/admin/shared/lib/format'
import { Paginator } from '@/admin/shared/ui'

const LIMIT = 50

type Lightbox = { type: 'image' | 'video' | 'audio'; url: string } | null

// Порт ChatMessages.jsx (C:\projects\admin-panel\src\pages\ChatMessages.jsx).
// userId в маршруте — внутренний users.id (см. api/routers/chats.py: query
// user_id, а не telegram_id), title чата передаётся через ?title=, т.к. общий
// роутер AdminApp.tsx не хранит состояние между страницами.
export function ChatMessagesPage() {
  const { userId, chatId } = useParams<{ userId: string; chatId: string }>()
  const [sp] = useSearchParams()
  const navigate = useNavigate()
  const uid = Number(userId)
  const cid = Number(chatId)
  const chatTitle = sp.get('title') || chatId

  const [tab, setTab] = useState<'messages' | 'media'>('messages')

  const [messages, setMessages] = useState<ChatMessage[]>([])
  const [hasMore, setHasMore] = useState(false)
  const [oldestId, setOldestId] = useState<number | null>(null)
  const [loadingMsgs, setLoadingMsgs] = useState(false)
  const [initDone, setInitDone] = useState(false)
  const [msgError, setMsgError] = useState('')

  const [mediaPage, setMediaPage] = useState(1)
  const [mimeFilter, setMimeFilter] = useState('')
  const [media, setMedia] = useState<MediaListResponse | null>(null)
  const [loadingMedia, setLoadingMedia] = useState(false)
  const [mediaError, setMediaError] = useState('')

  const [lightbox, setLightbox] = useState<Lightbox>(null)

  const bottomRef = useRef<HTMLDivElement>(null)
  const listRef = useRef<HTMLDivElement>(null)

  const loadMessages = useCallback(
    async (before: number | null = null) => {
      setLoadingMsgs(true)
      setMsgError('')
      try {
        const data = await getChatMessages(cid, { userId: uid, before: before ?? undefined, limit: LIMIT })
        const chunk = data.data // API: новые → старые
        const reversed = [...chunk].reverse() // отображаем: старые → новые
        setMessages(prev => (before ? [...reversed, ...prev] : reversed))
        setHasMore(data.cursor.hasMore)
        if (chunk.length) setOldestId(chunk[chunk.length - 1].id)
      } catch (e) {
        setMsgError(`Ошибка: ${(e as Error).message}`)
      } finally {
        setLoadingMsgs(false)
        setInitDone(true)
      }
    },
    [cid, uid],
  )

  const loadMedia = useCallback(async () => {
    setLoadingMedia(true)
    setMediaError('')
    try {
      const data = await getChatMedia(cid, { userId: uid, mimeType: mimeFilter || undefined, page: mediaPage, limit: 30 })
      setMedia(data)
    } catch (e) {
      setMediaError(`Ошибка: ${(e as Error).message}`)
    } finally {
      setLoadingMedia(false)
    }
  }, [cid, uid, mimeFilter, mediaPage])

  useEffect(() => {
    setMessages([])
    setInitDone(false)
    loadMessages()
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [cid, uid])

  useEffect(() => {
    if (initDone && !hasMore && bottomRef.current) {
      bottomRef.current.scrollIntoView({ behavior: 'auto' })
    }
  }, [initDone, hasMore])

  useEffect(() => {
    if (tab === 'media') loadMedia()
  }, [tab, loadMedia])

  const loadOlder = async () => {
    const el = listRef.current
    const prevH = el?.scrollHeight || 0
    await loadMessages(oldestId)
    if (el) el.scrollTop += el.scrollHeight - prevH
  }

  useEffect(() => {
    const h = (e: KeyboardEvent) => {
      if (e.key === 'Escape') setLightbox(null)
    }
    window.addEventListener('keydown', h)
    return () => window.removeEventListener('keydown', h)
  }, [])

  return (
    <div className="admin-page admin-chat-page">
      <div className="admin-chat-header">
        <div className="admin-breadcrumb">
          <span className="admin-breadcrumb-link" onClick={() => navigate('/a/users')}>
            Пользователи
          </span>
          <span className="admin-breadcrumb-sep">/</span>
          <span className="admin-breadcrumb-link" onClick={() => navigate(`/a/users/${uid}`)}>
            Пользователь #{uid}
          </span>
          <span className="admin-breadcrumb-sep">/</span>
          <span>{chatTitle}</span>
        </div>
        <div className="row gap-8">
          <span className="semibold">{chatTitle || `Чат ${cid}`}</span>
          <span className="admin-mono text2 text-xs">{cid}</span>
          {initDone && <span className="text2 text-sm">{messages.length} сообщений</span>}
        </div>
      </div>

      <div className="tabs">
        <button className={`tab${tab === 'messages' ? ' active' : ''}`} onClick={() => setTab('messages')}>
          Диалог
        </button>
        <button className={`tab${tab === 'media' ? ' active' : ''}`} onClick={() => setTab('media')}>
          Медиафайлы
        </button>
      </div>

      {tab === 'messages' && (
        <div ref={listRef} className="admin-chat-list">
          {hasMore && (
            <div className="admin-chat-load-older">
              <button className="btn btn-secondary" onClick={loadOlder} disabled={loadingMsgs}>
                {loadingMsgs ? 'Загрузка…' : '↑ Загрузить более ранние'}
              </button>
            </div>
          )}

          {!initDone ? (
            <div className="loading-center">
              <div className="spinner" />
            </div>
          ) : msgError ? (
            <div className="admin-error-msg">{msgError}</div>
          ) : messages.length === 0 ? (
            <div className="empty-state">
              <div className="icon">💬</div>
              <div>Сообщений нет</div>
            </div>
          ) : (
            renderWithSeps(messages, setLightbox)
          )}

          <div ref={bottomRef} style={{ height: 1 }} />
        </div>
      )}

      {tab === 'media' && (
        <div className="admin-chat-media">
          <div className="admin-search-row">
            <select
              className="admin-select"
              value={mimeFilter}
              onChange={e => {
                setMimeFilter(e.target.value)
                setMediaPage(1)
              }}
            >
              <option value="">Все типы</option>
              <option value="image/">📷 Фото</option>
              <option value="video/">🎬 Видео</option>
              <option value="audio/">🎵 Аудио</option>
            </select>
          </div>
          {loadingMedia ? (
            <div className="loading-center">
              <div className="spinner" />
            </div>
          ) : mediaError ? (
            <div className="admin-error-msg">{mediaError}</div>
          ) : !media?.data.length ? (
            <div className="empty-state">
              <div className="icon">🖼</div>
              <div>Медиафайлы не найдены</div>
            </div>
          ) : (
            <>
              <div className="admin-media-grid">
                {media.data.map((m, i) => (
                  <MediaTile key={i} item={m} onZoom={setLightbox} />
                ))}
              </div>
              <Paginator page={mediaPage} totalPages={media.pagination.totalPages} onChange={setMediaPage} />
            </>
          )}
        </div>
      )}

      {lightbox && (
        <div className="admin-lightbox-overlay" onClick={() => setLightbox(null)}>
          <span className="admin-lightbox-close" onClick={() => setLightbox(null)}>
            ✕
          </span>
          {lightbox.type === 'video' ? (
            <video src={lightbox.url} controls autoPlay className="admin-lightbox-video" onClick={e => e.stopPropagation()} />
          ) : lightbox.type === 'audio' ? (
            <div className="admin-lightbox-audio" onClick={e => e.stopPropagation()}>
              <span style={{ fontSize: 48 }}>🎵</span>
              <audio controls autoPlay src={lightbox.url} />
            </div>
          ) : (
            <img src={lightbox.url} alt="" onClick={e => e.stopPropagation()} />
          )}
        </div>
      )}
    </div>
  )
}

// ── Рендер с разделителями по датам ──────────────────────────────────────
function renderWithSeps(messages: ChatMessage[], setLightbox: (v: Lightbox) => void): ReactElement[] {
  const result: ReactElement[] = []
  let lastDay = ''
  for (const msg of messages) {
    const day = new Date(msg.receivedAt).toLocaleDateString('ru-RU', { day: '2-digit', month: 'long', year: 'numeric' })
    if (day !== lastDay) {
      lastDay = day
      result.push(
        <div key={`d-${msg.id}`} className="admin-date-sep">
          <div className="admin-date-sep-line" />
          <span>{day}</span>
          <div className="admin-date-sep-line" />
        </div>,
      )
    }
    result.push(<Bubble key={msg.id} msg={msg} onZoom={setLightbox} />)
  }
  return result
}

function getMsgKind(msg: ChatMessage): 'deleted' | 'viewonce' | 'normal' {
  if (msg.isDeleted) return 'deleted'
  const mediaTypes = ['photo', 'video', 'video_note', 'animation']
  if (mediaTypes.includes(msg.messageType) && !msg.fileUniqueId && !msg.textContent) return 'viewonce'
  return 'normal'
}

function Bubble({ msg, onZoom }: { msg: ChatMessage; onZoom: (v: Lightbox) => void }) {
  const out = msg.isOutgoing
  const kind = getMsgKind(msg)

  let cls = `admin-bubble ${out ? 'out' : 'in'}`
  if (kind === 'deleted') cls += ' deleted'
  if (kind === 'viewonce') cls += ' view-once'

  const hasContent = msg.fileUniqueId || msg.textContent

  return (
    <div className={`admin-bubble-wrap ${out ? 'out' : 'in'}`}>
      {!out && (msg.senderName || msg.senderUsername) && (
        <div className="admin-bubble-sender">{msg.senderName || `@${msg.senderUsername}`}</div>
      )}

      <div className={cls}>
        {kind === 'deleted' && (
          <div className="admin-bubble-flag">
            <span>🗑</span>
            <span className="admin-bubble-flag-text deleted">Удалено</span>
            {msg.deletedAt && <span className="admin-bubble-flag-time">{fmtTime(msg.deletedAt)}</span>}
          </div>
        )}

        {kind === 'viewonce' && (
          <div className="admin-bubble-flag">
            <span>🔒</span>
            <span className="admin-bubble-flag-text viewonce">
              Одноразовое {MSG_TYPE_ICON[msg.messageType] || ''} — недоступно
            </span>
          </div>
        )}

        {kind === 'deleted' && hasContent && (
          <div style={{ opacity: 0.6 }}>
            <BubbleMedia msg={msg} onZoom={onZoom} />
            {msg.textContent && <div className="admin-bubble-text">{msg.textContent}</div>}
          </div>
        )}

        {kind === 'normal' && <BubbleMedia msg={msg} onZoom={onZoom} />}

        {kind === 'normal' && msg.isEdited && msg.originalText && msg.originalText !== msg.textContent && (
          <div className="admin-bubble-original">{msg.originalText}</div>
        )}

        {kind === 'normal' && msg.textContent && <div className="admin-bubble-text">{msg.textContent}</div>}

        <div className="admin-bubble-meta">
          {msg.isEdited && kind === 'normal' && (
            <span className="admin-bubble-tag edited">изм.{msg.editCount > 1 ? ` ×${msg.editCount}` : ''}</span>
          )}
          <span className="admin-bubble-time">{fmtTime(msg.receivedAt)}</span>
        </div>
      </div>
    </div>
  )
}

function BubbleMedia({ msg, onZoom }: { msg: ChatMessage; onZoom: (v: Lightbox) => void }) {
  const [imgErr, setImgErr] = useState(false)
  const [mediaErr, setMediaErr] = useState('')

  if (!msg.fileUniqueId) return null

  const url = mediaUrl(msg.fileUniqueId)
  const mt = msg.messageType
  const mime = msg.mimeType || ''

  // Sticker — WebP-изображение; document попадает в mime-based определение.
  const isImg = mt === 'photo' || mt === 'sticker' || mime.startsWith('image/')
  const isVideo = mt === 'video' || mt === 'video_note' || mt === 'animation' || mime.startsWith('video/')
  const isAudio = mt === 'voice' || mt === 'audio' || mime.startsWith('audio/')

  const onMediaErr = (e: SyntheticEvent<HTMLMediaElement>) => {
    const code = e.currentTarget.error?.code
    const desc = code === 4 ? 'формат не поддерживается' : code === 3 ? 'ошибка декодирования' : `ошибка ${code ?? ''}`
    setMediaErr(desc)
  }

  if (isImg && !imgErr) {
    return (
      <img
        className="admin-bubble-img"
        src={url}
        alt=""
        onError={() => setImgErr(true)}
        onClick={() => onZoom({ type: 'image', url })}
      />
    )
  }

  if (isImg && imgErr) {
    return <MediaErrBox url={url} label="Фото" icon="🖼" />
  }

  if (isVideo) {
    if (mediaErr) return <MediaErrBox url={url} label="Видео" icon="🎬" detail={mediaErr} />
    return <video className="admin-bubble-video" controls preload="metadata" src={url} onError={onMediaErr} />
  }

  if (isAudio) {
    if (mediaErr) return <MediaErrBox url={url} label="Аудио" icon="🎙" detail={mediaErr} />
    return <audio className="admin-bubble-audio" controls preload="metadata" src={url} onError={onMediaErr} />
  }

  // Прочие файлы — ссылка на скачивание.
  const icon = MSG_TYPE_ICON[mt] || '📎'
  return (
    <a href={url} target="_blank" rel="noreferrer" className="admin-bubble-file">
      <span style={{ fontSize: 20 }}>{icon}</span>
      <span>
        {mt || 'файл'}
        {msg.fileSize ? ` · ${bytes(msg.fileSize)}` : ''}
      </span>
    </a>
  )
}

function MediaErrBox({ url, label, icon, detail }: { url: string; label: string; icon: string; detail?: string }) {
  return (
    <div className="admin-media-err">
      <span>{icon}</span>
      <span>
        {label} недоступно{detail ? ` — ${detail}` : ''}
      </span>
      <a href={url} target="_blank" rel="noreferrer">
        ↗ открыть
      </a>
    </div>
  )
}

// ── Плитка медиа (вкладка «Медиафайлы») ──────────────────────────────────
function MediaTile({ item, onZoom }: { item: MediaItem; onZoom: (v: Lightbox) => void }) {
  const url = mediaUrl(item.fileUniqueId)
  const mime = item.mimeType || ''
  const ft = item.fileType || ''

  const isImg = (mime.startsWith('image/') || ft === 'photo' || ft === 'sticker') && item.hasLocalFile
  const isVideo = (mime.startsWith('video/') || ft === 'video' || ft === 'video_note' || ft === 'animation') && item.hasLocalFile
  const isAudio = (mime.startsWith('audio/') || ft === 'audio' || ft === 'voice') && item.hasLocalFile

  if (isImg) {
    return (
      <div className="admin-media-tile" onClick={() => onZoom({ type: 'image', url })}>
        <img src={url} alt="" loading="lazy" />
      </div>
    )
  }

  if (isVideo) {
    return (
      <div className="admin-media-tile admin-media-tile-video" onClick={() => onZoom({ type: 'video', url })}>
        <video src={url} preload="metadata" className="admin-media-tile-video-el" />
        <div className="admin-media-tile-play">▶</div>
      </div>
    )
  }

  if (isAudio) {
    return (
      <div className="admin-media-tile" onClick={() => onZoom({ type: 'audio', url })}>
        <div className="admin-media-tile-icon">
          <span style={{ fontSize: 32 }}>{MSG_TYPE_ICON[ft] || '🎵'}</span>
          <span>{ft === 'voice' ? 'голос' : 'аудио'}</span>
        </div>
      </div>
    )
  }

  return (
    <div className="admin-media-tile" onClick={() => window.open(url, '_blank')}>
      <div className="admin-media-tile-icon">
        <span>{MSG_TYPE_ICON[ft] || '📎'}</span>
        <span>{ft || 'файл'}</span>
      </div>
    </div>
  )
}
