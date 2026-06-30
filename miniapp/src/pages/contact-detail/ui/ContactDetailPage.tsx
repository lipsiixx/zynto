import { useEffect, useState, useCallback } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import type { Contact, DayStat } from '@/entities/contact'
import { getContacts, getContactEvents, getContactStats } from '@/entities/contact'
import type { MessageEvent } from '@/entities/message'
import { MessageCard } from '@/entities/message'
import type { MutualRating } from '@/entities/mutual-rating'
import { getMutualRating } from '@/entities/mutual-rating'
import { MutualRatingCard } from '@/features/mutual-rating'
import { TrustSlider } from '@/features/set-trust'
import { useApp } from '@/app/AppContext'

function ActivityChart({ data }: { data: DayStat[] }) {
  if (!data.length) return null
  const maxTotal = Math.max(...data.map(d => d.total), 1)

  return (
    <div>
      <div className="text-xs text2 mb-12">Активность за 30 дней</div>
      <div className="chart-wrap">
        {data.map((d, i) => (
          <div key={i} className="chart-bar-group" title={`${d.day}: ${d.total} сообщений, ${d.deleted} удалено`}>
            {d.deleted > 0 && (
              <div
                className="chart-bar"
                style={{
                  height: `${(d.deleted / maxTotal) * 100}%`,
                  background: 'var(--red)',
                  opacity: 0.7,
                }}
              />
            )}
            <div
              className="chart-bar"
              style={{
                height: `${((d.total - d.deleted) / maxTotal) * 100}%`,
                background: 'var(--purple)',
              }}
            />
          </div>
        ))}
      </div>
      <div className="row gap-8 mt-8">
        <div className="row gap-4 text-xs text2">
          <div style={{ width: 8, height: 8, borderRadius: 2, background: 'var(--purple)' }} />
          Сообщения
        </div>
        <div className="row gap-4 text-xs text2">
          <div style={{ width: 8, height: 8, borderRadius: 2, background: 'var(--red)' }} />
          Удалено
        </div>
      </div>
    </div>
  )
}

export function ContactDetailPage() {
  const { chatId } = useParams<{ chatId: string }>()
  const navigate = useNavigate()
  const { showToast } = useApp()
  const cid = Number(chatId)

  const [contact, setContact] = useState<Contact | null>(null)
  const [events, setEvents] = useState<MessageEvent[]>([])
  const [statsData, setStatsData] = useState<DayStat[]>([])
  const [total, setTotal] = useState(0)
  const [page, setPage] = useState(1)
  const [filter, setFilter] = useState('all')
  const [loading, setLoading] = useState(true)
  const [loadingMore, setLoadingMore] = useState(false)
  const [manualScore, setManualScore] = useState<number | null>(null)
  const [mr, setMr] = useState<MutualRating | null>(null)
  const [mrLoading, setMrLoading] = useState(false)
  const [mrScore, setMrScore] = useState(50)   // слайдер при отправке/принятии запроса
  const [showMrSlider, setShowMrSlider] = useState(false)

  useEffect(() => {
    window.Telegram?.WebApp?.BackButton?.show()
    window.Telegram?.WebApp?.BackButton?.onClick(() => navigate('/contacts'))
    return () => window.Telegram?.WebApp?.BackButton?.hide()
  }, [navigate])

  const loadContact = useCallback(async () => {
    try {
      const res = await getContacts()
      const c = res.data.find(x => x.chat_id === cid)
      if (c) {
        setContact(c)
        setManualScore(c.manual_score)
      }
    } catch {/* ignore */}
  }, [cid])

  const loadEvents = useCallback(async (pg = 1, flt = filter, reset = false) => {
    if (pg === 1) setLoading(true)
    else setLoadingMore(true)
    try {
      const res = await getContactEvents(cid, { flt, page: pg })
      setEvents(prev => reset || pg === 1 ? res.data : [...prev, ...res.data])
      setTotal(res.total)
      setPage(pg)
    } finally {
      setLoading(false)
      setLoadingMore(false)
    }
  }, [cid, filter])

  const loadStats = useCallback(async () => {
    try {
      const res = await getContactStats(cid)
      setStatsData(res.data)
    } catch {/* ignore */}
  }, [cid])

  const loadMR = useCallback(async () => {
    try { setMr(await getMutualRating(cid)) } catch {/* ignore */}
  }, [cid])

  useEffect(() => {
    loadContact()
    loadStats()
    loadEvents(1, filter, true)
    loadMR()
  }, [loadContact, loadStats, loadMR]) // eslint-disable-line

  const changeFilter = (f: string) => {
    setFilter(f)
    loadEvents(1, f, true)
  }

  const autoScore = contact?.auto_score ?? 50
  const mrActive = mr?.status === 'active'
  const displayScore = mrActive ? (mr!.mutual_score ?? 50) : (manualScore !== null ? manualScore : autoScore)

  if (!contact && loading) {
    return <div className="loading-center"><div className="spinner" /></div>
  }

  const title = contact?.chat_title || `Чат ${cid}`

  return (
    <div className="page">
      <div className="page-header">
        <button
          onClick={() => navigate('/contacts')}
          style={{ background: 'none', border: 'none', color: 'var(--purple-l)', cursor: 'pointer', padding: '4px 8px 4px 0', fontSize: 20 }}
        >
          ←
        </button>
        <h1 className="truncate">{title}</h1>
      </div>

      {/* Mutual Rating block */}
      <MutualRatingCard
        mr={mr}
        cid={cid}
        mrScore={mrScore}
        setMrScore={setMrScore}
        showMrSlider={showMrSlider}
        setShowMrSlider={setShowMrSlider}
        mrLoading={mrLoading}
        setMrLoading={setMrLoading}
        onUpdate={(updated) => { setMr(updated); loadContact() }}
        showToast={showToast}
      />

      {/* Trust block */}
      <TrustSlider
        contact={contact}
        manualScore={manualScore}
        autoScore={autoScore}
        mrActive={mrActive}
        displayScore={displayScore}
        cid={cid}
        onSaved={(score) => { setManualScore(score); loadContact() }}
        showToast={showToast}
      />

      {/* Activity chart */}
      {statsData.length > 0 && (
        <div className="card">
          <ActivityChart data={statsData} />
        </div>
      )}

      {/* Events */}
      <div className="tabs mt-8">
        {['all', 'deleted', 'edited', 'media'].map(f => (
          <button key={f} className={`tab${filter === f ? ' active' : ''}`} onClick={() => changeFilter(f)}>
            {f === 'all' ? 'Все' : f === 'deleted' ? '🗑 Удалённые' : f === 'edited' ? '✏️ Изменённые' : '📎 Медиа'}
          </button>
        ))}
      </div>

      <div className="text-xs text2 mb-12">{total} событий</div>

      {loading ? (
        <div className="loading-center"><div className="spinner" /></div>
      ) : events.length === 0 ? (
        <div className="empty-state">
          <div className="icon">📭</div>
          <div>Нет событий</div>
        </div>
      ) : (
        <>
          {events.map(e => <MessageCard key={e.id} event={e} />)}

          {events.length < total && (
            <button
              className="btn btn-secondary mt-8"
              disabled={loadingMore}
              onClick={() => loadEvents(page + 1)}
            >
              {loadingMore ? 'Загрузка…' : `Ещё (${total - events.length})`}
            </button>
          )}
        </>
      )}
    </div>
  )
}
