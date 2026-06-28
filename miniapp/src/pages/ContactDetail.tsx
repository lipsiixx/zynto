import { useEffect, useState, useCallback } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { getContactEvents, getContactStats, setTrust } from '../api'
import type { Contact, DayStat, MessageEvent } from '../types'
import { getContacts } from '../api'
import { TrustCircle } from '../components/TrustCircle'
import { MessageCard } from '../components/MessageCard'
import { useApp } from '../App'

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

export function ContactDetail() {
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
  const [sliderVal, setSliderVal] = useState(50)
  const [savingTrust, setSavingTrust] = useState(false)

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
        const ms = c.manual_score
        setManualScore(ms)
        setSliderVal(ms !== null ? ms : c.auto_score)
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

  useEffect(() => {
    loadContact()
    loadStats()
    loadEvents(1, filter, true)
  }, [loadContact, loadStats]) // eslint-disable-line

  const changeFilter = (f: string) => {
    setFilter(f)
    loadEvents(1, f, true)
  }

  const saveTrust = async (score: number | null) => {
    setSavingTrust(true)
    try {
      await setTrust(cid, score)
      setManualScore(score)
      showToast(score === null ? 'Кредит сброшен до авто' : `Кредит установлен: ${score}`, 'success')
      await loadContact()
    } catch {
      showToast('Ошибка сохранения', 'error')
    } finally {
      setSavingTrust(false)
    }
  }

  const autoScore = contact?.auto_score ?? 50
  const displayScore = manualScore !== null ? manualScore : autoScore

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

      {/* Trust block */}
      <div className="card card-glow">
        <div style={{ display: 'flex', alignItems: 'center', gap: 20 }}>
          <TrustCircle score={displayScore} size={88} isManual={manualScore !== null} />
          <div style={{ flex: 1 }}>
            <div className="semibold" style={{ marginBottom: 4 }}>Кредит доверия</div>
            <div className="text-xs text2" style={{ marginBottom: 12 }}>
              {manualScore !== null
                ? 'Ручная оценка — вы выставили вручную'
                : 'Авто-оценка по истории сообщений'}
            </div>

            {contact && (
              <div className="row gap-8 text-xs">
                <span style={{ color: 'var(--red)' }}>🗑 {contact.deleted_count} удалено</span>
                <span style={{ color: 'var(--text2)' }}>💬 {contact.total_messages} всего</span>
              </div>
            )}
          </div>
        </div>

        <div className="divider" />

        {/* Slider */}
        <div>
          <div className="row-between text-xs text2 mb-12">
            <span>Ручная оценка</span>
            <span style={{ fontWeight: 700, color: 'var(--purple-l)' }}>{sliderVal}</span>
          </div>
          <div className="slider-wrap">
            <input
              type="range" min={0} max={100} value={sliderVal}
              style={{
                background: `linear-gradient(to right, var(--purple) ${sliderVal}%, rgba(255,255,255,0.1) ${sliderVal}%)`,
              }}
              onChange={e => setSliderVal(Number(e.target.value))}
              onMouseUp={() => saveTrust(sliderVal)}
              onTouchEnd={() => saveTrust(sliderVal)}
            />
          </div>
          <div className="row gap-8 mt-8">
            <button
              className="btn btn-primary"
              style={{ flex: 1, padding: '10px' }}
              disabled={savingTrust}
              onClick={() => saveTrust(sliderVal)}
            >
              Сохранить
            </button>
            {manualScore !== null && (
              <button
                className="btn btn-secondary"
                style={{ flex: 1, padding: '10px' }}
                disabled={savingTrust}
                onClick={() => { setSliderVal(autoScore); saveTrust(null) }}
              >
                Сброс
              </button>
            )}
          </div>
        </div>
      </div>

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
