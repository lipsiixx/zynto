import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { activateCode } from '../api'
import { useApp } from '../App'

export function Activate() {
  const { showToast, refreshMe } = useApp()
  const navigate = useNavigate()
  const [code, setCode] = useState('')
  const [loading, setLoading] = useState(false)
  const [result, setResult] = useState<{ type: string; message: string } | null>(null)

  const handleActivate = async () => {
    if (!code.trim()) return
    setLoading(true)
    setResult(null)
    try {
      const res = await activateCode(code.trim())
      setResult(res)
      showToast(res.message, 'success')
      if (res.type === 'access') {
        await refreshMe()
        setTimeout(() => navigate('/'), 1500)
      }
    } catch (e) {
      const msg = (e as Error).message
      const friendly =
        msg === 'code_not_found' ? 'Код не найден' :
        msg === 'code_used_or_expired' ? 'Код уже использован или истёк' :
        msg
      showToast(friendly, 'error')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="page">
      <div className="page-header">
        <h1>Промокод</h1>
      </div>

      <div className="card">
        <div className="text-sm text2" style={{ marginBottom: 12 }}>
          Введи промокод для активации доступа или скидки на следующую покупку.
        </div>

        <input
          className="input"
          placeholder="Например: A3BK9QTZ"
          value={code}
          onChange={e => setCode(e.target.value.toUpperCase())}
          onKeyDown={e => e.key === 'Enter' && handleActivate()}
          style={{ letterSpacing: '0.1em', fontFamily: 'monospace', marginBottom: 12 }}
        />

        <button
          className="btn btn-primary"
          disabled={loading || !code.trim()}
          onClick={handleActivate}
        >
          {loading ? 'Проверяем…' : 'Активировать'}
        </button>
      </div>

      {result && (
        <div className="card" style={{ marginTop: 12, border: '1px solid var(--green)', background: 'var(--green-dim)' }}>
          <div style={{ color: 'var(--green)', fontWeight: 600, marginBottom: 4 }}>
            {result.type === 'discount' ? '🎫 Скидка применена' : '✅ Подписка активирована'}
          </div>
          <div className="text-sm" style={{ color: 'var(--text2)' }}>{result.message}</div>
        </div>
      )}

      <div className="card" style={{ marginTop: 16 }}>
        <div className="text-xs text2" style={{ marginBottom: 8, fontWeight: 600 }}>
          Как получить промокод?
        </div>
        <div className="text-xs text3">
          • Пригласи друга — получишь бонусные дни<br />
          • Купи подарочный код для себя или друга<br />
          • Получи от администратора в рамках акции
        </div>
      </div>
    </div>
  )
}
