import { http } from './http'

export type WatchItem = {
  股票代码: string
  股票名称?: string
  综合评分?: number | null
  操作建议?: string | null
  分析理由摘要?: string | null
  最近分析时间?: string | null
}

export async function listWatchlist() {
  const r = await http.get<{ items: WatchItem[] }>('/api/watchlist/list')
  return r.data.items || []
}

export async function addWatch(symbol: string) {
  const r = await http.post('/api/watchlist/add', { symbol })
  return r.data
}

export async function removeWatch(symbol: string) {
  const r = await http.delete(`/api/watchlist/remove/${encodeURIComponent(symbol)}`)
  return r.data
}

export async function analyzeOne(symbol: string) {
  const r = await http.post('/api/watchlist/analyze', { symbols: [symbol] })
  return r.data
}

export type HistoryItem = {
  时间?: string
  综合评分?: number | null
  操作建议?: string | null
  分析理由摘要?: string | null
  AI详细分析?: string | null
}

export async function listHistory(symbol: string, page = 1, page_size = 10) {
  const r = await http.get(`/api/watchlist/history/${encodeURIComponent(symbol)}`, { params: { page, page_size } })
  return r.data as { symbol: string; total: number; page: number; page_size: number; items: HistoryItem[] }
}