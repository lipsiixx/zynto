import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { getTariffs, buyTariff } from '../api'
import type { Tariff } from '../types'
import { useApp } from '../App'

function fmtDuration(days: number | null) {
  if (days === null) return '♾ Навсегда'
  if (days === 1) return '1 день'
  if (days < 30) return `${days} дней`
  if (days < 365) {
    const m = Math.round(days / 30)
    return m === 1 ? '1 месяц' : `${m} месяца`
  }
  const y = Math.round(days / 365)
  return y === 1 ? '1 год' : `${y} года`
}

function SubStatusCard() {
  const { me } = useApp()
  if (!me) return null
  const { subscription: s } = me

  let label = ''
  let accent = 'var(--text2)'
  if (s.status === 'lifetime') { label = '♾ Подписка навсегда'; accent = 'var(--purple-l)' }
  else if (s.status === 'active') {
    const d = s.expires_at ? new Date(s.expires_at).toLocaleDateString('ru', { day: '2-digit', month: 'long', year: 'numeric' }) : ''
    label = `✅ Активна до ${d}`
    accent = 'var(--green)'
  } else if (s.status === 'expired') { label = '❌ Истекла'; accent = 'var(--red)' }
  else { label = 'Нет подписки'; accent = 'var(--text3)' }

  return (
    <div className="card" style={{ textAlign: 'center', padding: 20 }}>
      <div style={{ fontSize: 13, color: 'var(--text2)', marginBottom: 6 }}>Текущий статус</div>
      <div style={{ fontSize: 17, fontWeight: 700, color: accent }}>{label}</div>
    </div>
  )
}

export function Subscription() {
  const { showToast } = useApp()
  const navigate = useNavigate()
  const [tariffs, setTariffs] = useState<Tariff[]>([])
  const [loading, setLoading] = useState(true)
  const [buying, setBuying] = useState<number | null>(null)

  useEffect(() => {
    getTariffs().then(r => setTariffs(r.data)).finally(() => setLoading(false))
  }, [])

  const handleBuy = async (tariff: Tariff) => {
    setBuying(tariff.id)
    try {
      const res = await buyTariff(tariff.id)
      showToast(res.message, 'success')
      // Close mini app so user can see the invoice in chat
      setTimeout(() => window.Telegram?.WebApp?.close(), 1200)
    } catch (e) {
      showToast((e as Error).message || 'Ошибка', 'error')
    } finally {
      setBuying(null)
    }
  }

  return (
    <div className="page">
      <div className="page-header">
        <h1>Подписка</h1>
      </div>

      <SubStatusCard />

      <div className="mt-16">
        <div className="text-sm text2 mb-12">Доступные тарифы</div>

        {loading ? (
          <div className="loading-center"><div className="spinner" /></div>
        ) : tariffs.length === 0 ? (
          <div className="empty-state">
            <div className="icon">😔</div>
            <div>Нет доступных тарифов</div>
          </div>
        ) : (
          tariffs.map(t => (
            <div key={t.id} className="card" style={{ marginBottom: 12 }}>
              <div className="row-between">
                <div>
                  <div className="semibold" style={{ fontSize: 16 }}>{t.name}</div>
                  <div className="text-xs text2 mt-8">{fmtDuration(t.duration_days)}</div>
                  {t.description && (
                    <div className="text-xs text3 mt-8">{t.description}</div>
                  )}
                </div>
                <div style={{ textAlign: 'right', flexShrink: 0, marginLeft: 12 }}>
                  <div className="bold" style={{ fontSize: 20, color: 'var(--purple-l)' }}>
                    {t.price_stars} ⭐
                  </div>
                </div>
              </div>
              <button
                className="btn btn-primary mt-12"
                disabled={buying === t.id}
                onClick={() => handleBuy(t)}
              >
                {buying === t.id ? 'Отправляем инвойс…' : `Купить за ${t.price_stars} Stars`}
              </button>
            </div>
          ))
        )}

        <div className="divider" />

        <button className="btn btn-secondary" onClick={() => navigate('/activate')}>
          🎟 Активировать промокод
        </button>
      </div>
    </div>
  )
}
