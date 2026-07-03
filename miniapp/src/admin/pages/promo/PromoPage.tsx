import { useCallback, useEffect, useState, type FormEvent } from 'react'
import type { CreatePromoPayload, PromoCodeType, PromoFilter, PromoOut } from '@/admin/entities/promo'
import { PROMO_DURATION_PRESETS, PROMO_MAX_USES_PRESETS, createPromo, deletePromo, listPromo } from '@/admin/entities/promo'
import type { TariffOut } from '@/admin/entities/tariff'
import { listTariffs } from '@/admin/entities/tariff'
import { useAdminCtx } from '@/admin/shared/lib/AdminCtx'
import { fmtDate } from '@/admin/shared/lib/format'
import { ConfirmButton, CopyButton } from '@/admin/shared/ui'

const FILTERS: { value: PromoFilter; label: string }[] = [
  { value: 'all', label: 'Все' },
  { value: 'active', label: 'Активные' },
  { value: 'used', label: 'Использованные' },
]

const STATUS_BADGE: Record<PromoOut['status'], string> = {
  active: 'badge-green',
  exhausted: 'badge-gray',
  expired: 'badge-red',
}

const STATUS_LABEL: Record<PromoOut['status'], string> = {
  active: 'Активен',
  exhausted: 'Исчерпан',
  expired: 'Истёк',
}

// Порт handlers/admin/promo.py (создание + cb_list) на форму мини-аппа.
export function PromoPage() {
  const { showToast } = useAdminCtx()
  const [filter, setFilter] = useState<PromoFilter>('all')
  const [items, setItems] = useState<PromoOut[]>([])
  const [loading, setLoading] = useState(true)
  const [listError, setListError] = useState('')
  const [showForm, setShowForm] = useState(false)
  const [createdCode, setCreatedCode] = useState<PromoOut | null>(null)

  const load = useCallback(() => {
    setLoading(true)
    setListError('')
    listPromo(filter)
      .then(res => setItems(res.items))
      .catch(e => setListError((e as Error).message))
      .finally(() => setLoading(false))
  }, [filter])

  useEffect(() => {
    load()
  }, [load])

  const handleCreated = (promo: PromoOut) => {
    setCreatedCode(promo)
    setShowForm(false)
    showToast('Промокод создан', 'success')
    load()
  }

  return (
    <div className="admin-page">
      <div className="admin-page-header">
        <h1>Промокоды</h1>
        <button className="btn btn-primary" style={{ width: 'auto' }} onClick={() => setShowForm(v => !v)}>
          {showForm ? 'Отмена' : '+ Создать'}
        </button>
      </div>

      {createdCode && (
        <div className="card admin-created-code">
          <div className="text-sm text2" style={{ marginBottom: 6 }}>Промокод создан</div>
          <div className="row" style={{ justifyContent: 'space-between', alignItems: 'center', gap: 10 }}>
            <span className="admin-mono admin-code-big">{createdCode.code}</span>
            <CopyButton text={createdCode.code} />
          </div>
          <button className="admin-icon-btn" style={{ marginTop: 10 }} onClick={() => setCreatedCode(null)}>
            Скрыть
          </button>
        </div>
      )}

      {showForm && <PromoForm onCreated={handleCreated} />}

      <div className="tabs">
        {FILTERS.map(f => (
          <button key={f.value} className={`tab${filter === f.value ? ' active' : ''}`} onClick={() => setFilter(f.value)}>
            {f.label}
          </button>
        ))}
      </div>

      {listError && <div className="admin-error-msg">{listError}</div>}

      {loading ? (
        <div className="loading-center">
          <div className="spinner" />
        </div>
      ) : !items.length ? (
        <div className="empty-state">
          <div className="icon">🎟</div>
          <div>Промокодов нет</div>
        </div>
      ) : (
        <div className="admin-card-list">
          {items.map(p => (
            <PromoCard
              key={p.id}
              promo={p}
              onDelete={() => {
                deletePromo(p.id)
                  .then(() => {
                    showToast('Промокод удалён', 'success')
                    setItems(list => list.filter(x => x.id !== p.id))
                  })
                  .catch(e => showToast((e as Error).message, 'error'))
              }}
            />
          ))}
        </div>
      )}
    </div>
  )
}

function PromoCard({ promo, onDelete }: { promo: PromoOut; onDelete: () => void }) {
  const detail =
    promo.code_type === 'discount'
      ? `Скидка ${promo.discount_stars ?? 0}⭐ на ${promo.discount_tariff_id ? `тариф #${promo.discount_tariff_id}` : 'любой тариф'}`
      : promo.duration_label || 'Навсегда'
  const usesLabel = promo.max_uses === null ? `${promo.uses_count}/∞` : `${promo.uses_count}/${promo.max_uses}`

  return (
    <div className="card">
      <div className="row" style={{ justifyContent: 'space-between', alignItems: 'center', marginBottom: 6 }}>
        <span className="admin-mono semibold" style={{ fontSize: 15 }}>{promo.code}</span>
        <span className={`badge ${STATUS_BADGE[promo.status]}`}>{STATUS_LABEL[promo.status]}</span>
      </div>
      <div className="text-sm" style={{ marginBottom: 6 }}>{detail}</div>
      <div className="row gap-8 text-xs text2" style={{ flexWrap: 'wrap', marginBottom: 6 }}>
        <span>Использований: {usesLabel}</span>
        <span>Истекает: {promo.code_expires_at ? fmtDate(promo.code_expires_at) : 'бессрочно'}</span>
        <span>Создан: {fmtDate(promo.created_at)}</span>
      </div>
      {promo.note && <div className="text-xs text2" style={{ marginBottom: 8 }}>Заметка: {promo.note}</div>}
      <div className="row gap-8" style={{ flexWrap: 'wrap' }}>
        <CopyButton text={promo.code} />
        <ConfirmButton label="Удалить" className="admin-icon-btn" onConfirm={onDelete} />
      </div>
    </div>
  )
}

