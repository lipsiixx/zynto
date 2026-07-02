import { reqLegacy } from '@/admin/shared/api/adminApi'
import type { Graph } from '../model/types'

export async function getGraph(minWeight = 1): Promise<Graph> {
  return reqLegacy('GET', `/graph?min_weight=${minWeight}`)
}
