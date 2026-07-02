import { useEffect, useState } from 'react'
import type { TributeFetchedProduct, TributeProduct } from '@/admin/entities/tribute'
import { fetchTributeProducts, getTributeProducts, saveTributeProducts } from '@/admin/entities/tribute'
import { useAdminCtx } from '@/admin/shared/lib/AdminCtx'
import { ConfirmButton } from '@/admin/shared/ui'

// Порт handlers/admin/tribute_settings.py — "Фронт сам собирает список"
// (см. контракт PUT /tribute/products): загрузка из Tribute API и
// добавление в локальный массив, сохранение целиком по кнопке.
export function TributeTab() {
  const { showToast } = useAdminCtx()
  const [products, setProducts] = useState<TributeProduct[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [saving, setSaving] = useState(false)
  const [fetched, setFetched] = useState<TributeFetchedProduct[] | null>(null)
  const [fetching, setFetching] = useState(false)

  useEffect(() => {
    getTributeProducts()
      .then(res => setProducts(res.products))
      .catch(e => setError((e as Error).message))
      .finally(() => setLoading(false))
  }, [])

  const handleFetch = () => {
    setFetching(true)
    fetchTributeProducts()
      .then(res => setFetched(res.products))
      .catch(e => showToast((e as Error).message === 'tribute_key_missing' ? 'TRIBUTE_API_KEY не настроен в .env' : (e as Error).message, 'error'))
      .finally(() => setFetching(false))
  }

  const addFetched = (p: TributeFetchedProduct, durationDays: number | null) => {
    if (products.some(x => String(x.tribute_product_id) === String(p.id))) {
      showToast('Продукт уже в списке', 'info')
      return
    }
    setProducts(prev => [
      ...prev,
      {
        tribute_product_id: p.id,
        name: p.name,
        price: p.amount,
        currency: p.currency,
        web_link: p.webLink,
        duration_days: durationDays,
      },
    ])
    setFetched(prev => (prev ? prev.filter(x => x.id !== p.id) : prev))
  }

  const updateDuration = (id: string | number, durationDays: number | null) => {
    setProducts(prev => prev.map(p => (p.tribute_product_id === id ? { ...p, duration_days: durationDays } : p)))
  }

  const removeProduct = (id: string | number) => {
    setProducts(prev => prev.filter(p => p.tribute_product_id !== id))
  }

  const handleSave = () => {
    setSaving(true)
    saveTributeProducts(products)
      .then(res => {
        setProducts(res.products)
        showToast('Список сохранён', 'success')
      })
      .catch(e => showToast((e as Error).message, 'error'))
      .finally(() => setSaving(false))
  }

  if (loading) return <div className="loading-center"><div className="spinner" /></div>
  if (error) return <div className="admin-error-msg">{error}</div>

  return (
    <div>
      <div className="admin-page-header">
        <span className="semibold">Продукты Tribute (СБП)</span>
        <button className="admin-icon-btn" onClick={handleFetch} disabled={fetching}>
          {fetching ? 'Загрузка…' : 'Загрузить из Tribute'}
        </button>
      </div>

      {fetched && (
        <div className="card">
          <div className="text-sm text2" style={{ marginBottom: 8 }}>Одобренные продукты Tribute — выбери срок и добавь в список</div>
          {!fetched.length ? (
            <div className="text-sm text2">Нет новых продуктов</div>
          ) : (
            fetched.map(p => <FetchedProductRow key={p.id} product={p} onAdd={addFetched} />)
          )}
        </div>
      )}

      {!products.length ? (
        <div className="empty-state"><div>Список пуст</div></div>
      ) : (
        <div className="admin-card-list">
          {products.map(p => (
            <div key={p.tribute_product_id} className="card">
              <div className="row" style={{ justifyContent: 'space-between', alignItems: 'flex-start' }}>
                <div>
                  <div className="semibold">{p.name}</div>
                  <div className="text-xs text2" style={{ marginTop: 2 }}>
                    {p.price != null ? `${(p.price / 100).toFixed(2)} ${p.currency ?? ''}` : '—'}
                  </div>
                </div>
                <ConfirmButton label="Удалить" onConfirm={() => removeProduct(p.tribute_product_id)} />
              </div>
              <div className="admin-form-row" style={{ marginTop: 8 }}>
                <label className="text-sm text2">Срок подписки, дней (0 = навсегда)</label>
                <input
                  className="input"
                  type="number"
                  min={0}
                  value={p.duration_days ?? 0}
                  onChange={e => updateDuration(p.tribute_product_id, Number(e.target.value) || 0 ? Number(e.target.value) : null)}
                />
              </div>
            </div>
          ))}
        </div>
      )}

      <button className="btn btn-primary" onClick={handleSave} disabled={saving}>
        {saving ? 'Сохранение…' : 'Сохранить список'}
      </button>
    </div>
  )
}

function FetchedProductRow({ product, onAdd }: { product: TributeFetchedProduct; onAdd: (p: TributeFetchedProduct, d: number | null) => void }) {
  const [days, setDays] = useState('0')

  return (
    <div className="row gap-8" style={{ alignItems: 'center', flexWrap: 'wrap', padding: '8px 0', borderBottom: '1px solid var(--purple-border)' }}>
      <div style={{ flex: 1, minWidth: 120 }}>
        <div className="text-sm semibold">{product.name}</div>
        <div className="text-xs text2">{(product.amount / 100).toFixed(2)} {product.currency}</div>
      </div>
      <input
        className="input"
        type="number"
        min={0}
        style={{ width: 90 }}
        value={days}
        onChange={e => setDays(e.target.value)}
      />
      <button
        className="admin-icon-btn"
        onClick={() => onAdd(product, Number(days) > 0 ? Number(days) : null)}
      >
        Добавить
      </button>
    </div>
  )
}
