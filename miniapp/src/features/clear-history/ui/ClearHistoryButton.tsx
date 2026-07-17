import { useState } from 'react'
import { haptics } from '@/shared/lib/haptics'
import { ConfirmButton } from '@/shared/ui'
import { clearHistory } from '../api/clearHistoryApi'

interface Props {
  onCleared: (clearedAt: string) => void
  showToast: (msg: string, type?: 'success' | 'error' | 'info') => void
}

export function ClearHistoryButton({ onCleared, showToast }: Props) {
  const [clearing, setClearing] = useState(false)

  const handleClear = async () => {
    haptics.select()
    setClearing(true)
    try {
      const res = await clearHistory()
      onCleared(res.history_cleared_at)
      haptics.success()
      showToast('История очищена', 'success')
    } catch {
      haptics.error()
      showToast('Ошибка очистки истории', 'error')
    } finally {
      setClearing(false)
    }
  }

  return (
    <div>
      <div className="text-xs text3" style={{ marginBottom: 10 }}>
        Скроет всю сохранённую историю удалённых, изменённых сообщений и медиа.
        Подписки и настроек это не касается.
      </div>
      <ConfirmButton
        label={clearing ? 'Очистка...' : 'Очистить историю'}
        confirmLabel="Точно очистить?"
        onConfirm={handleClear}
        disabled={clearing}
      />
    </div>
  )
}
