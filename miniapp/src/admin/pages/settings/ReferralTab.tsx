import { useEffect, useState } from 'react'
import type { ReferralOut } from '@/admin/entities/referral'
import { getReferral, updateReferral } from '@/admin/entities/referral'
import { useAdminCtx } from '@/admin/shared/lib/AdminCtx'
import { fmtDate } from '@/admin/shared/lib/format'
import { Paginator, Toggle } from '@/admin/shared/ui'

const LIMIT = 20

// Порт handlers/admin/referral.py.
export function ReferralTab() {
  const { showToast } = useAdminCtx()
  const [data, setData] = useState<ReferralOut | null>(null)
  const [page, setPage] = useState(1)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [saving, setSaving] = useState(false)
  const [rewardDaysInput, setRewardDaysInput] = useState('3')

  const load = (p: number) => {
    setLoading(true)
    setError('')
    getReferral(p, LIMIT)
      .then(d => {
        setData(d)
        setRewardDaysInput(String(d.reward_days))
      })
      .catch(e => setError((e as Error).message))
      .finally(() => setLoading(false))
  }

  useEffect(() => load(page), [page])

  const handleToggleEnabled = (enabled: boolean) => {
    if (!data) return
    setData({ ...data, enabled })
    updateReferral({ enabled })
      .then(s => setData(prev => (prev ? { ...prev, ...s } : prev)))
      .catch(e => {
        showToast((e as Error).message, 'error')
        setData(prev => (prev ? { ...prev, enabled: !enabled } : prev))
      })
  }

  const handleSaveDays = () => {
    const days = Number(rewardDaysInput)
    if (Number.isNaN(days) || days < 0) return
    setSaving(true)
    updateReferral({ reward_days: days })
      .then(s => {
        setData(prev => (prev ? { ...prev, ...s } : prev))
        showToast('Сохранено', 'success')
      })
      .catch(e => showToast((e as Error).message, 'error'))
      .finally(() => setSaving(false))
  }

  if (loading && !data) return <div className="loading-center"><div className="spinner" /></div>
  if (error) return <div className="admin-error-msg">{error}</div>
  if (!data) return null

  const totalPages = Math.max(1, Math.ceil(data.total_rewards / LIMIT))

  return (
    <div>
      <div className="card">
        <div className="admin-form-row">
          <Toggle checked={data.enabled} onChange={handleToggleEnabled} label="Реферальная программа включена" />
        </div>
        <div className="admin-form-row">
          <label className="text-sm text2">Дней подписки за приглашённого</label>
          <div className="row gap-8">
            <input className="input" type="number" min={0} value={rewardDaysInput} onChange={e => setRewardDaysInput(e.target.value)} />
            <button className="btn btn-primary" style={{ width: 'auto' }} onClick={handleSaveDays} disabled={saving}>
              {saving ? '…' : 'Сохранить'}
            </button>
          </div>
        </div>
      </div>

      <div className="admin-section-title">Начисления ({data.total_rewards})</div>
      {!data.rewards.length ? (
        <div className="empty-state"><div>Начислений ещё не было</div></div>
      ) : (
        <div className="card admin-table-wrap">
          <table className="admin-table">
            <thead>
              <tr>
                <th>Реферер</th>
                <th>Приглашённый</th>
                <th>Дней</th>
                <th>Дата</th>
              </tr>
            </thead>
            <tbody>
              {data.rewards.map((r, i) => (
                <tr key={i}>
                  <td>{r.referrer_name || <span className="admin-mono">{r.referrer_id}</span>}</td>
                  <td>{r.referred_name || <span className="text2">—</span>}</td>
                  <td>{r.days_granted}</td>
                  <td className="text-xs text2">{fmtDate(r.created_at)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
      <Paginator page={page} totalPages={totalPages} onChange={setPage} />
    </div>
  )
}
