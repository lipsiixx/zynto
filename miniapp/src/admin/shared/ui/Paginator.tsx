interface Props {
  page: number
  totalPages: number
  onChange: (page: number) => void
}

// Упрощённая пагинация «‹ N/M ›» — вместо номерной ленты из
// admin-panel/src/pages/Users.jsx (не нужна на узком экране мини-аппа),
// в стиле Paginator из admin-panel/src/pages/UserDetail.jsx.
export function Paginator({ page, totalPages, onChange }: Props) {
  if (totalPages <= 1) return null
  return (
    <div className="admin-pagination">
      <button className="admin-page-btn" onClick={() => onChange(page - 1)} disabled={page <= 1}>
        ‹
      </button>
      <span className="text-xs text2">
        {page} / {totalPages}
      </span>
      <button className="admin-page-btn" onClick={() => onChange(page + 1)} disabled={page >= totalPages}>
        ›
      </button>
    </div>
  )
}
