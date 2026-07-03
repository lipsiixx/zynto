import { useCallback, useEffect, useState, type FormEvent } from 'react'
import type { TariffOut, TariffPayload } from '@/admin/entities/tariff'
import { createTariff, deleteTariff, listTariffs, toggleTariff, updateTariff } from '@/admin/entities/tariff'
import { useAdminCtx } from '@/admin/shared/lib/AdminCtx'
import { ConfirmButton } from '@/admin/shared/ui'

const EMPTY_FORM: TariffPayload = { name: '', description: '', duration_days: 30, price_stars: 0, sort_order: 0 }

// Лимит Telegram Bot API на инвойс в XTR — бэкенд отдаёт 422 invalid_price выше него
const MAX_PRICE_STARS = 10000

export function TariffsPage() {
  const { showToast } = useAdminCtx()
  const [items, setItems] = useState<TariffOut[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [showCreate, setShowCreate] = useState(false)
  const [editingId, setEditingId] = useState<number | null>(null)

  const load = useCallback(() => {
    setLoading(true)
    setError('')
    listTariffs()
      .then(res => setItems(res.items.sort((a, b) => a.sort_order - b.sort_order)))
      .catch(e => setError((e as Error).message))
      .finally(() => setLoading(false))
  }, [])

  useEffect(() => {
    load()
  }, [load])

  const handleToggle = (id: number) => {
    toggleTariff(id)
      .then(updated => setItems(prev => prev.map(t => (t.id === id ? updated : t))))
      .catch(e => showToast((e as Error).message, 'error'))
  }

  const handleDelete = (id: number) => {
    deleteTariff(id)
      .then(() => {
        setItems(prev => prev.filter(t => t.id !== id))
        showToast('Тариф удалён', 'success')
      })
      .catch(e => showToast((e as Error).message, 'error'))
  }

  return (
    <div className="admin-page">
      <div className="admin-page-header">
        <h1>Тарифы</h1>
        <button className="btn btn-primary" style={{ width: 'auto' }} onClick={() => setShowCreate(v => !v)}>
          {showCreate ? 'Отмена' : '+ Добавить'}
        </button>
      </div>

      {showCreate && (
        <TariffForm
          submitLabel="Создать тариф"
          initial={EMPTY_FORM}
          onSubmit={payload =>
            createTariff(payload).then(created => {
              setItems(prev => [...prev, created])
              setShowCreate(false)
              showToast('Тариф создан', 'success')
            })
          }
        />
      )}

      {error && <div className="admin-error-msg">{error}</div>}

      {loading ? (
        <div className="loading-center">
          <div className="spinner" />
        </div>
      ) : !items.length ? (
        <div className="empty-state">
          <div className="icon">💳</div>
          <div>Тарифов нет</div>
        </div>
      ) : (
        <div className="admin-card-list">
          {items.map(t =>
            editingId === t.id ? (
              <TariffForm
                key={t.id}
                submitLabel="Сохранить"
                initial={t}
                onSubmit={payload =>
                  updateTariff(t.id, payload).then(updated => {
                    setItems(prev => prev.map(x => (x.id === t.id ? updated : x)))
                    setEditingId(null)
                    showToast('Тариф обновлён', 'success')
                  })
                }
                onCancel={() => setEditingId(null)}
              />
            ) : (
              <div key={t.id} className={`card${t.is_active ? '' : ' admin-card-disabled'}`}>
                <div className="row" style={{ justifyContent: 'space-between', alignItems: 'flex-start' }}>
                  <div>
                    <div className="semibold" style={{ fontSize: 15 }}>{t.name}</div>
                    {t.description && <div className="text-sm text2" style={{ marginTop: 2 }}>{t.description}</div>}
                  </div>
                  <span className={`badge ${t.is_active ? 'badge-green' : 'badge-gray'}`}>
                    {t.is_active ? 'Активен' : 'Скрыт'}
                  </span>
                </div>
                <div className="row gap-8 text-xs text2" style={{ flexWrap: 'wrap', margin: '10px 0' }}>
                  <span>Срок: {t.duration_days === null ? 'навсегда' : `${t.duration_days} дн.`}</span>
                  <span>Цена: {t.price_stars}⭐</span>
                  <span>Порядок: {t.sort_order}</span>
                </div>
                <div className="row gap-8" style={{ flexWrap: 'wrap' }}>
                  <button className="admin-icon-btn" onClick={() => setEditingId(t.id)}>Редактировать</button>
                  <button className="admin-icon-btn" onClick={() => handleToggle(t.id)}>
                    {t.is_active ? 'Скрыть' : 'Показать'}
                  </button>
                  <ConfirmButton label="Удалить" onConfirm={() => handleDelete(t.id)} />
                </div>
              </div>
            ),
          )}
        </div>
      )}
    </div>
  )
}

function TariffForm({
  initial,
  submitLabel,
  onSubmit,
  onCancel,
}: {
  initial: TariffPayload
  submitLabel: string
  onSubmit: (payload: TariffPayload) => Promise<unknown>
  onCancel?: () => void
}) {
  const [name, setName] = useState(initial.name)
  const [description, setDescription] = useState(initial.description ?? '')
  const [lifetime, setLifetime] = useState(initial.duration_days == null)
  const [durationDays, setDurationDays] = useState(String(initial.duration_days ?? 30))
  const [priceStars, setPriceStars] = useState(String(initial.price_stars))
  const [sortOrder, setSortOrder] = useState(String(initial.sort_order))
  const [submitting, setSubmitting] = useState(false)
  const [error, setError] = useState('')

  const handleSubmit = async (e: FormEvent) => {
    e.preventDefault()
    setError('')
    if (!name.trim()) {
      setError('Укажи название тарифа')
      return
    }
    const price = Number(priceStars)
    if (!price || price < 1 || price > MAX_PRICE_STARS) {
      setError(`Цена — от 1 до ${MAX_PRICE_STARS}⭐ (лимит Telegram на инвойс в Stars)`)
      return
    }
    const payload: TariffPayload = {
      name: name.trim(),
      description: description.trim() || null,
      duration_days: lifetime ? null : Math.max(1, Number(durationDays) || 1),
      price_stars: price,
      sort_order: Number(sortOrder) || 0,
    }
    setSubmitting(true)
    try {
      await onSubmit(payload)
    } catch (e) {
      setError((e as Error).message)
    } finally {
      setSubmitting(false)
    }
  }

  return (
    <form className="card admin-form" onSubmit={handleSubmit}>
      <div className="admin-form-row">
        <label className="text-sm text2">Название</label>
        <input className="input" value={name} onChange={e => setName(e.target.value)} />
      </div>
      <div className="admin-form-row">
        <label className="text-sm text2">Описание</label>
        <textarea className="input" rows={2} value={description} onChange={e => setDescription(e.target.value)} />
      </div>
      <div className="admin-form-row">
        <label className="admin-checkbox-row">
          <input type="checkbox" checked={lifetime} onChange={e => setLifetime(e.target.checked)} />
          <span>Пожизненный (без срока)</span>
        </label>
        {!lifetime && (
          <input
            className="input"
            style={{ marginTop: 8 }}
            type="number"
            min={1}
            placeholder="Срок, дней"
            value={durationDays}
            onChange={e => setDurationDays(e.target.value)}
          />
        )}
      </div>
      <div className="admin-grid-2">
        <div className="admin-form-row">
          <label className="text-sm text2">Цена, ⭐ (1–{MAX_PRICE_STARS})</label>
          <input className="input" type="number" min={1} max={MAX_PRICE_STARS} value={priceStars} onChange={e => setPriceStars(e.target.value)} />
        </div>
        <div className="admin-form-row">
          <label className="text-sm text2">Порядок сортировки</label>
          <input className="input" type="number" value={sortOrder} onChange={e => setSortOrder(e.target.value)} />
        </div>
      </div>

      {error && <div className="admin-error-msg">{error}</div>}

      <div className="row gap-8">
        <button className="btn btn-primary" type="submit" disabled={submitting}>
          {submitting ? 'Сохранение…' : submitLabel}
        </button>
        {onCancel && (
          <button className="btn btn-secondary" type="button" onClick={onCancel} style={{ width: 'auto' }}>
            Отмена
          </button>
        )}
      </div>
    </form>
  )
}
