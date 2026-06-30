import { useEffect, useState } from 'react'
import type { ReferralStats } from '@/entities/referral'
import { getReferral } from '@/entities/referral'
import { useApp } from '@/app/AppContext'

function daysLabel(n: number): string {
  if (n % 10 === 1 && n % 100 !== 11) return `${n} день`
  if ([2, 3, 4].includes(n % 10) && ![12, 13, 14].includes(n % 100)) return `${n} дня`
  return `${n} дней`
}

export function ReferralPage() {
  const { showToast } = useApp()
  const [data, setData] = useState<ReferralStats | null>(null)
  const [loading, setLoading] = useState(true)
  const [copied, setCopied] = useState(false)

  useEffect(() => {
    getReferral()
      .then(setData)
      .catch(() => showToast('Ошибка загрузки', 'error'))
      .finally(() => setLoading(false))
  }, [])

  const copyLink = () => {
    if (!data) return
    navigator.clipboard.writeText(data.link).then(() => {
      setCopied(true)
      showToast('Ссылка скопирована!', 'success')
      setTimeout(() => setCopied(false), 2000)
    })
  }

  const shareLink = () => {
    if (!data) return
    const shareUrl = `https://t.me/share/url?url=${encodeURIComponent(data.link)}&text=${encodeURIComponent('Присоединяйся к Zynto — умный мониторинг удалённых сообщений!')}`
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    const tg = (window as any).Telegram?.WebApp
    if (tg?.openTelegramLink) {
      tg.openTelegramLink(shareUrl)
    } else {
      window.open(shareUrl, '_blank')
    }
  }

  return (
    <div className="page">
      <div className="page-header">
        <h1>Реферальная программа</h1>
      </div>

      {loading ? (
        <div className="loading-center"><div className="spinner" /></div>
      ) : !data || !data.enabled ? (
        <div className="empty-state">
          <div className="icon">🔒</div>
          <div>Реферальная программа временно недоступна</div>
        </div>
      ) : (
        <>
          {/* Описание */}
          <div className="card" style={{ marginBottom: 12 }}>
            <div style={{ fontSize: 32, marginBottom: 8, textAlign: 'center' }}>👥</div>
            <div className="semibold" style={{ textAlign: 'center', marginBottom: 6 }}>
              Приглашай друзей — получай бонусы
            </div>
            <div className="text-xs text3" style={{ textAlign: 'center', lineHeight: 1.5 }}>
              За каждую покупку подписки по твоей ссылке ты получаешь{' '}
              <span style={{ color: 'var(--purple-l)', fontWeight: 700 }}>
                +{daysLabel(data.reward_days)}
              </span>{' '}
              бесплатного доступа
            </div>
          </div>

          {/* Ссылка */}
          <div className="card" style={{ marginBottom: 12 }}>
            <div className="text-xs text3" style={{ marginBottom: 6 }}>Твоя реферальная ссылка</div>
            <div
              style={{
                background: 'var(--bg-card2)',
                border: '1px solid var(--purple-border)',
                borderRadius: 8,
                padding: '10px 12px',
                fontSize: 13,
                wordBreak: 'break-all',
                color: 'var(--purple-l)',
                marginBottom: 10,
                fontFamily: 'monospace',
              }}
            >
              {data.link}
            </div>
            <div className="row gap-8">
              <button className="btn btn-primary" style={{ flex: 1 }} onClick={copyLink}>
                {copied ? '✓ Скопировано' : '📋 Копировать'}
              </button>
              <button className="btn btn-secondary" style={{ flex: 1 }} onClick={shareLink}>
                📤 Поделиться
              </button>
            </div>
          </div>

          {/* Статистика */}
          <div className="card">
            <div className="semibold" style={{ marginBottom: 12 }}>Твоя статистика</div>
            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 10 }}>
              <StatBox label="Приглашено" value={data.total_referred} icon="👤" />
              <StatBox label="Купили подписку" value={data.total_converted} icon="✅" />
              <StatBox label="Всего наград" value={data.total_rewards} icon="🎁" />
              <StatBox label="Заработано дней" value={data.total_days_earned} icon="📅" />
            </div>
          </div>
        </>
      )}
    </div>
  )
}

function StatBox({ label, value, icon }: { label: string; value: number; icon: string }) {
  return (
    <div
      style={{
        background: 'var(--bg-card2)',
        borderRadius: 10,
        padding: '12px 10px',
        textAlign: 'center',
      }}
    >
      <div style={{ fontSize: 22, marginBottom: 4 }}>{icon}</div>
      <div style={{ fontSize: 22, fontWeight: 800, color: 'var(--purple-l)' }}>{value}</div>
      <div className="text-xs text3" style={{ marginTop: 2 }}>{label}</div>
    </div>
  )
}
