/**
 * 分析日志相关类型定义
 */

export interface AnalysisLog {
  id: number;
  log_type: string;
  stock_symbol?: string;
  timestamp: string;
  log_level: string;
  log_message: string;
  log_details?: Record<string, any>;
  
  // AI相关字段
  ai_request_prompt?: string;
  ai_response_content?: string;
  ai_response_tokens?: number;
  ai_processing_time_ms?: number;
  ai_provider?: string;
  
  // 技术分析字段
  technical_indicators?: Record<string, any>;
  technical_score?: number;
  technical_signals?: Record<string, any>;
  
  // 融合评分字段
  fusion_components?: Record<string, any>;
  fusion_weights?: Record<string, any>;
  final_score?: number;
  
  // 性能监控字段
  memory_usage_mb?: number;
  cpu_time_ms?: number;
}

export interface LogStats {
  task_id: string;
  total_logs: number;
  error_count: number;
  warning_count: number;
  ai_analysis_count: number;
  technical_analysis_count: number;
  avg_ai_time_ms?: number;
  total_tokens?: number;
  first_log_time?: string;
  last_log_time?: string;
}

export interface AIScreeningLog {
  start_time?: string;
  end_time?: string;
  ai_requests: Array<{
    timestamp: string;
    prompt: string;
    response: string;
    processing_time_ms: number;
    tokens: number;
  }>;
  fallback_events: Array<{
    timestamp: string;
    reason: string;
    details: Record<string, any>;
  }>;
  errors: Array<{
    timestamp: string;
    error_message: string;
    details: Record<string, any>;
  }>;
  summary: {
    total_processing_time_ms: number;
    total_tokens: number;
    stocks_recommended: number;
  };
}

export interface PerformanceLog {
  ai_performance: {
    total_calls: number;
    total_time_ms: number;
    avg_time_ms: number;
    total_tokens: number;
    avg_tokens_per_call: number;
  };
  technical_performance: {
    total_analyses: number;
    avg_score: number;
  };
  timeline: Array<{
    timestamp: string;
    log_type: string;
    stock_symbol?: string;
    processing_time_ms?: number;
    memory_mb?: number;
  }>;
}

export interface StockAnalysisLog {
  stock_symbol: string;
  technical_analysis?: {
    timestamp: string;
    score: number;
    indicators: Record<string, any>;
    signals: Record<string, any>;
  };
  ai_analysis: {
    start_time?: string;
    end_time?: string;
    chunks: Array<{
      timestamp: string;
      chunk_content: string;
    }>;
    final_result?: {
      content: string;
      processing_time_ms: number;
      tokens: number;
    };
  };
  fusion_score?: {
    timestamp: string;
    components: Record<string, any>;
    weights: Record<string, any>;
    final_score: number;
  };
  errors: Array<{
    timestamp: string;
    error_message: string;
    details: Record<string, any>;
  }>;
}

export interface LogQueryParams {
  logTypes?: string[];
  logLevel?: string;
  includeDebug?: boolean;
}