// Порт shared/ui/Toast.tsx основного приложения — продублирован намеренно
// (админ-бандл не может импортировать код из src/shared основного
// приложения). Классы toast-container/toast определены в app/styles.css
// основного приложения, но доступны и здесь: оба бандла рендерятся в один
// document (см. комментарий в шапке admin/styles.css).
export interface AdminToastItem {
  id: number
  msg: string
  type: 'success' | 'error' | 'info'
}

export function AdminToast({ toasts }: { toasts: AdminToastItem[] }) {
  if (!toasts.length) return null
  return (
    <div className="toast-container">
      {toasts.map(t => (
        <div key={t.id} className={`toast toast-${t.type}`}>
          {t.msg}
        </div>
      ))}
    </div>
  )
}
