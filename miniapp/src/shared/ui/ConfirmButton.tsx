import { useState } from 'react'

interface Props {
  label: string
  confirmLabel?: string
  className?: string
  onConfirm: () => void
  disabled?: boolean
}

// Двухшажное подтверждение вместо window.confirm() / Telegram.WebApp.showConfirm() —
// оба ведут себя непредсказуемо в части Telegram-клиентов, поэтому вместо нативного
// диалога используем инлайн-подтверждение прямо в кнопке (тап → появляются
// «подтвердить»/«отмена»). См. аналогичный компонент в изолированном admin-бандле
// (miniapp/src/admin/shared/ui/ConfirmButton.tsx) — импортировать оттуда нельзя,
// бандлы собираются раздельно, поэтому копия здесь для основного мини-аппа.
export function ConfirmButton({
  label,
  confirmLabel = 'Точно?',
  className = 'btn btn-danger',
  onConfirm,
  disabled,
}: Props) {
  const [confirming, setConfirming] = useState(false)

  if (confirming) {
    return (
      <span className="row gap-8" style={{ display: 'flex', width: '100%' }}>
        <button
          type="button"
          className="btn btn-danger"
          style={{ flex: 1 }}
          onClick={() => {
            setConfirming(false)
            onConfirm()
          }}
          disabled={disabled}
        >
          {confirmLabel}
        </button>
        <button
          type="button"
          className="btn btn-secondary"
          style={{ flex: 1 }}
          onClick={() => setConfirming(false)}
          disabled={disabled}
        >
          Отмена
        </button>
      </span>
    )
  }

  return (
    <button type="button" className={className} onClick={() => setConfirming(true)} disabled={disabled}>
      {label}
    </button>
  )
}
