import { useState } from 'react'
import type { Contact } from '@/entities/contact'
import { TrustCircle, setTrust } from '@/entities/contact'

interface Props {
  contact: Contact | null
  manualScore: number | null
  autoScore: number
  mrActive: boolean
  displayScore: number
  cid: number
  onSaved: (score: number | null) => void
  showToast: (msg: string, type?: 'success' | 'error' | 'info') => void
}

export function TrustSlider({ contact, manualScore, autoScore, mrActive, displayScore, cid, onSaved, showToast }: Props) {
  const [sliderVal, setSliderVal] = useState(manualScore !== null ? manualScore : autoScore)
  const [savingTrust, setSavingTrust] = useState(false)

  const saveTrust = async (score: number | null) => {
    setSavingTrust(true)
    try {
      await setTrust(cid, score)
      onSaved(score)
      showToast(score === null ? 'Кредит сброшен до авто' : `Кредит установлен: ${score}`, 'success')
    } catch {
      showToast('Ошибка сохранения', 'error')
    } finally {
      setSavingTrust(false)
    }
  }

  return (
    <div className="card card-glow">
      <div style={{ display: 'flex', alignItems: 'center', gap: 20 }}>
        <TrustCircle score={displayScore} size={88} isManual={mrActive || manualScore !== null} />
        <div style={{ flex: 1 }}>
          <div className="semibold" style={{ marginBottom: 4 }}>Кредит доверия</div>
          <div className="text-xs text2" style={{ marginBottom: 12 }}>
            {mrActive
              ? '🤝 Взаимный рейтинг — среднее двух оценок'
              : manualScore !== null
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

      {/* Slider — disabled when mutual rating is active */}
      <div style={{ opacity: mrActive ? 0.4 : 1, pointerEvents: mrActive ? 'none' : 'auto' }}>
        <div className="row-between text-xs text2 mb-12">
          <span>Ручная оценка</span>
          {mrActive
            ? <span style={{ color: 'var(--text3)' }}>заблокировано взаимным рейтингом</span>
            : <span style={{ fontWeight: 700, color: 'var(--purple-l)' }}>{sliderVal}</span>
          }
        </div>
        {!mrActive && (
          <>
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
          </>
        )}
      </div>
    </div>
  )
}
