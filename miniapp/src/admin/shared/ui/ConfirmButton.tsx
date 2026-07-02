import { useState } from 'react'

interface Props {
  label: string
  confirmLabel?: string
  className?: string
  onConfirm: () => void
  disabled?: boolean
}

// Двухшажное подтверждение вместо window.confirm() — внутри Telegram WebView
// нативные диалоги ведут себя непредсказуемо на части клиентов, а
// Telegram.WebApp.showConfirm недоступен админ-бандлу (нет доступа к SDK
// здесь намеренно, см. styles.css комментарии об изоляции бандлов).
export function ConfirmButton({ label, confirmLabel = 'Точно?', className = 'btn btn-danger', onConfirm, disabled }: Props) {
  const [confirming, setConfirming] = useState(false)

  if (confirming) {
    return (
      <span className="row gap-8" style={{ display: 'inline-flex' }}>
        <button
          type="button"
          className="btn btn-danger"
          style={{ width: 'auto' }}
          onClick={() => {
            setConfirming(false)
            onConfirm()
          }}
          disabled={disabled}
        >
          {confirmLabel}
        </button>
        <button type="button" className="btn btn-secondary" style={{ width: 'auto' }} onClick={() => setConfirming(false)}>
          Отмена
        </button>
      </span>
    )
  }

  return (
    <button type="button" className={className} style={{ width: 'auto' }} onClick={() => setConfirming(true)} disabled={disabled}>
      {label}
    </button>
  )
}
