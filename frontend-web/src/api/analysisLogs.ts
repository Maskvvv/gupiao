/**
 * 分析日志API函数
 */
import axios from 'axios';
import type { 
  AnalysisLog, 
  LogStats, 
  AIScreeningLog, 
  PerformanceLog, 
  StockAnalysisLog,
  LogQueryParams 
} from '../types/analysisLogs';

const API_BASE_URL = '/api/v2';

const apiClient = axios.create({
  baseURL: API_BASE_URL,
  timeout: 30000,
});

export const analysisLogApi = {
  /**
   * 获取任务的分析日志
   */
  async getTaskLogs(taskId: string, params?: LogQueryParams): Promise<AnalysisLog[]> {
    const queryParams = new URLSearchParams();
    
    if (params?.logTypes) {
      params.logTypes.forEach(type => {
        queryParams.append('log_types', type);
      });
    }
    
    if (params?.logLevel) {
      queryParams.set('log_level', params.logLevel);
    }
    
    if (params?.includeDebug !== undefined) {
      queryParams.set('include_debug', params.includeDebug.toString());
    }
    
    const queryString = queryParams.toString();
    const url = `/analysis-logs/tasks/${taskId}/logs${queryString ? `?${queryString}` : ''}`;
    
    const response = await apiClient.get(url);
    return response.data;
  },

  /**
   * 获取任务日志统计信息
   */
  async getTaskLogStats(taskId: string): Promise<LogStats> {
    const response = await apiClient.get(`/analysis-logs/tasks/${taskId}/logs/stats`);
    return response.data;
  },

  /**
   * 获取AI筛选专项日志
   */
  async getAIScreeningLogs(taskId: string): Promise<AIScreeningLog> {
    const response = await apiClient.get(`/analysis-logs/tasks/${taskId}/logs/ai-screening`);
    return response.data;
  },

  /**
   * 获取性能监控日志
   */
  async getPerformanceLogs(taskId: string): Promise<PerformanceLog> {
    const response = await apiClient.get(`/analysis-logs/tasks/${taskId}/logs/performance`);
    return response.data;
  },

  /**
   * 获取特定股票的分析日志
   */
  async getStockAnalysisLogs(taskId: string, symbol: string): Promise<StockAnalysisLog> {
    const response = await apiClient.get(`/analysis-logs/tasks/${taskId}/logs/stock/${symbol}`);
    return response.data;
  }
};