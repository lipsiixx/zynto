import { useState } from 'react'
import type { Tariff } from '@/entities/tariff'
import { buyTariff } from '@/entities/tariff'

interface Props {
  tariff: Tariff
  onSuccess?: (message: string) => void
  onError?: (message: string) => void
}

export function BuyButton({ tariff, onSuccess, onError }: Props) {
  const [buying, setBuying] = useState(false)

  const handleBuy = async () => {
    setBuying(true)
    try {
      const res = await buyTariff(tariff.id)
      onSuccess?.(res.message)
      // Close mini app so user can see the invoice in chat
      setTimeout(() => window.Telegram?.WebApp?.close(), 1200)
    } catch (e) {
      onError?.((e as Error).message || 'Ошибка')
    } finally {
      setBuying(false)
    }
  }

  return (
    <button
      className="btn btn-primary mt-12"
      disabled={buying}
      onClick={handleBuy}
    >
      {buying ? 'Отправляем инвойс…' : `Купить за ${tariff.price_stars} Stars`}
    </button>
  )
}
