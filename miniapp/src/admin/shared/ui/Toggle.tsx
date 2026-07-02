interface Props {
  checked: boolean
  onChange: (v: boolean) => void
  label?: string
  disabled?: boolean
}

// Стилизованный чекбокс-переключатель (.admin-toggle* в styles.css) —
// в основном приложении такого компонента нет, здесь он нужен для
// enabled-флагов в SettingsPage (Nudge/Рефералка/О боте/Курс).
export function Toggle({ checked, onChange, label, disabled }: Props) {
  return (
    <label className={`admin-toggle${disabled ? ' disabled' : ''}`}>
      <input type="checkbox" checked={checked} disabled={disabled} onChange={e => onChange(e.target.checked)} />
      <span className="admin-toggle-track">
        <span className="admin-toggle-thumb" />
      </span>
      {label && <span className="admin-toggle-label">{label}</span>}
    </label>
  )
}
