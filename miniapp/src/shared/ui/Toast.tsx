export interface ToastItem { id: number; msg: string; type: string; leaving?: boolean }

export function Toast({ toasts }: { toasts: ToastItem[] }) {
  if (!toasts.length) return null
  return (
    <div className="toast-container">
      {toasts.map(t => (
        <div key={t.id} className={`toast toast-${t.type}${t.leaving ? ' toast-leaving' : ''}`}>
          {t.msg}
        </div>
      ))}
    </div>
  )
}
