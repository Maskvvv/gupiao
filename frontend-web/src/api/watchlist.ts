import { http } from './http'

export type WatchItem = {
  股票代码: string
  股票名称?: string
  综合评分?: number | null
  操作建议?: string | null
  分析理由摘要?: string | null
  AI详细分析?: string | null
  最近分析时间?: string | null
  加入日期?: string | null
  '累计涨跌幅(%)'?: number | null
  累计涨跌额?: number | null
  // 新增字段：AI信心、融合分（用于Watchlist页面展示与Tooltip）
  AI信心?: number | null
  融合分?: number | null
}

export async function listWatchlist() {
  const r = await http.get<{ items: WatchItem[] }>(' /api/watchlist/list'.trim())
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

export async function analyzeOne(
  symbol: string,
  opts?: { period?: string; weights?: Record<string, number>; provider?: string; temperature?: number; api_key?: string }
) {
  const payload: any = { symbols: [symbol] }
  // 仅在存在时附加可选参数，保持后端默认值
  if (opts?.period) payload.period = opts.period
  if (opts?.weights) payload.weights = opts.weights
  if (opts?.provider) payload.provider = opts.provider
  if (typeof opts?.temperature === 'number') payload.temperature = opts.temperature
  if (opts?.api_key) payload.api_key = opts?.api_key
  const r = await http.post('/api/watchlist/analyze', payload)
  return r.data
}

export type HistoryItem = {
  时间?: string
  综合评分?: number | null
  操作建议?: string | null
  分析理由摘要?: string | null
  AI详细分析?: string | null
  AI信心?: number | null
  融合分?: number | null
}

export async function listHistory(symbol: string, page = 1, page_size = 10) {
  const r = await http.get(`/api/watchlist/history/${encodeURIComponent(symbol)}`, { params: { page, page_size } })
  return r.data as { symbol: string; total: number; page: number; page_size: number; items: HistoryItem[] }
}

export type BatchStartResp = { task_id?: string }
export type BatchStatusResp = { status?: string; done?: number; total?: number; percent?: number }
export type BatchResultItem = {
  股票代码: string
  股票名称?: string
  评分?: number | null
  建议动作?: string | null
  理由简述?: string | null
  AI详细分析?: string | null
  错误?: string | null
}
export type BatchResultResp = { items?: BatchResultItem[]; status?: string; error?: string }

export async function startBatchAnalyze(payload: { symbols?: string[]; period?: string; weights?: Record<string, number>; provider?: string; temperature?: number; api_key?: string }) {
  const r = await http.post('/api/watchlist/analyze/batch/start', payload)
  return r.data as BatchStartResp
}

export async function getBatchStatus(task_id: string) {
  const r = await http.get(`/api/watchlist/analyze/batch/status/${encodeURIComponent(task_id)}`)
  return r.data as BatchStatusResp
}

export async function getBatchResult(task_id: string) {
  const r = await http.get(`/api/watchlist/analyze/batch/result/${encodeURIComponent(task_id)}`)
  return r.data as BatchResultResp
}