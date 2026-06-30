import { useState } from 'react'
import { activateCode } from '@/entities/user'

interface Props {
  onSuccess: (res: { type: string; message: string }) => void
  onError: (message: string) => void
}

export function ActivateForm({ onSuccess, onError }: Props) {
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
      onSuccess(res)
    } catch (e) {
      const msg = (e as Error).message
      const friendly =
        msg === 'code_not_found' ? 'Код не найден' :
        msg === 'code_used_or_expired' ? 'Код уже использован или истёк' :
        msg
      onError(friendly)
    } finally {
      setLoading(false)
    }
  }

  return (
    <>
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
    </>
  )
}
