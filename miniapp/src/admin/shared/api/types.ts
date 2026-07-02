// Общая обёртка пагинации, используемая всеми monitoring-роутерами
// (api/schemas.py::Pagination). Вынесена в shared, чтобы entities/user и
// entities/chat не зависели друг от друга.

export interface Pagination {
  page: number
  limit: number
  total: number
  totalPages: number
}
