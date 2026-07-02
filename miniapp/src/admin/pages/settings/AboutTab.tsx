import { useEffect, useState } from 'react'
import type { AboutContentType, AboutLegalSection, AboutOut, AboutSupportSection } from '@/admin/entities/about'
import { getAbout, updateAbout } from '@/admin/entities/about'
import { useAdminCtx } from '@/admin/shared/lib/AdminCtx'
import { Toggle } from '@/admin/shared/ui'

const EMPTY_LEGAL: AboutLegalSection = { enabled: true, type: 'text', content: '' }
const EMPTY_SUPPORT: AboutSupportSection = { enabled: true, url: '' }

// Порт handlers/admin/about_settings.py.
export function AboutTab() {
  const { showToast } = useAdminCtx()
  const [privacy, setPrivacy] = useState<AboutLegalSection>(EMPTY_LEGAL)
  const [terms, setTerms] = useState<AboutLegalSection>(EMPTY_LEGAL)
  const [support, setSupport] = useState<AboutSupportSection>(EMPTY_SUPPORT)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [saving, setSaving] = useState(false)

  useEffect(() => {
    getAbout()
      .then((data: AboutOut) => {
        setPrivacy(data.privacy)
        setTerms(data.terms)
        setSupport(data.support)
      })
      .catch(e => setError((e as Error).message))
      .finally(() => setLoading(false))
  }, [])

  const handleSave = () => {
    setSaving(true)
    updateAbout({ privacy, terms, support })
      .then(data => {
        setPrivacy(data.privacy)
        setTerms(data.terms)
        setSupport(data.support)
        showToast('Сохранено', 'success')
      })
      .catch(e => showToast((e as Error).message, 'error'))
      .finally(() => setSaving(false))
  }

  if (loading) return <div className="loading-center"><div className="spinner" /></div>
  if (error) return <div className="admin-error-msg">{error}</div>

  return (
    <div>
      <LegalSectionForm title="Политика конфиденциальности" section={privacy} onChange={setPrivacy} />
      <LegalSectionForm title="Пользовательское соглашение" section={terms} onChange={setTerms} />

      <div className="card">
        <div className="admin-form-row">
          <Toggle checked={support.enabled} onChange={v => setSupport(s => ({ ...s, enabled: v }))} label="Поддержка" />
        </div>
        {support.enabled && (
          <div className="admin-form-row">
            <label className="text-sm text2">Ссылка/контакт поддержки</label>
            <input className="input" value={support.url} onChange={e => setSupport(s => ({ ...s, url: e.target.value }))} />
          </div>
        )}
      </div>

      <button className="btn btn-primary" onClick={handleSave} disabled={saving}>
        {saving ? 'Сохранение…' : 'Сохранить'}
      </button>
    </div>
  )
}

function LegalSectionForm({
  title,
  section,
  onChange,
}: {
  title: string
  section: AboutLegalSection
  onChange: (s: AboutLegalSection) => void
}) {
  return (
    <div className="card">
      <div className="admin-form-row">
        <Toggle checked={section.enabled} onChange={v => onChange({ ...section, enabled: v })} label={title} />
      </div>
      {section.enabled && (
        <>
          <div className="admin-form-row">
            <label className="text-sm text2">Тип содержимого</label>
            <div className="tabs">
              {(['text', 'url'] as AboutContentType[]).map(t => (
                <button
                  key={t}
                  type="button"
                  className={`tab${section.type === t ? ' active' : ''}`}
                  onClick={() => onChange({ ...section, type: t })}
                >
                  {t === 'text' ? 'Текст' : 'URL'}
                </button>
              ))}
            </div>
          </div>
          <div className="admin-form-row">
            <label className="text-sm text2">{section.type === 'url' ? 'Ссылка' : 'Текст'}</label>
            {section.type === 'url' ? (
              <input className="input" value={section.content} onChange={e => onChange({ ...section, content: e.target.value })} />
            ) : (
              <textarea className="input" rows={4} value={section.content} onChange={e => onChange({ ...section, content: e.target.value })} />
            )}
          </div>
        </>
      )}
    </div>
  )
}
