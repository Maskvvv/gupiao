import React, { useState, useEffect } from 'react';
import {
  Card,
  Form,
  Input,
  Select,
  Button,
  Row,
  Col,
  InputNumber,
  Switch,
  Space,
  Progress,
  Statistic,
  Tag,
  Typography,
  Alert,
  List,
  Empty,
  message,
  Skeleton,
  Timeline,
  Spin,
  Badge,
  Tooltip
} from 'antd';
import {
  SearchOutlined,
  ThunderboltOutlined,
  PlayCircleOutlined,
  PauseCircleOutlined,
  ReloadOutlined,
  CheckCircleOutlined,
  CloseCircleOutlined,
  LoadingOutlined,
  RobotOutlined,
  BarChartOutlined,
  ClockCircleOutlined,
  BulbOutlined
} from '@ant-design/icons';
import { useMutation, useQuery } from '@tanstack/react-query';
import { taskApi } from '../../api/tasks';
import type { KeywordRecommendationRequest, RecommendationTask, TaskResult } from '../../types/tasks';
import RecommendationResultCard from './RecommendationResultCard';

const { Option } = Select;
const { Text } = Typography;

const StreamingKeywordForm: React.FC = () => {
  const [form] = Form.useForm();
  const [currentTaskId, setCurrentTaskId] = useState<string | null>(null);
  const [isStreaming, setIsStreaming] = useState(false);
  const [results, setResults] = useState<TaskResult[]>([]);
  const [eventSource, setEventSource] = useState<EventSource | null>(null);
  const [aiPhase, setAiPhase] = useState<'idle' | 'screening' | 'analyzing' | 'completed'>('idle');
  const [screeningStartTime, setScreeningStartTime] = useState<number | null>(null);
  const [screeningDuration, setScreeningDuration] = useState<number>(0);
  const [showOptimizationTips, setShowOptimizationTips] = useState(false);
  const [estimatedTime, setEstimatedTime] = useState(0);
  const [screeningProgress, setScreeningProgress] = useState(0);
  const [encouragementText, setEncouragementText] = useState('');
  const [screeningStats, setScreeningStats] = useState({ processed: 0, total: 4000 });

  // 鼓励文案数组
  const encouragementMessages = [
    '🎯 AI正在为您精挑细选最优质的投资机会...',
    '💎 好股票值得等待，AI正在深度挖掘价值洼地...',
    '🚀 智能算法正在分析市场趋势，寻找潜力股...',
    '⭐ 耐心一点，AI正在为您筛选明日之星...',
    '🔥 数据海洋中淘金，AI正在发现隐藏的投资机会...',
    '💰 好的投资需要时间验证，AI正在严格把关...',
    '🎪 让AI为您做功课，专业的事交给专业的算法...',
    '🌟 每一秒的等待都是为了更精准的推荐...'
  ];

  // 创建任务的 mutation
  const createTaskMutation = useMutation({
    mutationFn: async (request: KeywordRecommendationRequest) => {
      return await taskApi.createAndStartKeywordRecommendation(request);
    },
    onSuccess: (data) => {
      setCurrentTaskId(data.task_id);
      setIsStreaming(true);
      startSSEConnection(data.task_id);
      message.success('任务创建成功，开始流式推荐');
    },
    onError: (error) => {
      console.error('创建任务失败:', error);
      message.error('创建任务失败，请重试');
    }
  });

  // 启动任务的 mutation
  const startTaskMutation = useMutation({
    mutationFn: async (taskId: string) => {
      return await taskApi.startTask(taskId);
    },
    onSuccess: () => {
      message.success('任务启动成功');
    },
    onError: (error) => {
      console.error('启动任务失败:', error);
      message.error('启动任务失败，请重试');
    }
  });

  // 取消任务的 mutation
  const cancelTaskMutation = useMutation({
    mutationFn: async (taskId: string) => {
      return await taskApi.cancelTask(taskId);
    },
    onSuccess: () => {
      setIsStreaming(false);
      stopSSEConnection();
      message.success('任务已取消');
    },
    onError: (error) => {
      console.error('取消任务失败:', error);
      message.error('取消任务失败，请重试');
    }
  });

  // 查询当前任务状态
  const { data: currentTask } = useQuery({
    queryKey: ['taskStatus', currentTaskId],
    queryFn: () => currentTaskId ? taskApi.getTaskStatus(currentTaskId) : null,
    enabled: !!currentTaskId,
    refetchInterval: isStreaming ? 2000 : false,
  });

  // 查询任务结果
  const { data: taskResults } = useQuery({
    queryKey: ['taskResults', currentTaskId],
    queryFn: () => currentTaskId ? taskApi.getTaskResults(currentTaskId, true) : [],
    enabled: !!currentTaskId && currentTask?.status === 'completed',
  });

  // 启动SSE连接
  const startSSEConnection = (taskId: string) => {
    if (eventSource) {
      eventSource.close();
    }

    const url = `/api/v2/tasks/${taskId}/stream`;
    const source = new EventSource(url);

    source.onopen = () => {
      console.log('SSE连接已建立');
    };

    source.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data);
        console.log('收到SSE消息:', data);
        
        if (data.event === 'task_update') {
          // 任务状态更新已通过React Query处理
        } else if (data.event === 'task_completed') {
          setIsStreaming(false);
          message.success('推荐任务完成');
        } else if (data.event === 'task_failed') {
          setIsStreaming(false);
          message.error('推荐任务失败: ' + (data.data?.error || '未知错误'));
        } else if (data.event === 'recommendation_result') {
          setResults(prev => [...prev, data.data]);
        }
      } catch (error) {
        console.error('解析SSE消息失败:', error);
      }
    };

    source.onerror = (error) => {
      console.error('SSE连接错误:', error);
      if (source.readyState === EventSource.CLOSED) {
        setIsStreaming(false);
      }
    };

    setEventSource(source);
  };

  // 停止SSE连接
  const stopSSEConnection = () => {
    if (eventSource) {
      eventSource.close();
      setEventSource(null);
    }
  };

  // 监控AI阶段变化
  useEffect(() => {
    if (currentTask) {
      if (currentTask.status === 'running' && currentTask.progress_percent < 5) {
        // 任务刚开始，可能在AI股票筛选阶段
        if (aiPhase !== 'screening') {
          setAiPhase('screening');
          setScreeningStartTime(Date.now());
          setShowOptimizationTips(false);
        }
      } else if (currentTask.progress_percent >= 5) {
        // 进入股票分析阶段
        if (aiPhase === 'screening') {
          setAiPhase('analyzing');
          if (screeningStartTime) {
            setScreeningDuration(Date.now() - screeningStartTime);
          }
        }
      }
      
      if (currentTask.status === 'completed') {
        setAiPhase('completed');
      }
    }
  }, [currentTask, aiPhase, screeningStartTime]);
  
  // 监控筛选阶段时长，超过8秒显示优化提示
  useEffect(() => {
    if (aiPhase === 'screening' && screeningStartTime) {
      const timer = setInterval(() => {
        const elapsed = Date.now() - screeningStartTime;
        const progress = Math.min((elapsed / 15000) * 100, 95); // 15秒内完成筛选
        setScreeningProgress(progress);
        
        // 动态估算剩余时间
        const remaining = Math.max(15 - elapsed / 1000, 0);
        setEstimatedTime(remaining);
        
        // 模拟筛选统计数据
        const processedCount = Math.min(Math.floor((elapsed / 15000) * 4000), 3950);
        setScreeningStats({ processed: processedCount, total: 4000 });
        
        // 每3秒随机切换鼓励文案
        if (Math.floor(elapsed / 3000) !== Math.floor((elapsed - 500) / 3000)) {
          const randomIndex = Math.floor(Math.random() * encouragementMessages.length);
          setEncouragementText(encouragementMessages[randomIndex]);
        }
        
        if (elapsed > 8000 && !showOptimizationTips) {
          setShowOptimizationTips(true);
        }
      }, 500);
      
      return () => clearInterval(timer);
    }
  }, [aiPhase, screeningStartTime, showOptimizationTips, encouragementMessages]);
  useEffect(() => {
    if (aiPhase === 'screening' && screeningStartTime) {
      const timer = setTimeout(() => {
        setShowOptimizationTips(true);
      }, 8000); // 8秒后显示提示
      
      return () => clearTimeout(timer);
    }
  }, [aiPhase, screeningStartTime]);

  // 组件卸载时清理SSE连接
  useEffect(() => {
    return () => {
      stopSSEConnection();
    };
  }, []);

  // 处理表单提交
  const handleSubmit = (values: any) => {
    const request: KeywordRecommendationRequest = {
      keyword: values.keyword,
      period: values.period,
      max_candidates: values.max_candidates,
      weights: {
        technical: values.technical_weight,
        macro_sentiment: values.macro_weight,
        news_events: values.news_weight,
      },
      filter_config: {
        exclude_st: values.exclude_st,
        min_market_cap: values.min_market_cap,
        board: values.board === 'all' ? undefined : values.board,
      },
      ai_config: {
        provider: values.provider,
        temperature: values.temperature,
      },
      priority: 1
    };

    createTaskMutation.mutate(request);
  };

  return (
    <div className="streaming-keyword-form">
      <Card 
        title={
          <span>
            <SearchOutlined />
            关键词流式推荐
          </span>
        }
        extra={
          currentTaskId && (
            <Space>
              {currentTask?.status === 'pending' && (
                <Button 
                  type="primary" 
                  icon={<PlayCircleOutlined />}
                  onClick={() => startTaskMutation.mutate(currentTaskId)}
                  loading={startTaskMutation.isPending}
                >
                  启动任务
                </Button>
              )}
              {currentTask?.status === 'running' && (
                <Button 
                  danger 
                  icon={<PauseCircleOutlined />}
                  onClick={() => cancelTaskMutation.mutate(currentTaskId)}
                  loading={cancelTaskMutation.isPending}
                >
                  取消任务
                </Button>
              )}
              <Button 
                icon={<ReloadOutlined />}
                onClick={() => {
                  setCurrentTaskId(null);
                  setResults([]);
                  setIsStreaming(false);
                  stopSSEConnection();
                  form.resetFields();
                }}
              >
                重新开始
              </Button>
            </Space>
          )
        }
      >
        {!currentTaskId ? (
          <Form
            form={form}
            layout="vertical"
            onFinish={handleSubmit}
            initialValues={{
              period: '1y',
              max_candidates: 5,
              exclude_st: true,
              board: 'all',
              technical_weight: 0.4,
              macro_weight: 0.35,
              news_weight: 0.25,
              temperature: 0.7
            }}
          >
            <Row gutter={16}>
              <Col span={12}>
                <Form.Item
                  name="keyword"
                  label="关键词"
                  rules={[{ required: true, message: '请输入关键词' }]}
                >
                  <Input placeholder="例如：新能源、人工智能、医药等" />
                </Form.Item>
              </Col>
              <Col span={6}>
                <Form.Item name="period" label="分析周期">
                  <Select>
                    <Option value="1y">1年</Option>
                    <Option value="6mo">6个月</Option>
                    <Option value="3mo">3个月</Option>
                    <Option value="1mo">1个月</Option>
                  </Select>
                </Form.Item>
              </Col>
              <Col span={6}>
                <Form.Item name="max_candidates" label="最大候选数">
                  <InputNumber min={5} max={100} style={{ width: '100%' }} />
                </Form.Item>
              </Col>
            </Row>

            <Row gutter={16}>
              <Col span={6}>
                <Form.Item name="board" label="板块筛选">
                  <Select>
                    <Option value="all">全部板块</Option>
                    <Option value="main">主板</Option>
                    <Option value="gem">创业板</Option>
                    <Option value="star">科创板</Option>
                  </Select>
                </Form.Item>
              </Col>
              <Col span={6}>
                <Form.Item name="exclude_st" label="排除ST" valuePropName="checked">
                  <Switch />
                </Form.Item>
              </Col>
              <Col span={6}>
                <Form.Item name="min_market_cap" label="最小市值(亿)">
                  <InputNumber min={0} step={10} style={{ width: '100%' }} />
                </Form.Item>
              </Col>
              <Col span={6}>
                <Form.Item name="provider" label="AI提供商">
                  <Select placeholder="默认">
                    <Option value="openai">OpenAI</Option>
                    <Option value="deepseek">DeepSeek</Option>
                    <Option value="gemini">Gemini</Option>
                  </Select>
                </Form.Item>
              </Col>
            </Row>

            <Row gutter={16}>
              <Col span={6}>
                <Form.Item name="technical_weight" label="技术权重">
                  <InputNumber min={0} max={1} step={0.1} style={{ width: '100%' }} />
                </Form.Item>
              </Col>
              <Col span={6}>
                <Form.Item name="macro_weight" label="宏观权重">
                  <InputNumber min={0} max={1} step={0.1} style={{ width: '100%' }} />
                </Form.Item>
              </Col>
              <Col span={6}>
                <Form.Item name="news_weight" label="新闻权重">
                  <InputNumber min={0} max={1} step={0.1} style={{ width: '100%' }} />
                </Form.Item>
              </Col>
              <Col span={6}>
                <Form.Item name="temperature" label="AI创造性">
                  <InputNumber min={0} max={2} step={0.1} style={{ width: '100%' }} />
                </Form.Item>
              </Col>
            </Row>

            <Form.Item>
              <Button 
                type="primary" 
                htmlType="submit" 
                loading={createTaskMutation.isPending}
                icon={createTaskMutation.isPending ? <LoadingOutlined /> : <ThunderboltOutlined />}
                size="large"
                style={{ minWidth: 160 }}
              >
                {createTaskMutation.isPending ? '创建任务中...' : '开始关键词推荐'}
              </Button>
              <div style={{ marginTop: 8, fontSize: '12px', color: '#666' }}>
                🚀 已优化策略：智能缓存 + 超时保护 + 并行处理
              </div>
            </Form.Item>
          </Form>
        ) : (
          <div>
            {/* 任务状态显示 */}
            {currentTask && (
              <Card size="small" style={{ marginBottom: 16 }}>
                {/* AI阶段指示器 */}
                {aiPhase !== 'idle' && (
                  <div style={{ marginBottom: 16 }}>
                    <Timeline>
                      <Timeline.Item 
                        color={aiPhase === 'screening' ? 'blue' : 'green'}
                        dot={aiPhase === 'screening' ? <LoadingOutlined spin /> : <CheckCircleOutlined />}
                      >
                        <div>
                          <Text strong>🧠 AI智能筛选</Text>
                          {aiPhase === 'screening' && (
                            <>
                              <Tag color="processing" style={{ marginLeft: 8 }}>筛选中</Tag>
                              <div style={{ marginTop: 8 }}>
                                <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                                  <Text type="secondary">🔍 正在分析全市场股票池...</Text>
                                  {estimatedTime > 0 && (
                                    <Tag color="cyan">预计还需 {Math.ceil(estimatedTime)}秒</Tag>
                                  )}
                                </div>
                                {screeningProgress > 0 && (
                                  <Progress 
                                    percent={Math.round(screeningProgress)} 
                                    size="small" 
                                    status="active"
                                    strokeColor={{
                                      '0%': '#108ee9',
                                      '100%': '#87d068',
                                    }}
                                    style={{ marginTop: 4, maxWidth: 200 }}
                                  />
                                )}
                              </div>
                            </>
                          )}
                          {aiPhase !== 'screening' && screeningDuration > 0 && (
                            <>
                              <Tag color="success" style={{ marginLeft: 8 }}>已完成</Tag>
                              <Text type="secondary" style={{ marginLeft: 8 }}>
                                ⚡ 耗时 {(screeningDuration / 1000).toFixed(1)}秒
                              </Text>
                            </>
                          )}
                        </div>
                      </Timeline.Item>
                      <Timeline.Item 
                        color={aiPhase === 'analyzing' ? 'blue' : aiPhase === 'completed' ? 'green' : 'gray'}
                        dot={aiPhase === 'analyzing' ? <LoadingOutlined spin /> : 
                          aiPhase === 'completed' ? <CheckCircleOutlined /> : <ClockCircleOutlined />
                        }
                      >
                        <div>
                          <Text strong>📊 深度分析</Text>
                          {aiPhase === 'analyzing' && (
                            <>
                              <Tag color="processing" style={{ marginLeft: 8 }}>分析中</Tag>
                              <div style={{ marginTop: 8 }}>
                                <Text type="secondary">⚡ 并行分析候选股票，生成推荐评分...</Text>
                                <div style={{ marginTop: 4 }}>
                                  <Tag color="blue">🧠 AI评估</Tag>
                                  <Tag color="green">📈 技术分析</Tag>
                                  <Tag color="orange">📰 基本面</Tag>
                                </div>
                              </div>
                            </>
                          )}
                          {aiPhase === 'completed' && (
                            <>
                              <Tag color="success" style={{ marginLeft: 8 }}>✅ 已完成</Tag>
                              <Text type="secondary" style={{ marginLeft: 8 }}>🎉 推荐结果已生成</Text>
                            </>
                          )}
                        </div>
                      </Timeline.Item>
                    </Timeline>
                  </div>
                )}
                
                {/* 优化提示 */}
                {showOptimizationTips && aiPhase === 'screening' && (
                  <Alert
                    type="info"
                    icon={<BulbOutlined />}
                    message="性能优化提示"
                    description={
                      <div>
                        <div>AI股票筛选正在进行中，已实施以下优化策略：</div>
                        <ul style={{ marginTop: 8, marginBottom: 0, paddingLeft: 20 }}>
                          <li>🧠 <strong>智能缓存</strong>：相同关键词1小时内直接使用缓存结果</li>
                          <li>⚡ <strong>超时保护</strong>：AI调用设置10秒超时，超时自动降级</li>
                          <li>🔄 <strong>降级策略</strong>：AI失败时自动切换到关键词匹配</li>
                          <li>⚙️ <strong>简化提示词</strong>：减少AI传输延迟</li>
                        </ul>
                      </div>
                    }
                    style={{ marginBottom: 16 }}
                    closable
                    onClose={() => setShowOptimizationTips(false)}
                  />
                )}
                
                <Row gutter={16}>
                  <Col span={6}>
                    <Statistic 
                      title="任务状态" 
                      value={currentTask.status} 
                      valueStyle={{ 
                        color: currentTask.status === 'completed' ? '#3f8600' : 
                               currentTask.status === 'failed' ? '#cf1322' : '#1890ff' 
                      }}
                      prefix={
                        currentTask.status === 'running' ? <RobotOutlined /> :
                        currentTask.status === 'completed' ? <CheckCircleOutlined /> :
                        currentTask.status === 'failed' ? <CloseCircleOutlined /> : null
                      }
                    />
                  </Col>
                  <Col span={6}>
                    <Statistic 
                      title="总体进度" 
                      value={`${currentTask.progress_percent.toFixed(1)}%`}
                      prefix={<BarChartOutlined />}
                    />
                  </Col>
                  <Col span={6}>
                    <Statistic 
                      title="已处理" 
                      value={`${currentTask.completed_symbols}/${currentTask.total_symbols}`}
                      prefix={<CheckCircleOutlined />}
                    />
                  </Col>
                  <Col span={6}>
                    <Badge count={currentTask.successful_count} showZero>
                      <Statistic title="成功数" value={currentTask.successful_count} />
                    </Badge>
                  </Col>
                </Row>
                
                {currentTask.progress_percent > 0 && (
                  <>
                    <Progress 
                      percent={Math.round(currentTask.progress_percent)} 
                      status={currentTask.status === 'failed' ? 'exception' : 'active'}
                      style={{ marginTop: 16 }}
                      strokeColor={{
                        '0%': '#108ee9',
                        '100%': '#87d068',
                      }}
                    />
                    
                    {aiPhase === 'screening' && currentTask.progress_percent < 5 && (
                      <div style={{ 
                        textAlign: 'center', 
                        marginTop: 12,
                        padding: '12px',
                        background: 'linear-gradient(135deg, #f6f9fc 0%, #e9f4ff 100%)',
                        borderRadius: '6px',
                        border: '1px solid #d9e9ff'
                      }}>
                        <div style={{ fontSize: '14px', fontWeight: 'bold', color: '#1890ff', marginBottom: 6 }}>
                          🤖 AI智能筛选中...
                        </div>
                        <Text type="secondary" style={{ fontSize: '12px' }}>
                          {encouragementText || '正在分析全市场股票，为您精选优质标的'}
                        </Text>
                        {estimatedTime > 0 && (
                          <div style={{ marginTop: 6, fontSize: '11px', color: '#666' }}>
                            预计还需 <Text strong style={{ color: '#1890ff' }}>{Math.ceil(estimatedTime)}</Text> 秒
                          </div>
                        )}
                      </div>
                    )}
                  </>
                )}
                
                {currentTask.current_symbol && (
                  <div style={{ marginTop: 12 }}>
                    <Text type="secondary">当前分析: </Text>
                    <Tooltip title="正在进行技术分析和AI深度评估">
                      <Tag color="processing">
                        {currentTask.current_symbol}
                      </Tag>
                    </Tooltip>
                    {aiPhase === 'analyzing' && (
                      <Text type="secondary" style={{ marginLeft: 8 }}>
                        🧠 并行分析中，最夒3只股票同时处理
                      </Text>
                    )}
                  </div>
                )}
                
                {currentTask.error_message && (
                  <Alert
                    type="error"
                    message="任务执行错误"
                    description={
                      <div>
                        <div>{currentTask.error_message}</div>
                        <div style={{ marginTop: 8 }}>
                          <Text type="secondary">提示：系统已启用多重容错机制，可尝试重新开始或联系管理员。</Text>
                        </div>
                      </div>
                    }
                    style={{ marginTop: 16 }}
                    showIcon
                  />
                )}
              </Card>
            )}

            {/* 实时结果显示 */}
            {results.length > 0 && (
              <Card title="实时推荐结果" size="small" style={{ marginBottom: 16 }}>
                <List
                  grid={{ gutter: 16, column: 2 }}
                  dataSource={results}
                  renderItem={(item) => (
                    <List.Item>
                      <RecommendationResultCard result={item} />
                    </List.Item>
                  )}
                />
              </Card>
            )}

            {/* 最终结果显示 */}
            {taskResults && taskResults.length > 0 && (
              <Card 
                title={
                  <span>
                    <CheckCircleOutlined style={{ color: '#52c41a' }} />
                    最终推荐结果 ({taskResults.length}个)
                  </span>
                }
              >
                <List
                  grid={{ gutter: 16, column: 2 }}
                  dataSource={taskResults}
                  renderItem={(item) => (
                    <List.Item>
                      <RecommendationResultCard result={item} />
                    </List.Item>
                  )}
                />
              </Card>
            )}

            {/* 空状态 */}
            {currentTask?.status === 'completed' && (!taskResults || taskResults.length === 0) && results.length === 0 && (
              <Empty 
                description="未找到符合条件的推荐结果"
                image={Empty.PRESENTED_IMAGE_SIMPLE}
              />
            )}
          </div>
        )}
      </Card>
    </div>
  );
};

export default StreamingKeywordForm;