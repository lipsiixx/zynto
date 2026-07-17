import { useState } from 'react'
import { haptics } from '@/shared/lib/haptics'
import { setHistoryRetention } from '../api/historyRetentionApi'

interface Props {
  currentHours: number
  onSaved: (hours: number) => void
  showToast: (msg: string, type?: 'success' | 'error' | 'info') => void
}

type Mode = 'hours' | 'days'

function pluralHours(n: number): string {
  const mod10 = n % 10
  const mod100 = n % 100
  if (mod100 >= 11 && mod100 <= 14) return 'часов'
  if (mod10 === 1) return 'час'
  if (mod10 >= 2 && mod10 <= 4) return 'часа'
  return 'часов'
}

function pluralDays(n: number): string {
  const mod10 = n % 10
  const mod100 = n % 100
  if (mod100 >= 11 && mod100 <= 14) return 'дней'
  if (mod10 === 1) return 'день'
  if (mod10 >= 2 && mod10 <= 4) return 'дня'
  return 'дней'
}

function initialState(hours: number): { mode: Mode; hoursVal: number; daysVal: number } {
  if (hours >= 1 && hours <= 12) {
    return { mode: 'hours', hoursVal: hours, daysVal: 2 }
  }
  if (hours >= 24 && hours <= 168 && hours % 24 === 0) {
    return { mode: 'days', hoursVal: 1, daysVal: hours / 24 }
  }
  // Неожиданное значение с сервера — откатываемся к дефолту (48ч = 2 дня)
  return { mode: 'days', hoursVal: 1, daysVal: 2 }
}

export function HistoryRetentionControl({ currentHours, onSaved, showToast }: Props) {
  const init = initialState(currentHours)
  const [mode, setMode] = useState<Mode>(init.mode)
  const [hoursVal, setHoursVal] = useState(init.hoursVal)
  const [daysVal, setDaysVal] = useState(init.daysVal)
  const [saving, setSaving] = useState(false)

  const min = mode === 'hours' ? 1 : 1
  const max = mode === 'hours' ? 12 : 7
  const value = mode === 'hours' ? hoursVal : daysVal
  const pct = ((value - min) / (max - min)) * 100

  const switchMode = (m: Mode) => {
    if (m === mode) return
    haptics.select()
    setMode(m)
  }

  const handleChange = (v: number) => {
    if (mode === 'hours') setHoursVal(v)
    else setDaysVal(v)
  }

  const handleSave = async () => {
    haptics.select()
    setSaving(true)
    try {
      const hoursToSend = mode === 'hours' ? hoursVal : daysVal * 24
      const res = await setHistoryRetention(hoursToSend)
      onSaved(res.history_retention_hours)
      showToast('Срок хранения обновлён', 'success')
    } catch (e) {
      showToast(
        e instanceof Error && e.message === 'invalid_hours'
          ? 'Недопустимое значение срока хранения'
          : 'Ошибка сохранения',
        'error',
      )
    } finally {
      setSaving(false)
    }
  }

  return (
    <div>
      <div className="row gap-8 mb-12">
        <button
          className={`btn ${mode === 'hours' ? 'btn-primary' : 'btn-secondary'}`}
          style={{ flex: 1, padding: '8px' }}
          disabled={saving}
          onClick={() => switchMode('hours')}
        >
          Часы
        </button>
        <button
          className={`btn ${mode === 'days' ? 'btn-primary' : 'btn-secondary'}`}
          style={{ flex: 1, padding: '8px' }}
          disabled={saving}
          onClick={() => switchMode('days')}
        >
          Дни
        </button>
      </div>

      <div className="row-between text-xs text2 mb-12">
        <span>Хранить историю</span>
        <span style={{ fontWeight: 700, color: 'var(--purple-l)' }}>
          {mode === 'hours' ? `${value} ${pluralHours(value)}` : `${value} ${pluralDays(value)}`}
        </span>
      </div>

      <div className="slider-wrap">
        <input
          type="range"
          min={min}
          max={max}
          step={1}
          value={value}
          style={{
            background: `linear-gradient(to right, var(--purple) ${pct}%, rgba(255,255,255,0.1) ${pct}%)`,
          }}
          onChange={(e) => handleChange(Number(e.target.value))}
          disabled={saving}
        />
      </div>

      <button
        className="btn btn-primary"
        style={{ marginTop: 12, width: '100%' }}
        disabled={saving}
        onClick={handleSave}
      >
        {saving ? 'Сохранение...' : 'Сохранить'}
      </button>
    </div>
  )
}
