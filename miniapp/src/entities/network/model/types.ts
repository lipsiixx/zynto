export interface NetworkStatus {
  in_network: boolean
  consent_at: string | null
  visible: boolean
}

export interface NetworkNode {
  id: string
  label: string
  type: 'self' | 'contact'
  message_count: number
  trust_score: number | null
  strength: number  // 0-1
}

export interface NetworkEdge {
  source: string
  target: string
  weight: number
  trust_score: number | null
  strength: number
}

export interface NetworkGraph {
  nodes: NetworkNode[]
  edges: NetworkEdge[]
}