function PromoForm({ onCreated }: { onCreated: (p: PromoOut) => void }) {
  const [codeType, setCodeType] = useState<PromoCodeType>('access')
  const [durationPreset, setDurationPreset] = useState('d1')
  const [customDays, setCustomDays] = useState('')
  const [discountStars, setDiscountStars] = useState('')
  const [discountTariffId, setDiscountTariffId] = useState('')
  const [tariffs, setTariffs] = useState<TariffOut[]>([])
  const [maxUsesPreset, setMaxUsesPreset] = useState('1')
  const [codeExpiresAt, setCodeExpiresAt] = useState('')
  const [note, setNote] = useState('')
  const [submitting, setSubmitting] = useState(false)
  const [error, setError] = useState('')

  useEffect(() => {
    if (codeType === 'discount' && !tariffs.length) {
      listTariffs()
        .then(res => setTariffs(res.items.filter(t => t.is_active)))
        .catch(() => {})
    }
  }, [codeType, tariffs.length])

  const handleSubmit = async (e: FormEvent) => {
    e.preventDefault()
    setError('')

    const maxUsesObj = PROMO_MAX_USES_PRESETS.find(p => p.value === maxUsesPreset)
    const payload: CreatePromoPayload = {
      code_type: codeType,
      max_uses: maxUsesObj ? maxUsesObj.maxUses : 1,
      code_expires_at: codeExpiresAt ? new Date(codeExpiresAt).toISOString() : null,
      note: note.trim() || null,
    }

    if (codeType === 'access') {
      if (durationPreset === 'custom') {
        const days = Number(customDays)
        if (!days || days < 1) {
          setError('Укажи корректное количество дней')
          return
        }
        payload.minutes = days * 1440
        payload.label = `${days} дн.`
      } else {
        const preset = PROMO_DURATION_PRESETS.find(p => p.value === durationPreset)
        payload.minutes = preset?.minutes ?? null
        payload.label = preset?.label
      }
    } else {
      const stars = Number(discountStars)
      if (!stars || stars < 1) {
        setError('Укажи размер скидки в звёздах')
        return
      }
      payload.discount_stars = stars
      payload.discount_tariff_id = discountTariffId ? Number(discountTariffId) : null
    }

    setSubmitting(true)
    try {
      const created = await createPromo(payload)
      onCreated(created)
    } catch (e) {
      setError((e as Error).message)
    } finally {
      setSubmitting(false)
    }
  }

  return (
    <form className="card admin-form" onSubmit={handleSubmit}>
      <div className="admin-form-row">
        <label className="text-sm text2">Тип промокода</label>
        <div className="tabs">
          <button type="button" className={`tab${codeType === 'access' ? ' active' : ''}`} onClick={() => setCodeType('access')}>
            Доступ
          </button>
          <button type="button" className={`tab${codeType === 'discount' ? ' active' : ''}`} onClick={() => setCodeType('discount')}>
            Скидка
          </button>
        </div>
      </div>

      {codeType === 'access' ? (
        <div className="admin-form-row">
          <label className="text-sm text2">Срок доступа</label>
          <select className="admin-select" style={{ width: '100%' }} value={durationPreset} onChange={e => setDurationPreset(e.target.value)}>
            {PROMO_DURATION_PRESETS.map(p => (
              <option key={p.value} value={p.value}>{p.label}</option>
            ))}
          </select>
          {durationPreset === 'custom' && (
            <input
              className="input"
              style={{ marginTop: 8 }}
              type="number"
              min={1}
              placeholder="Количество дней"
              value={customDays}
              onChange={e => setCustomDays(e.target.value)}
            />
          )}
        </div>
      ) : (
        <>
          <div className="admin-form-row">
            <label className="text-sm text2">Скидка, ⭐ XTR</label>
            <input className="input" type="number" min={1} value={discountStars} onChange={e => setDiscountStars(e.target.value)} />
          </div>
          <div className="admin-form-row">
            <label className="text-sm text2">Тариф</label>
            <select className="admin-select" style={{ width: '100%' }} value={discountTariffId} onChange={e => setDiscountTariffId(e.target.value)}>
              <option value="">Любой тариф</option>
              {tariffs.map(t => (
                <option key={t.id} value={t.id}>{t.name}</option>
              ))}
            </select>
          </div>
        </>
      )}

      <div className="admin-form-row">
        <label className="text-sm text2">Количество использований</label>
        <select className="admin-select" style={{ width: '100%' }} value={maxUsesPreset} onChange={e => setMaxUsesPreset(e.target.value)}>
          {PROMO_MAX_USES_PRESETS.map(p => (
            <option key={p.value} value={p.value}>{p.label}</option>
          ))}
        </select>
      </div>

      <div className="admin-form-row">
        <label className="text-sm text2">Код истекает (необязательно)</label>
        <input className="input" type="date" value={codeExpiresAt} onChange={e => setCodeExpiresAt(e.target.value)} />
      </div>

      <div className="admin-form-row">
        <label className="text-sm text2">Заметка (необязательно)</label>
        <textarea className="input" rows={2} value={note} onChange={e => setNote(e.target.value)} />
      </div>

      {error && <div className="admin-error-msg">{error}</div>}

      <button className="btn btn-primary" type="submit" disabled={submitting}>
        {submitting ? 'Создание…' : 'Создать промокод'}
      </button>
    </form>
  )
}
