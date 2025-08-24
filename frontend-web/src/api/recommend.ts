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
  AI详细分析?: string | null
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
  recommend_type?: string
  status?: string
}

export async function getRecommendHistory(page = 1, page_size = 10, start_date?: string, end_date?: string, recommend_type?: string) {
  const r = await http.get('/api/recommendations/history', { params: { page, page_size, start_date, end_date, recommend_type } })
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

// 关键词推荐：请求与结果类型
export type KeywordStartPayload = {
  keyword: string
  period?: string
  max_candidates?: number
  weights?: Record<string, number>
  exclude_st?: boolean
  min_market_cap?: number
  board?: 'main' | 'gem' | 'star'
  provider?: string
  temperature?: number
  api_key?: string
}

export type KeywordTaskPhases = { screen: number; analyze: number }
export type KeywordTaskStatus = (
  { status: string; done: number; total: number; percent: number; phase?: 'screen'|'analyze'|'done'; phases?: KeywordTaskPhases }
) | { status: 'not_found' }
export type KeywordTaskResult = ({ recommendations: RecommendItem[]; rec_id?: number; filtered_count?: number }) | { status: string } | { error: string }

export async function startKeywordRecommend(payload: KeywordStartPayload) {
  const r = await http.post<{ task_id: string }>('/api/recommend/keyword/start', payload)
  return r.data
}

export async function getKeywordStatus(task_id: string) {
  const r = await http.get(`/api/recommend/keyword/status/${encodeURIComponent(task_id)}`)
  return r.data as KeywordTaskStatus
}

export async function getKeywordResult(task_id: string) {
  const r = await http.get(`/api/recommend/keyword/result/${encodeURIComponent(task_id)}`)
  return r.data as KeywordTaskResult
}

// 全市场推荐：请求类型与函数
export type MarketRecommendPayload = {
  period?: string
  max_candidates?: number
  weights?: Record<string, number>
  exclude_st?: boolean
  min_market_cap?: number
  board?: 'main' | 'gem' | 'star'
  provider?: string
  temperature?: number
  api_key?: string
}

export async function recommendMarket(payload: MarketRecommendPayload = {}) {
  const r = await http.post<{ recommendations: RecommendItem[]; rec_id: number; total_screened?: number }>(
    '/api/recommend/market',
    payload
  )
  return r.data
}