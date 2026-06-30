import { useNavigate } from 'react-router-dom'
import { ActivateForm } from '@/features/activate-promo'
import { useApp } from '@/app/AppContext'

export function ActivatePage() {
  const { showToast, refreshMe } = useApp()
  const navigate = useNavigate()

  const handleSuccess = async (res: { type: string; message: string }) => {
    showToast(res.message, 'success')
    if (res.type === 'access') {
      await refreshMe()
      setTimeout(() => navigate('/'), 1500)
    }
  }

  return (
    <div className="page">
      <div className="page-header">
        <h1>Промокод</h1>
      </div>

      <ActivateForm
        onSuccess={handleSuccess}
        onError={(msg) => showToast(msg, 'error')}
      />

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
