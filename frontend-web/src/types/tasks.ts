// 任务状态类型
export type TaskStatus = 'pending' | 'running' | 'completed' | 'failed' | 'cancelled';

// 任务类型
export type TaskType = 'ai' | 'keyword' | 'market';

// 推荐任务接口
export interface RecommendationTask {
  id: string;
  task_type: TaskType;
  status: TaskStatus;
  priority: number;
  created_at?: string;
  started_at?: string;
  completed_at?: string;
  updated_at?: string;
  total_symbols: number;
  completed_symbols: number;
  current_symbol?: string;
  current_phase?: string;
  progress_percent: number;
  successful_count: number;
  failed_count: number;
  final_recommendations: number;
  error_message?: string;
  execution_time_seconds?: number;
  is_running: boolean;
  
  // 任务详情字段
  request_params?: string;  // JSON字符串
  ai_config?: string;      // JSON字符串
  filter_config?: string;  // JSON字符串
  weights_config?: string; // JSON字符串
  
  // 新增的详情字段
  user_input_summary?: string;     // 用户输入摘要
  filter_summary?: string;         // 筛选条件摘要
  ai_prompt_used?: string;         // AI提示词
  execution_strategy?: string;     // 执行策略说明
  candidate_stocks_info?: string;  // 候选股票信息 (JSON)
}

// 推荐结果接口
export interface TaskResult {
  id: number;
  symbol: string;
  name?: string;
  technical_score?: number;
  ai_score?: number;
  fusion_score?: number;
  final_score?: number;
  action?: 'buy' | 'hold' | 'sell';
  ai_analysis?: string;
  ai_confidence?: number;
  summary?: string;
  rank_in_task?: number;
  is_recommended: boolean;
  recommendation_reason?: string;
  current_price?: number;
  analyzed_at?: string;
}

// 任务进度接口
export interface TaskProgress {
  id: number;
  task_id: string;
  timestamp: string;
  event_type: string;
  symbol?: string;
  phase?: string;
  progress_data?: any;
  ai_chunk_content?: string;
  accumulated_content?: string;
  status?: string;
  message?: string;
}

// 任务统计接口
export interface TaskStats {
  total: number;
  pending: number;
  running: number;
  completed: number;
  failed: number;
  cancelled: number;
}

// 任务列表响应接口
export interface TaskListResponse {
  tasks: RecommendationTask[];
  stats: TaskStats;
  pagination: {
    total: number;
    limit: number;
    offset: number;
    has_more: boolean;
  };
}

// 创建任务响应接口
export interface CreateTaskResponse {
  task_id: string;
  stream_url: string;
  status: string;
  message: string;
}

// AI推荐请求接口
export interface AIRecommendationRequest {
  symbols: string[];
  period?: string;
  weights?: {
    technical?: number;
    macro_sentiment?: number;
    news_events?: number;
  };
  ai_config?: {
    provider?: string;
    model?: string;
    temperature?: number;
    api_key?: string;
  };
  priority?: number;
}

// 关键词推荐请求接口
export interface KeywordRecommendationRequest {
  keyword: string;
  period?: string;
  max_candidates?: number;
  weights?: {
    technical?: number;
    macro_sentiment?: number;
    news_events?: number;
  };
  filter_config?: {
    exclude_st?: boolean;
    min_market_cap?: number;
    board?: string;
    max_candidates?: number;
  };
  ai_config?: {
    provider?: string;
    model?: string;
    temperature?: number;
    api_key?: string;
  };
  priority?: number;
}

// 全市场推荐请求接口
export interface MarketRecommendationRequest {
  period?: string;
  max_candidates?: number;
  weights?: {
    technical?: number;
    macro_sentiment?: number;
    news_events?: number;
  };
  filter_config?: {
    exclude_st?: boolean;
    min_market_cap?: number;
    board?: string;
  };
  ai_config?: {
    provider?: string;
    model?: string;
    temperature?: number;
    api_key?: string;
  };
  priority?: number;
}

// SSE事件接口
export interface SSEEvent {
  event: string;
  data: any;
  timestamp: string;
  task_id: string;
}

// 系统状态接口
export interface SystemStatus {
  running_tasks: number;
  running_task_ids: string[];
  total_connections: number;
  task_connections: Record<string, number>;
  max_concurrent_tasks: number;
  system_health: string;
}