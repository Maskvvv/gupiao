import axios from 'axios';
import type { 
  RecommendationTask, 
  TaskResult, 
  CreateTaskResponse,
  TaskListResponse,
  AIRecommendationRequest,
  KeywordRecommendationRequest,
  MarketRecommendationRequest
} from '../types/tasks';

const API_BASE_URL = '/api/v2';

const apiClient = axios.create({
  baseURL: API_BASE_URL,
  timeout: 30000,
});

export const taskApi = {
  // 创建任务
  async createAIRecommendation(request: AIRecommendationRequest): Promise<CreateTaskResponse> {
    const response = await apiClient.post('/recommend/ai', request);
    return response.data;
  },

  async createKeywordRecommendation(request: KeywordRecommendationRequest): Promise<CreateTaskResponse> {
    const response = await apiClient.post('/recommend/keyword', request);
    return response.data;
  },

  async createMarketRecommendation(request: MarketRecommendationRequest): Promise<CreateTaskResponse> {
    const response = await apiClient.post('/recommend/market', request);
    return response.data;
  },

  // 创建并启动任务
  async createAndStartAIRecommendation(request: AIRecommendationRequest): Promise<CreateTaskResponse> {
    const response = await apiClient.post('/recommend/ai/start', request);
    return response.data;
  },

  async createAndStartKeywordRecommendation(request: KeywordRecommendationRequest): Promise<CreateTaskResponse> {
    const response = await apiClient.post('/recommend/keyword/start', request);
    return response.data;
  },

  async createAndStartMarketRecommendation(request: MarketRecommendationRequest): Promise<CreateTaskResponse> {
    const response = await apiClient.post('/recommend/market/start', request);
    return response.data;
  },

  // 任务管理
  async startTask(taskId: string): Promise<{ message: string; task_id: string }> {
    const response = await apiClient.post(`/tasks/${taskId}/start`);
    return response.data;
  },

  async cancelTask(taskId: string): Promise<{ message: string; task_id: string }> {
    const response = await apiClient.post(`/tasks/${taskId}/cancel`);
    return response.data;
  },

  async retryTask(taskId: string): Promise<{ message: string; task_id: string }> {
    const response = await apiClient.post(`/tasks/${taskId}/retry`);
    return response.data;
  },

  // 查询任务
  async getTaskStatus(taskId: string): Promise<RecommendationTask> {
    const response = await apiClient.get(`/tasks/${taskId}/status`);
    return response.data;
  },

  async listTasks(params?: {
    status?: string;
    task_type?: string;
    limit?: number;
    offset?: number;
  }): Promise<TaskListResponse> {
    const response = await apiClient.get('/tasks', { params });
    return response.data;
  },

  async getTaskResults(taskId: string, recommendedOnly: boolean = false): Promise<TaskResult[]> {
    const response = await apiClient.get(`/tasks/${taskId}/results`, {
      params: { recommended_only: recommendedOnly }
    });
    return response.data.results;
  },

  // 获取任务实时进度
  async getTaskProgress(taskId: string): Promise<any[]> {
    const response = await apiClient.get(`/tasks/${taskId}/progress`);
    return response.data.progress;
  },

  // 系统状态
  async getSystemStatus(): Promise<{
    running_tasks: number;
    running_task_ids: string[];
    total_connections: number;
    task_connections: Record<string, number>;
    max_concurrent_tasks: number;
    system_health: string;
  }> {
    const response = await apiClient.get('/system/status');
    return response.data;
  },

  // 兼容性接口
  async legacyAnalyze(request: AIRecommendationRequest): Promise<{
    task_id: string;
    stream_url: string;
    status: string;
    symbols: string[];
    message: string;
  }> {
    const response = await apiClient.post('/legacy/analyze', request);
    return response.data;
  }
};

// 响应拦截器
apiClient.interceptors.response.use(
  (response) => response,
  (error) => {
    console.error('API请求失败:', error);
    
    if (error.response?.status === 404) {
      throw new Error('请求的资源不存在');
    } else if (error.response?.status === 500) {
      throw new Error('服务器内部错误');
    } else if (error.code === 'ECONNABORTED') {
      throw new Error('请求超时');
    }
    
    throw error;
  }
);

export default taskApi;