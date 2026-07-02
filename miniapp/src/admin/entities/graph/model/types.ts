// Форма ответа api/routers/graph.py::get_graph (GET /v1/graph). Полный граф
// подписчик↔контакт (в отличие от entities/network — граф связей ОДНОГО
// пользователя с его контактами; см. entities/network/model/types.ts).
//
// ВНИМАНИЕ (координация с backend): database/queries/api.py::get_graph()
// добавляет узлам-подписчикам поле "dbId" (внутренний User.id, нужен для
// перехода на /a/users/:id — так делал старый admin-panel), но
// api/schemas.py::GraphNode его не объявляет, и pydantic молча отбрасывает
// "лишние" поля при сериализации ответа. Поэтому dbId сюда типизирован как
// опциональный и код ниже готов его использовать, но реальный бэкенд сейчас
// его не отдаёт — клик по узлу-подписчику не сможет перейти в профиль, пока
// backend-агент не добавит `dbId: Optional[int] = None` в GraphNode.
export type GraphNodeType = 'subscriber' | 'contact' | string

export interface GraphNode {
  id: string
  label: string
  type: GraphNodeType
  avatarFileUniqueId: string | null
  /** Внутренний User.id — см. предупреждение выше, сейчас backend его не отдаёт. */
  dbId?: number
}

export interface GraphEdge {
  source: string
  target: string
  weight: number
}

export interface Graph {
  nodes: GraphNode[]
  edges: GraphEdge[]
}
