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

// 单股分析接口 - 现在返回任务信息
export type TaskResponse = {
  task_id: string
  stream_url: string
  status: string
  message: string
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
  return r.data as TaskResponse
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

// 批量分析接口 - 使用新的任务管理中心
export type WatchlistBatchRequest = {
  symbols?: string[]
  period?: string
  weights?: Record<string, number>
  provider?: string
  temperature?: number
  api_key?: string
}

export type WatchlistReanalyzeRequest = {
  symbol: string
  period?: string
  weights?: Record<string, number>
  provider?: string
  temperature?: number
  api_key?: string
}

// 创建自选股票批量分析任务
export async function createWatchlistBatchTask(payload: WatchlistBatchRequest) {
  const r = await http.post('/api/v2/watchlist/batch', payload)
  return r.data as TaskResponse
}

// 创建并启动自选股票批量分析任务
export async function startWatchlistBatchTask(payload: WatchlistBatchRequest) {
  const r = await http.post('/api/v2/watchlist/batch/start', payload)
  return r.data as TaskResponse
}

// 创建自选股票单股重新分析任务
export async function createWatchlistReanalyzeTask(payload: WatchlistReanalyzeRequest) {
  const r = await http.post('/api/v2/watchlist/reanalyze', payload)
  return r.data as TaskResponse
}

// 创建并启动自选股票单股重新分析任务
export async function startWatchlistReanalyzeTask(payload: WatchlistReanalyzeRequest) {
  const r = await http.post('/api/v2/watchlist/reanalyze/start', payload)
  return r.data as TaskResponse
}

// 兼容性：保留旧的批量分析接口名称，但使用新的任务管理接口
export async function startBatchAnalyze(payload: WatchlistBatchRequest) {
  return startWatchlistBatchTask(payload)
}

// 任务管理相关接口
export type TaskStatus = {
  task_id: string
  task_type: string
  status: string
  progress: number
  total_items: number
  processed_items: number
  created_at: string
  updated_at: string
  user_input_summary?: string
  filter_summary?: string
  execution_strategy?: string
  result_summary?: string
  error_message?: string
}

export type TaskResult = {
  task_id: string
  status: string
  result?: any
  error?: string
}

// 获取任务状态
export async function getTaskStatus(task_id: string) {
  const r = await http.get(`/api/v2/tasks/${encodeURIComponent(task_id)}/status`)
  return r.data as TaskStatus
}

// 获取任务结果
export async function getTaskResult(task_id: string) {
  const r = await http.get(`/api/v2/tasks/${encodeURIComponent(task_id)}/results`)
  return r.data as TaskResult
}

// 获取任务列表
export async function getTaskList(task_type?: string, status?: string, limit = 10) {
  const params: any = { limit }
  if (task_type) params.task_type = task_type
  if (status) params.status = status
  const r = await http.get('/api/v2/tasks', { params })
  return r.data as { tasks: TaskStatus[] }
}

// 取消任务
export async function cancelTask(task_id: string) {
  const r = await http.post(`/api/v2/tasks/${encodeURIComponent(task_id)}/cancel`)
  return r.data
}

// 重试任务
export async function retryTask(task_id: string) {
  const r = await http.post(`/api/v2/tasks/${encodeURIComponent(task_id)}/retry`)
  return r.data as TaskResponse
}