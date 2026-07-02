import { useState } from 'react'
import { useAdminCtx } from '@/admin/shared/lib/AdminCtx'
import { AboutTab } from './AboutTab'
import { CleanupTab } from './CleanupTab'
import { CourseTab } from './CourseTab'
import { NudgeTab } from './NudgeTab'
import { ReferralTab } from './ReferralTab'
import { TributeTab } from './TributeTab'

type TabKey = 'nudge' | 'about' | 'course' | 'tribute' | 'referral' | 'cleanup'

const BASE_TABS: { key: TabKey; label: string }[] = [
  { key: 'nudge', label: 'Nudge' },
  { key: 'about', label: 'О боте' },
  { key: 'course', label: 'Курс' },
  { key: 'tribute', label: 'Tribute' },
  { key: 'referral', label: 'Рефералка' },
]

// Аккордеон-вкладки вместо под-роутов — каждая вкладка независимо грузит
// свои данные (см. handlers/admin/*.py, соответствующие роутеру каждой
// секции). «Автоочистка» — только для суперадмина (isSuperadmin из
// GET /v1/webapp/me, см. AdminApp.tsx).
export function SettingsPage() {
  const { isSuperadmin } = useAdminCtx()
  const tabs = isSuperadmin ? [...BASE_TABS, { key: 'cleanup' as TabKey, label: 'Автоочистка' }] : BASE_TABS
  const [tab, setTab] = useState<TabKey>('nudge')

  return (
    <div className="admin-page">
      <div className="admin-page-header">
        <h1>Настройки</h1>
      </div>

      <div className="tabs">
        {tabs.map(t => (
          <button key={t.key} className={`tab${tab === t.key ? ' active' : ''}`} onClick={() => setTab(t.key)}>
            {t.label}
          </button>
        ))}
      </div>

      {tab === 'nudge' && <NudgeTab />}
      {tab === 'about' && <AboutTab />}
      {tab === 'course' && <CourseTab />}
      {tab === 'tribute' && <TributeTab />}
      {tab === 'referral' && <ReferralTab />}
      {tab === 'cleanup' && isSuperadmin && <CleanupTab />}
    </div>
  )
}
