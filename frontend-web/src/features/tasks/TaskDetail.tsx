import React, { useState, useEffect } from 'react';
import {
  Drawer,
  Tabs,
  Card,
  Descriptions,
  Tag,
  Progress,
  Table,
  Timeline,
  Alert,
  Spin,
  Button,
  Typography,
  Space,
  Modal,
  App
} from 'antd';
import { PlusOutlined, EyeOutlined } from '@ant-design/icons';
import { useQuery, useMutation } from '@tanstack/react-query';
import dayjs from 'dayjs';
import { taskApi } from '../../api/tasks';
import { StreamingProgress } from './StreamingProgress';
import AnalysisLogViewer from './AnalysisLogViewer';
import type { RecommendationTask, TaskResult, TaskProgress } from '../../types/tasks';

const { Text, Paragraph } = Typography;

interface TaskDetailProps {
  taskId: string;
  open: boolean;
  onClose: () => void;
  defaultActiveTab?: string;
}

export const TaskDetail: React.FC<TaskDetailProps> = ({ taskId, open, onClose, defaultActiveTab = 'overview' }) => {
  const [activeTab, setActiveTab] = useState(defaultActiveTab);

  // 当defaultActiveTab变化时更新activeTab
  useEffect(() => {
    if (open) {
      setActiveTab(defaultActiveTab);
    }
  }, [defaultActiveTab, open]);

  const { data: taskDetail, isLoading } = useQuery<RecommendationTask>({
    queryKey: ['task-detail', taskId],
    queryFn: () => taskApi.getTaskStatus(taskId),
    enabled: open,
    refetchInterval: (data) => data?.status === 'running' ? 2000 : false
  });

  const { data: results } = useQuery<TaskResult[]>({
    queryKey: ['task-results', taskId],
    queryFn: () => taskApi.getTaskResults(taskId),
    enabled: open && taskDetail?.status === 'completed'
  });

  const getStatusText = (status: string) => {
    const statusMap = {
      'pending': '等待中',
      'running': '执行中',
      'completed': '已完成',
      'failed': '失败',
      'cancelled': '已取消'
    };
    return statusMap[status as keyof typeof statusMap] || status;
  };

  const getStatusColor = (status: string) => {
    const colorMap = {
      'pending': 'default',
      'running': 'processing',
      'completed': 'success',
      'failed': 'error',
      'cancelled': 'warning'
    };
    return colorMap[status as keyof typeof colorMap] || 'default';
  };

  const getTaskTypeText = (type: string) => {
    const typeMap = {
      'ai': 'AI推荐',
      'keyword': '关键词推荐', 
      'market': '全市场推荐'
    };
    return typeMap[type as keyof typeof typeMap] || type;
  };

  const TaskOverview = ({ task }: { task: RecommendationTask }) => (
    <Card title="任务概览">
      <Descriptions bordered column={2}>
        <Descriptions.Item label="任务ID" span={2}>
          <Text copyable>{task.id}</Text>
        </Descriptions.Item>
        
        <Descriptions.Item label="任务类型">
          <Tag color="blue">{getTaskTypeText(task.task_type)}</Tag>
        </Descriptions.Item>
        
        <Descriptions.Item label="当前状态">
          <Tag color={getStatusColor(task.status)}>
            {getStatusText(task.status)}
          </Tag>
        </Descriptions.Item>
        
        <Descriptions.Item label="优先级">
          {task.priority}
        </Descriptions.Item>
        
        <Descriptions.Item label="执行进度">
          <Progress 
            percent={Math.round(task.progress_percent)} 
            status={task.status === 'failed' ? 'exception' : 'active'}
          />
        </Descriptions.Item>
        
        <Descriptions.Item label="股票处理">
          {task.completed_symbols} / {task.total_symbols}
        </Descriptions.Item>
        
        <Descriptions.Item label="当前处理">
          {task.current_symbol || '-'}
        </Descriptions.Item>
        
        <Descriptions.Item label="成功数量">
          <Text type="success">{task.successful_count}</Text>
        </Descriptions.Item>
        
        <Descriptions.Item label="失败数量">
          <Text type="danger">{task.failed_count}</Text>
        </Descriptions.Item>
        
        <Descriptions.Item label="最终推荐">
          <Text type="success">{task.final_recommendations}</Text>
        </Descriptions.Item>
        
        <Descriptions.Item label="执行时间">
          {task.execution_time_seconds ? `${Math.round(task.execution_time_seconds)}秒` : '-'}
        </Descriptions.Item>
        
        <Descriptions.Item label="创建时间">
          {task.created_at ? dayjs(task.created_at).format('YYYY-MM-DD HH:mm:ss') : '-'}
        </Descriptions.Item>
        
        <Descriptions.Item label="开始时间">
          {task.started_at ? dayjs(task.started_at).format('YYYY-MM-DD HH:mm:ss') : '-'}
        </Descriptions.Item>
        
        <Descriptions.Item label="完成时间">
          {task.completed_at ? dayjs(task.completed_at).format('YYYY-MM-DD HH:mm:ss') : '-'}
        </Descriptions.Item>
        
        {task.error_message && (
          <Descriptions.Item label="错误信息" span={2}>
            <Alert message={task.error_message} type="error" />
          </Descriptions.Item>
        )}
      </Descriptions>
    </Card>
  );

  const TaskDetailInfo = ({ task }: { task: RecommendationTask }) => {
    // 解析请求参数
    const requestParams = task.request_params ? JSON.parse(task.request_params) : {};
    // 解析筛选配置
    const filterConfig = task.filter_config ? JSON.parse(task.filter_config) : {};
    // 解析AI配置
    const aiConfig = task.ai_config ? JSON.parse(task.ai_config) : {};
    // 解析候选股票信息
    const candidateInfo = task.candidate_stocks_info ? JSON.parse(task.candidate_stocks_info) : null;
    
    return (
      <Space direction="vertical" size="large" style={{ width: '100%' }}>
        {/* 用户输入信息 */}
        <Card title="用户输入信息" size="small">
          <Descriptions bordered size="small" column={2}>
            <Descriptions.Item label="任务类型">
              <Tag color="blue">{getTaskTypeText(task.task_type)}</Tag>
            </Descriptions.Item>
            
            {task.user_input_summary && (
              <Descriptions.Item label="输入摘要" span={2}>
                {task.user_input_summary}
              </Descriptions.Item>
            )}
            
            {requestParams.keyword && (
              <Descriptions.Item label="关键词">
                <Tag color="orange">{requestParams.keyword}</Tag>
              </Descriptions.Item>
            )}
            
            {requestParams.max_candidates && (
              <Descriptions.Item label="最大候选数">
                {requestParams.max_candidates}
              </Descriptions.Item>
            )}
            
            {requestParams.period && (
              <Descriptions.Item label="分析周期">
                {requestParams.period}
              </Descriptions.Item>
            )}
          </Descriptions>
        </Card>
        
        {/* 筛选条件 */}
        <Card title="筛选条件" size="small">
          <Descriptions bordered size="small" column={2}>
            {task.filter_summary && (
              <Descriptions.Item label="筛选摘要" span={2}>
                {task.filter_summary}
              </Descriptions.Item>
            )}
            
            <Descriptions.Item label="排除ST股票">
              <Tag color={filterConfig.exclude_st ? 'success' : 'default'}>
                {filterConfig.exclude_st ? '是' : '否'}
              </Tag>
            </Descriptions.Item>
            
            {filterConfig.board && (
              <Descriptions.Item label="板块筛选">
                <Tag color="geekblue">
                  {filterConfig.board === 'main' ? '主板' : 
                   filterConfig.board === 'gem' ? '创业板' :
                   filterConfig.board === 'star' ? '科创板' : 
                   filterConfig.board === 'all' ? '全部' : filterConfig.board}
                </Tag>
              </Descriptions.Item>
            )}
            
            {filterConfig.min_market_cap && (
              <Descriptions.Item label="最小市值">
                {filterConfig.min_market_cap}亿
              </Descriptions.Item>
            )}
          </Descriptions>
        </Card>
        
        {/* AI配置 */}
        {Object.keys(aiConfig).length > 0 && (
          <Card title="AI配置" size="small">
            <Descriptions bordered size="small" column={2}>
              {aiConfig.provider && (
                <Descriptions.Item label="AI提供商">
                  <Tag color="purple">{aiConfig.provider}</Tag>
                </Descriptions.Item>
              )}
              
              {aiConfig.temperature !== undefined && (
                <Descriptions.Item label="温度参数">
                  {aiConfig.temperature}
                </Descriptions.Item>
              )}
            </Descriptions>
          </Card>
        )}
        
        {/* 执行策略 */}
        {task.execution_strategy && (
          <Card title="执行策略" size="small">
            <Alert 
              message={task.execution_strategy} 
              type="info" 
              showIcon 
              style={{ fontSize: '13px' }}
            />
          </Card>
        )}
        
        {/* 候选股票信息 */}
        {candidateInfo && (
          <Card title="候选股票信息" size="small">
            <Space direction="vertical" style={{ width: '100%' }}>
              <Alert 
                message={`筛选方法: ${candidateInfo.selection_method}`}
                type="success"
                showIcon
                style={{ fontSize: '12px' }}
              />
              
              <Text type="secondary">
                共筛选出 {candidateInfo.total_count} 只候选股票
              </Text>
              
              {candidateInfo.candidates && candidateInfo.candidates.length > 0 && (
                <Table
                  size="small"
                  dataSource={candidateInfo.candidates}
                  rowKey="code"
                  pagination={{
                    pageSize: 10,
                    size: 'small',
                    showSizeChanger: false
                  }}
                  columns={[
                    {
                      title: '排序',
                      dataIndex: 'rank',
                      key: 'rank',
                      width: 60
                    },
                    {
                      title: '股票代码',
                      dataIndex: 'code',
                      key: 'code',
                      width: 100
                    },
                    {
                      title: '股票名称',
                      dataIndex: 'name',
                      key: 'name'
                    },
                    {
                      title: '选择方式',
                      dataIndex: 'selected_by',
                      key: 'selected_by',
                      width: 100,
                      render: (text: string) => (
                        <Tag color={text === 'AI推荐' ? 'blue' : 'green'} size="small">
                          {text}
                        </Tag>
                      )
                    }
                  ]}
                />
              )}
            </Space>
          </Card>
        )}
        
        {/* AI提示词 */}
        {task.ai_prompt_used && (
          <Card title="AI提示词" size="small">
            <Alert 
              message="用于查看AI如何理解和处理您的任务"
              type="info"
              style={{ marginBottom: 12, fontSize: '12px' }}
            />
            <Paragraph 
              style={{ 
                backgroundColor: '#f5f5f5', 
                padding: '12px', 
                borderRadius: '6px',
                fontSize: '12px',
                lineHeight: '1.5',
                fontFamily: 'monospace'
              }}
            >
              {task.ai_prompt_used}
            </Paragraph>
          </Card>
        )}
      </Space>
    );
  };

  const TaskResults = ({ results }: { results: TaskResult[] }) => {
    const { message } = App.useApp();
    
    // 加入自选的mutation
    const addToWatchlistMutation = useMutation({
      mutationFn: async (symbol: string) => {
        const response = await fetch('/api/watchlist/add', {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json'
          },
          body: JSON.stringify({ symbol })
        });
        if (!response.ok) {
          throw new Error('加入自选失败');
        }
        return response.json();
      },
      onSuccess: (_, symbol) => {
        message.success(`${symbol} 已加入自选股`);
      },
      onError: (error: any) => {
        message.error(`加入自选失败: ${error.message}`);
      }
    });
    
    const columns = [
      {
        title: '排名',
        dataIndex: 'rank_in_task',
        key: 'rank',
        width: 60,
        render: (rank: number) => (
          <Tag color={rank <= 3 ? 'gold' : 'default'}>#{rank}</Tag>
        )
      },
      {
        title: '股票代码',
        dataIndex: 'symbol',
        key: 'symbol',
        width: 100
      },
      {
        title: '股票名称',
        dataIndex: 'name',
        key: 'name',
        width: 120
      },
      {
        title: '综合评分',
        dataIndex: 'final_score',
        key: 'final_score',
        width: 100,
        render: (score: number) => (
          <Text strong style={{ color: score >= 7 ? '#52c41a' : score >= 5 ? '#faad14' : '#ff4d4f' }}>
            {score?.toFixed(2) || '-'}
          </Text>
        ),
        sorter: (a: TaskResult, b: TaskResult) => (a.final_score || 0) - (b.final_score || 0)
      },
      {
        title: 'AI评分',
        dataIndex: 'ai_score',
        key: 'ai_score',
        width: 80,
        render: (score: number) => score?.toFixed(2) || '-'
      },
      {
        title: '技术评分',
        dataIndex: 'technical_score',
        key: 'technical_score',
        width: 80,
        render: (score: number) => score?.toFixed(2) || '-'
      },
      {
        title: '建议',
        dataIndex: 'action',
        key: 'action',
        width: 80,
        render: (action: string) => {
          const actionMap = {
            'buy': { color: 'success', text: '买入' },
            'hold': { color: 'warning', text: '持有' },
            'sell': { color: 'error', text: '卖出' }
          };
          const config = actionMap[action as keyof typeof actionMap] || { color: 'default', text: action };
          return <Tag color={config.color}>{config.text}</Tag>;
        }
      },
      {
        title: '是否推荐',
        dataIndex: 'is_recommended',
        key: 'is_recommended',
        width: 100,
        render: (recommended: boolean) => (
          <Tag color={recommended ? 'success' : 'default'}>
            {recommended ? '推荐' : '不推荐'}
          </Tag>
        )
      },
      {
        title: '当前价格',
        dataIndex: 'current_price',
        key: 'current_price',
        width: 100,
        render: (price: number) => price ? `¥${price.toFixed(2)}` : '-'
      },
      {
        title: '分析摘要',
        dataIndex: 'summary',
        key: 'summary',
        width: 300,
        render: (summary: string, record: TaskResult) => (
          <div style={{ minWidth: 280 }}>
            <Paragraph 
              ellipsis={{ 
                rows: 3, 
                expandable: true, 
                symbol: '查看更多',
                onExpand: (_, info) => {
                  if (info.expanded) {
                    // 记录用户展开详情的行为
                    console.log(`用户查看了 ${record.symbol} 的详细分析`);
                  }
                }
              }}
              style={{ 
                margin: 0,
                fontSize: '12px',
                lineHeight: '1.4'
              }}
            >
              {summary || '暂无分析摘要'}
            </Paragraph>
          </div>
        )
      },
      {
        title: '操作',
        key: 'actions',
        width: 120,
        fixed: 'right' as const,
        render: (_, record: TaskResult) => (
          <Space size="small">
            <Button 
              type="primary"
              size="small"
              icon={<PlusOutlined />}
              loading={addToWatchlistMutation.isPending}
              onClick={() => addToWatchlistMutation.mutate(record.symbol)}
              title="加入自选股"
            >
              自选
            </Button>
            {record.ai_analysis && (
              <Button 
                size="small"
                icon={<EyeOutlined />}
                onClick={() => {
                  Modal.info({
                    title: `${record.symbol} ${record.name || ''} - AI分析详情`,
                    content: (
                      <div style={{ maxHeight: '400px', overflow: 'auto' }}>
                        <Paragraph style={{ whiteSpace: 'pre-wrap', fontSize: '13px' }}>
                          {record.ai_analysis}
                        </Paragraph>
                      </div>
                    ),
                    width: 800,
                    okText: '关闭'
                  });
                }}
                title="查看AI分析详情"
              >
                详情
              </Button>
            )}
          </Space>
        )
      }
    ];

    return (
      <Card 
        title="推荐结果" 
        extra={
          <Space>
            <Text type="secondary">
              共 {results.length} 个结果，推荐 {results.filter(r => r.is_recommended).length} 只
            </Text>
          </Space>
        }
      >
        <Table
          columns={columns}
          dataSource={results}
          rowKey="id"
          size="small"
          pagination={{
            pageSize: 10,
            showSizeChanger: true,
            showQuickJumper: true,
            showTotal: (total, range) => `第 ${range[0]}-${range[1]} 条，共 ${total} 条记录`
          }}
          scroll={{ x: 1400, y: 600 }}
          sticky
        />
      </Card>
    );
  };

  return (
    <Drawer
      title={`任务详情 - ${taskId.substring(0, 8)}`}
      placement="right"
      size="large"
      open={open}
      onClose={onClose}
      className="task-detail-drawer"
    >
      <Spin spinning={isLoading}>
        {taskDetail && (
          <Tabs
            activeKey={activeTab}
            onChange={setActiveTab}
            items={[
              {
                key: 'overview',
                label: '任务概览',
                children: <TaskOverview task={taskDetail} />
              },
              {
                key: 'details',
                label: '任务详情',
                children: <TaskDetailInfo task={taskDetail} />
              },
              {
                key: 'progress',
                label: '执行进度',
                children: (
                  <StreamingProgress 
                    taskId={taskId} 
                    isRunning={taskDetail.status === 'running'} 
                  />
                )
              },
              {
                key: 'analysis-logs',
                label: '分析日志',
                children: <AnalysisLogViewer taskId={taskId} />
              },
              {
                key: 'results',
                label: `推荐结果${results ? ` (${results.length})` : ''}`,
                disabled: taskDetail.status !== 'completed',
                children: results && <TaskResults results={results} />
              }
            ]}
          />
        )}
      </Spin>
    </Drawer>
  );
};