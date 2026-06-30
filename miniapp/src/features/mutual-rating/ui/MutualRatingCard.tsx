import type { MutualRating } from '@/entities/mutual-rating'
import { sendMRRequest, acceptMR, declineMR, cancelMR } from '@/entities/mutual-rating'

interface MRProps {
  mr: MutualRating | null
  cid: number
  mrScore: number
  setMrScore: (v: number) => void
  showMrSlider: boolean
  setShowMrSlider: (v: boolean) => void
  mrLoading: boolean
  setMrLoading: (v: boolean) => void
  onUpdate: (mr: MutualRating) => void
  showToast: (msg: string, type?: 'success' | 'error' | 'info') => void
}

export function MutualRatingCard({
  mr, cid, mrScore, setMrScore, showMrSlider, setShowMrSlider,
  mrLoading, setMrLoading, onUpdate, showToast,
}: MRProps) {
  const act = async (fn: () => Promise<MutualRating>) => {
    setMrLoading(true)
    try {
      const updated = await fn()
      onUpdate(updated)
    } catch (e) {
      const msg = (e as Error).message
      const friendly: Record<string, string> = {
        target_not_in_bot: 'Контакт не использует бота',
        target_not_connected: 'Контакт не подключил мониторинг',
        already_exists: 'Запрос уже отправлен',
      }
      showToast(friendly[msg] || 'Ошибка', 'error')
    } finally {
      setMrLoading(false)
    }
  }

  // Нет записи или недоступно
  if (!mr || mr.status === 'none') {
    if (mr?.target_in_bot === false) {
      return (
        <div className="mr-card mr-unavailable">
          <span className="mr-icon">🤝</span>
          <span className="text-xs text3">Контакт не использует бота — взаимный рейтинг недоступен</span>
        </div>
      )
    }
    if (mr?.target_connected === false) {
      return (
        <div className="mr-card mr-unavailable">
          <span className="mr-icon">🤝</span>
          <span className="text-xs text3">Контакт не подключил мониторинг</span>
        </div>
      )
    }
    return (
      <div className="mr-card">
        <div className="mr-header">
          <span className="mr-icon">🤝</span>
          <div style={{ flex: 1 }}>
            <div className="semibold" style={{ fontSize: 13 }}>Взаимный рейтинг</div>
            <div className="text-xs text3">Оба выставят оценку — увидите среднее</div>
          </div>
          <button
            className="btn btn-primary mr-action-btn"
            onClick={() => setShowMrSlider(!showMrSlider)}
          >
            Предложить
          </button>
        </div>
        {showMrSlider && (
          <div className="mr-slider-wrap">
            <div className="row-between text-xs text2 mb-12">
              <span>Ваша оценка контакта</span>
              <span style={{ fontWeight: 700, color: 'var(--purple-l)' }}>{mrScore}</span>
            </div>
            <div className="slider-wrap">
              <input
                type="range" min={0} max={100} value={mrScore}
                style={{ background: `linear-gradient(to right, var(--purple) ${mrScore}%, rgba(255,255,255,0.1) ${mrScore}%)` }}
                onChange={e => setMrScore(Number(e.target.value))}
              />
            </div>
            <button
              className="btn btn-primary mt-12"
              disabled={mrLoading}
              onClick={() => act(() => sendMRRequest(cid, mrScore))}
            >
              {mrLoading ? 'Отправка…' : 'Отправить запрос'}
            </button>
          </div>
        )}
      </div>
    )
  }

  // Pending outgoing
  if (mr.status === 'pending' && mr.direction === 'outgoing') {
    return (
      <div className="mr-card mr-pending">
        <div className="mr-header">
          <span className="mr-icon">⏳</span>
          <div style={{ flex: 1 }}>
            <div className="semibold" style={{ fontSize: 13 }}>Взаимный рейтинг</div>
            <div className="text-xs text3">Ожидаем ответа от контакта…</div>
          </div>
          <button
            className="btn btn-secondary mr-action-btn"
            disabled={mrLoading}
            onClick={() => act(() => cancelMR(cid))}
          >
            Отменить
          </button>
        </div>
      </div>
    )
  }

  // Pending incoming
  if (mr.status === 'pending' && mr.direction === 'incoming') {
    return (
      <div className="mr-card mr-incoming">
        <div className="mr-header">
          <span className="mr-icon">🤝</span>
          <div style={{ flex: 1 }}>
            <div className="semibold" style={{ fontSize: 13 }}>Входящий запрос</div>
            <div className="text-xs text3">Предлагает открыть Взаимный рейтинг</div>
          </div>
        </div>
        <div className="mr-slider-wrap">
          <div className="row-between text-xs text2 mb-12">
            <span>Ваша оценка</span>
            <span style={{ fontWeight: 700, color: 'var(--purple-l)' }}>{mrScore}</span>
          </div>
          <div className="slider-wrap">
            <input
              type="range" min={0} max={100} value={mrScore}
              style={{ background: `linear-gradient(to right, var(--purple) ${mrScore}%, rgba(255,255,255,0.1) ${mrScore}%)` }}
              onChange={e => setMrScore(Number(e.target.value))}
            />
          </div>
          <div className="row gap-8 mt-12">
            <button
              className="btn btn-primary"
              style={{ flex: 2 }}
              disabled={mrLoading}
              onClick={() => act(() => acceptMR(cid, mrScore))}
            >
              {mrLoading ? '…' : '✅ Принять'}
            </button>
            <button
              className="btn btn-secondary"
              style={{ flex: 1 }}
              disabled={mrLoading}
              onClick={() => act(() => declineMR(cid))}
            >
              Отклонить
            </button>
          </div>
        </div>
      </div>
    )
  }

  // Active
  if (mr.status === 'active') {
    const score = mr.mutual_score ?? 50
    return (
      <div className="mr-card mr-active">
        <div className="mr-header">
          <span className="mr-icon">🤝</span>
          <div style={{ flex: 1 }}>
            <div className="semibold" style={{ fontSize: 13 }}>Взаимный рейтинг активен</div>
            <div className="text-xs text3">
              Ваша оценка: {mr.direction === 'outgoing' ? mr.requester_score : mr.target_score} &nbsp;·&nbsp;
              Их оценка: {mr.direction === 'outgoing' ? mr.target_score : mr.requester_score}
            </div>
          </div>
          <div className="mr-score-badge">{score}</div>
        </div>
        <div className="mr-score-bar">
          <div className="mr-score-fill" style={{ width: `${score}%` }} />
        </div>
        <button
          className="btn btn-secondary mt-12"
          style={{ fontSize: 12 }}
          disabled={mrLoading}
          onClick={() => act(() => cancelMR(cid))}
        >
          {mrLoading ? '…' : '🔕 Отключить взаимный рейтинг'}
        </button>
      </div>
    )
  }

  // Declined / Cancelled — показываем что было
  return (
    <div className="mr-card mr-unavailable">
      <span className="mr-icon">🤝</span>
      <span className="text-xs text3">
        {mr.status === 'declined' ? 'Запрос отклонён' : 'Взаимный рейтинг отключён'}
        {' — '}
        <button
          style={{ background: 'none', border: 'none', color: 'var(--purple-l)', cursor: 'pointer', padding: 0, fontSize: 12 }}
          onClick={() => setShowMrSlider(true)}
        >
          предложить снова
        </button>
      </span>
    </div>
  )
}
