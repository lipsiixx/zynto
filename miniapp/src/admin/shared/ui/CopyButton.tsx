import { useState } from 'react'

async function copyText(text: string): Promise<void> {
  try {
    await navigator.clipboard.writeText(text)
    return
  } catch {
    // Clipboard API недоступен (нет HTTPS-контекста/разрешения) — textarea-фоллбэк.
  }
  const ta = document.createElement('textarea')
  ta.value = text
  ta.style.position = 'fixed'
  ta.style.opacity = '0'
  document.body.appendChild(ta)
  ta.focus()
  ta.select()
  try {
    document.execCommand('copy')
  } catch {
    /* ignore — нечем скопировать, юзер скопирует руками */
  }
  document.body.removeChild(ta)
}

export function CopyButton({ text, label = '⧉ Копировать' }: { text: string; label?: string }) {
  const [copied, setCopied] = useState(false)

  const handleClick = () => {
    copyText(text).finally(() => {
      setCopied(true)
      setTimeout(() => setCopied(false), 1500)
    })
  }

  return (
    <button type="button" className="admin-icon-btn" onClick={handleClick}>
      {copied ? '✓ Скопировано' : label}
    </button>
  )
}
