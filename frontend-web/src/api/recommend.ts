import { http } from './http'

export type RecommendConfig = {
  symbols?: string[]
  period?: string
  weights?: Record<string, number>
  provider?: string
  temperature?: number
  api_key?: string
}

export type RecommendItem = {
  股票代码: string
  股票名称: string
  评分: number
  建议动作: string
  理由简述: string
}

export async function recommend(config: RecommendConfig = {}) {
  const r = await http.post<{ recommendations: RecommendItem[]; rec_id: number }>('/api/recommend', config)
  return r.data
}

export type HistoryRecord = {
  id: number
  created_at: string
  period: string
  total_candidates: number
  top_n: number
  summary: string
}

export async function getRecommendHistory(page = 1, page_size = 10, start_date?: string, end_date?: string) {
  const r = await http.get('/api/recommendations/history', { params: { page, page_size, start_date, end_date } })
  return r.data as { total: number; page: number; page_size: number; records: HistoryRecord[] }
}

export async function getRecommendDetails(rec_id: number) {
  const r = await http.get(`/api/recommendations/${rec_id}/details`)
  return r.data as { id: number; created_at: string; period: string; total_candidates: number; items: RecommendItem[] }
}

export async function deleteRecommend(rec_id: number) {
  const r = await http.delete(`/api/recommendations/${rec_id}`)
  return r.data
}