import React, { useState, useEffect } from 'react';
import {
  Card,
  Table,
  Tag,
  Button,
  Space,
  Select,
  Statistic,
  Row,
  Col,
  Progress,
  Tooltip,
  Drawer,
  message,
  Badge,
  Popconfirm
} from 'antd';
import {
  ReloadOutlined,
  PlayCircleOutlined,
  PauseCircleOutlined,
  DeleteOutlined,
  EyeOutlined,
  RedoOutlined,
  UnorderedListOutlined,
  SyncOutlined,
  CheckCircleOutlined,
  ExclamationCircleOutlined
} from '@ant-design/icons';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import dayjs from 'dayjs';
import { TaskDetail } from './TaskDetail';
import { taskApi } from '../../api/tasks';
import type { RecommendationTask, TaskStats } from '../../types/tasks';

const { Option } = Select;

interface TaskListResponse {
  tasks: RecommendationTask[];
  stats: TaskStats;
  pagination: {
    total: number;
    limit: number;
    offset: number;
    has_more: boolean;
  };
}

export const TaskDashboard: React.FC = () => {
  const [statusFilter, setStatusFilter] = useState<string>('all');
  const [typeFilter, setTypeFilter] = useState<string>('all');
  const [selectedTask, setSelectedTask] = useState<string | null>(null);
  const [selectedTabKey, setSelectedTabKey] = useState<string>('overview');
  const [page, setPage] = useState(1);
  const [pageSize, setPageSize] = useState(20);

  const queryClient = useQueryClient();

  // 获取任务列表
  const { data: tasksData, isLoading, refetch } = useQuery<TaskListResponse>({
    queryKey: ['tasks', statusFilter, typeFilter, page, pageSize],
    queryFn: () => taskApi.listTasks({
      status: statusFilter === 'all' ? undefined : statusFilter,
      task_type: typeFilter === 'all' ? undefined : typeFilter,
      limit: pageSize,
      offset: (page - 1) * pageSize
    }),
    refetchInterval: 5000, // 每5秒刷新
  });

  // 取消任务
  const cancelTaskMutation = useMutation({
    mutationFn: (taskId: string) => taskApi.cancelTask(taskId),
    onSuccess: () => {
      message.success('任务已取消');
      refetch();
    },
    onError: (error: any) => {
      message.error(`取消任务失败: ${error.response?.data?.detail || error.message}`);
    }
  });

  // 重试任务
  const retryTaskMutation = useMutation({
    mutationFn: (taskId: string) => taskApi.retryTask(taskId),
    onSuccess: () => {
      message.success('任务已重新启动');
      refetch();
    },
    onError: (error: any) => {
      message.error(`重试任务失败: ${error.response?.data?.detail || error.message}`);
    }
  });

  // 启动任务
  const startTaskMutation = useMutation({
    mutationFn: (taskId: string) => taskApi.startTask(taskId),
    onSuccess: () => {
      message.success('任务已启动');
      refetch();
    },
    onError: (error: any) => {
      message.error(`启动任务失败: ${error.response?.data?.detail || error.message}`);
    }
  });

  const getTaskTypeText = (type: string) => {
    const typeMap = {
      'ai': 'AI推荐',
      'keyword': '关键词推荐',
      'market': '全市场推荐'
    };
    return typeMap[type as keyof typeof typeMap] || type;
  };

  const getTaskTypeColor = (type: string) => {
    const colorMap = {
      'ai': 'blue',
      'keyword': 'green',
      'market': 'purple'
    };
    return colorMap[type as keyof typeof colorMap] || 'default';
  };

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

  const columns = [
    {
      title: '任务ID',
      dataIndex: 'id',
      key: 'id',
      width: 120,
      render: (id: string) => (
        <Tooltip title={id}>
          <span className="task-id-short">{id.substring(0, 8)}...</span>
        </Tooltip>
      )
    },
    {
      title: '任务类型',
      dataIndex: 'task_type',
      key: 'task_type',
      width: 100,
      render: (type: string) => (
        <Tag color={getTaskTypeColor(type)}>
          {getTaskTypeText(type)}
        </Tag>
      )
    },
    {
      title: '状态',
      dataIndex: 'status',
      key: 'status',
      width: 100,
      render: (status: string, record: RecommendationTask) => (
        <Space>
          <Tag color={getStatusColor(status)}>
            {getStatusText(status)}
          </Tag>
          {record.is_running && <Badge status="processing" />}
        </Space>
      )
    },
    {
      title: '进度',
      dataIndex: 'progress_percent',
      key: 'progress',
      width: 150,
      render: (progress: number, record: RecommendationTask) => (
        <div>
          <Progress 
            percent={Math.round(progress)} 
            size="small" 
            status={record.status === 'failed' ? 'exception' : 'active'}
          />
          <div className="progress-detail" style={{ fontSize: '12px', color: '#666' }}>
            {record.completed_symbols} / {record.total_symbols} 股票
          </div>
        </div>
      )
    },
    {
      title: '创建时间',
      dataIndex: 'created_at',
      key: 'created_at',
      width: 150,
      render: (time: string) => dayjs(time).format('MM-DD HH:mm:ss')
    },
    {
      title: '执行时间',
      dataIndex: 'execution_time_seconds',
      key: 'execution_time',
      width: 100,
      render: (seconds: number) => 
        seconds ? `${Math.round(seconds)}s` : '-'
    },
    {
      title: '推荐数',
      dataIndex: 'final_recommendations',
      key: 'recommendations',
      width: 80,
      render: (count: number) => count || '-'
    },
    {
      title: '操作',
      key: 'actions',
      width: 250,
      render: (_, record: RecommendationTask) => (
        <Space>
          <Button 
            size="small" 
            icon={<EyeOutlined />}
            onClick={() => {
              setSelectedTask(record.id);
              setSelectedTabKey('overview'); // 详情按钮默认显示概览
            }}
          >
            详情
          </Button>
          
          {record.status === 'pending' && (
            <Button 
              size="small" 
              type="primary"
              icon={<PlayCircleOutlined />}
              onClick={() => startTaskMutation.mutate(record.id)}
              loading={startTaskMutation.isPending}
            >
              启动
            </Button>
          )}
          
          {record.status === 'running' && (
            <Popconfirm
              title="确定要取消这个任务吗？"
              onConfirm={() => cancelTaskMutation.mutate(record.id)}
              okText="确定"
              cancelText="取消"
            >
              <Button 
                size="small" 
                danger
                icon={<PauseCircleOutlined />}
                loading={cancelTaskMutation.isPending}
              >
                取消
              </Button>
            </Popconfirm>
          )}
          
          {['failed', 'cancelled'].includes(record.status) && (
            <Button 
              size="small" 
              type="primary"
              icon={<RedoOutlined />}
              onClick={() => retryTaskMutation.mutate(record.id)}
              loading={retryTaskMutation.isPending}
            >
              重试
            </Button>
          )}
          
          {record.status === 'completed' && (
            <Button 
              size="small" 
              type="link"
              icon={<EyeOutlined />}
              onClick={() => {
                setSelectedTask(record.id);
                setSelectedTabKey('results'); // 直接跳转到推荐结果标签页
              }}
            >
              查看结果
            </Button>
          )}
        </Space>
      )
    }
  ];

  return (
    <div className="task-dashboard">
      <Card title="任务管理中心" className="dashboard-header">
        <Row gutter={16} className="dashboard-stats">
          <Col span={6}>
            <Statistic
              title="总任务数"
              value={tasksData?.stats?.total || 0}
              prefix={<UnorderedListOutlined />}
            />
          </Col>
          <Col span={6}>
            <Statistic
              title="执行中"
              value={tasksData?.stats?.running || 0}
              valueStyle={{ color: '#1890ff' }}
              prefix={<SyncOutlined spin />}
            />
          </Col>
          <Col span={6}>
            <Statistic
              title="已完成"
              value={tasksData?.stats?.completed || 0}
              valueStyle={{ color: '#3f8600' }}
              prefix={<CheckCircleOutlined />}
            />
          </Col>
          <Col span={6}>
            <Statistic
              title="失败/取消"
              value={(tasksData?.stats?.failed || 0) + (tasksData?.stats?.cancelled || 0)}
              valueStyle={{ color: '#cf1322' }}
              prefix={<ExclamationCircleOutlined />}
            />
          </Col>
        </Row>
      </Card>

      <Card className="task-table-card" style={{ marginTop: 16 }}>
        <div className="table-controls" style={{ marginBottom: 16 }}>
          <Space>
            <Select
              value={statusFilter}
              onChange={setStatusFilter}
              placeholder="筛选状态"
              style={{ width: 120 }}
            >
              <Option value="all">全部状态</Option>
              <Option value="pending">等待中</Option>
              <Option value="running">执行中</Option>
              <Option value="completed">已完成</Option>
              <Option value="failed">失败</Option>
              <Option value="cancelled">已取消</Option>
            </Select>
            
            <Select
              value={typeFilter}
              onChange={setTypeFilter}
              placeholder="筛选类型"
              style={{ width: 120 }}
            >
              <Option value="all">全部类型</Option>
              <Option value="ai">AI推荐</Option>
              <Option value="keyword">关键词推荐</Option>
              <Option value="market">全市场推荐</Option>
            </Select>
            
            <Button 
              icon={<ReloadOutlined />} 
              onClick={() => refetch()}
              loading={isLoading}
            >
              刷新
            </Button>
          </Space>
        </div>

        <Table
          columns={columns}
          dataSource={tasksData?.tasks || []}
          loading={isLoading}
          rowKey="id"
          pagination={{
            current: page,
            pageSize: pageSize,
            total: tasksData?.pagination?.total || 0,
            showSizeChanger: true,
            showQuickJumper: true,
            showTotal: (total) => `共 ${total} 个任务`,
            onChange: (newPage, newPageSize) => {
              setPage(newPage);
              setPageSize(newPageSize || 20);
            }
          }}
          scroll={{ x: 1200 }}
        />
      </Card>

      {/* 任务详情抽屉 */}
      {selectedTask && (
        <TaskDetail
          taskId={selectedTask}
          open={!!selectedTask}
          onClose={() => {
            setSelectedTask(null);
            setSelectedTabKey('overview'); // 重置标签页
          }}
          defaultActiveTab={selectedTabKey}
        />
      )}
    </div>
  );
};