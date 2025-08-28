import React, { useState, useEffect } from 'react';
import {
  Card,
  Tabs,
  Table,
  Tag,
  Typography,
  Collapse,
  Timeline,
  Statistic,
  Row,
  Col,
  Button,
  Switch,
  Alert,
  Descriptions,
  Progress,
  message,
  Empty,
  Spin
} from 'antd';
import {
  ClockCircleOutlined,
  BugOutlined,
  InfoCircleOutlined,
  WarningOutlined,
  CloseCircleOutlined,
  RobotOutlined,
  BarChartOutlined,
  ThunderboltOutlined,
  EyeOutlined,
  ReloadOutlined
} from '@ant-design/icons';
import { useQuery } from '@tanstack/react-query';
import { analysisLogApi } from '../../api/analysisLogs';
import type { AnalysisLog, LogStats, AIScreeningLog, PerformanceLog } from '../../types/analysisLogs';

const { TabPane } = Tabs;
const { Panel } = Collapse;
const { Text, Paragraph } = Typography;

interface AnalysisLogViewerProps {
  taskId: string;
}

const AnalysisLogViewer: React.FC<AnalysisLogViewerProps> = ({ taskId }) => {
  const [activeTab, setActiveTab] = useState('overview');
  const [showDebugLogs, setShowDebugLogs] = useState(false);
  const [selectedStock, setSelectedStock] = useState<string | null>(null);

  // 获取日志统计
  const { data: logStats, isLoading: statsLoading } = useQuery({
    queryKey: ['logStats', taskId],
    queryFn: () => analysisLogApi.getTaskLogStats(taskId),
    refetchInterval: 5000
  });

  // 获取基础日志
  const { data: basicLogs, isLoading: logsLoading, refetch: refetchLogs } = useQuery({
    queryKey: ['analysisLogs', taskId, showDebugLogs],
    queryFn: () => analysisLogApi.getTaskLogs(taskId, {
      logLevel: showDebugLogs ? 'debug' : 'info',
      includeDebug: showDebugLogs
    }),
    refetchInterval: 3000
  });

  // 获取AI筛选日志
  const { data: aiScreeningLogs } = useQuery({
    queryKey: ['aiScreeningLogs', taskId],
    queryFn: () => analysisLogApi.getAIScreeningLogs(taskId),
    enabled: activeTab === 'ai-screening'
  });

  // 获取性能日志
  const { data: performanceLogs } = useQuery({
    queryKey: ['performanceLogs', taskId],
    queryFn: () => analysisLogApi.getPerformanceLogs(taskId),
    enabled: activeTab === 'performance'
  });

  // 获取特定股票的分析日志
  const { data: stockAnalysisLogs } = useQuery({
    queryKey: ['stockAnalysisLogs', taskId, selectedStock],
    queryFn: () => selectedStock ? analysisLogApi.getStockAnalysisLogs(taskId, selectedStock) : null,
    enabled: !!selectedStock
  });

  const getLogLevelIcon = (level: string) => {
    switch (level) {
      case 'error': return <CloseCircleOutlined style={{ color: '#ff4d4f' }} />;
      case 'warning': return <WarningOutlined style={{ color: '#faad14' }} />;
      case 'info': return <InfoCircleOutlined style={{ color: '#1890ff' }} />;
      case 'debug': return <BugOutlined style={{ color: '#666' }} />;
      default: return <InfoCircleOutlined />;
    }
  };

  const getLogTypeTag = (type: string) => {
    const typeConfig = {
      'ai_screening': { color: 'blue', text: 'AI筛选' },
      'technical_analysis': { color: 'green', text: '技术分析' },
      'ai_analysis': { color: 'purple', text: 'AI分析' },
      'fusion_score': { color: 'orange', text: '融合评分' },
      'performance': { color: 'cyan', text: '性能监控' },
      'error': { color: 'red', text: '错误' },
      'task_start': { color: 'geekblue', text: '任务开始' },
      'task_complete': { color: 'lime', text: '任务完成' }
    };
    
    const config = typeConfig[type as keyof typeof typeConfig] || { color: 'default', text: type };
    return <Tag color={config.color}>{config.text}</Tag>;
  };

  const logColumns = [
    {
      title: '时间',
      dataIndex: 'timestamp',
      key: 'timestamp',
      width: 180,
      render: (timestamp: string) => {
        const date = new Date(timestamp);
        return (
          <div>
            <div>{date.toLocaleDateString()}</div>
            <Text type="secondary" style={{ fontSize: '12px' }}>
              {date.toLocaleTimeString()}
            </Text>
          </div>
        );
      }
    },
    {
      title: '级别',
      dataIndex: 'log_level',
      key: 'log_level',
      width: 80,
      render: (level: string) => (
        <div style={{ display: 'flex', alignItems: 'center', gap: 4 }}>
          {getLogLevelIcon(level)}
          <Text style={{ textTransform: 'uppercase', fontSize: '12px' }}>{level}</Text>
        </div>
      )
    },
    {
      title: '类型',
      dataIndex: 'log_type',
      key: 'log_type',
      width: 120,
      render: (type: string) => getLogTypeTag(type)
    },
    {
      title: '股票',
      dataIndex: 'stock_symbol',
      key: 'stock_symbol',
      width: 80,
      render: (symbol: string) => symbol ? (
        <Button 
          type="link" 
          size="small" 
          onClick={() => setSelectedStock(symbol)}
        >
          {symbol}
        </Button>
      ) : '-'
    },
    {
      title: '消息',
      dataIndex: 'log_message',
      key: 'log_message',
      ellipsis: true,
      render: (message: string, record: AnalysisLog) => (
        <div>
          <Text>{message}</Text>
          {record.ai_processing_time_ms && (
            <Tag color="cyan" style={{ marginLeft: 8 }}>
              {record.ai_processing_time_ms}ms
            </Tag>
          )}
          {record.ai_response_tokens && (
            <Tag color="orange" style={{ marginLeft: 4 }}>
              {record.ai_response_tokens} tokens
            </Tag>
          )}
        </div>
      )
    },
    {
      title: '操作',
      key: 'action',
      width: 100,
      render: (_, record: AnalysisLog) => (
        <Button 
          type="text" 
          size="small" 
          icon={<EyeOutlined />}
          onClick={() => {
            // 显示详细信息
            console.log('Log details:', record);
          }}
        >
          详情
        </Button>
      )
    }
  ];

  return (
    <Card 
      title={
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
          <span>
            <BugOutlined style={{ marginRight: 8 }} />
            分析过程日志
          </span>
          <div style={{ display: 'flex', gap: 12, alignItems: 'center' }}>
            <Switch
              checkedChildren="调试"
              unCheckedChildren="标准"
              checked={showDebugLogs}
              onChange={setShowDebugLogs}
              size="small"
            />
            <Button 
              type="text" 
              size="small" 
              icon={<ReloadOutlined />} 
              onClick={() => refetchLogs()}
            >
              刷新
            </Button>
          </div>
        </div>
      }
    >
      <Tabs activeKey={activeTab} onChange={setActiveTab}>
        <TabPane tab="概览统计" key="overview">
          {statsLoading ? (
            <Spin size="large" style={{ display: 'block', textAlign: 'center', padding: '40px' }} />
          ) : logStats ? (
            <>
              <Row gutter={16} style={{ marginBottom: 24 }}>
                <Col span={6}>
                  <Statistic 
                    title="总日志数" 
                    value={logStats.total_logs} 
                    prefix={<InfoCircleOutlined />}
                  />
                </Col>
                <Col span={6}>
                  <Statistic 
                    title="错误数" 
                    value={logStats.error_count} 
                    valueStyle={{ color: '#cf1322' }}
                    prefix={<CloseCircleOutlined />}
                  />
                </Col>
                <Col span={6}>
                  <Statistic 
                    title="AI分析次数" 
                    value={logStats.ai_analysis_count} 
                    prefix={<RobotOutlined />}
                  />
                </Col>
                <Col span={6}>
                  <Statistic 
                    title="技术分析次数" 
                    value={logStats.technical_analysis_count} 
                    prefix={<BarChartOutlined />}
                  />
                </Col>
              </Row>
              
              <Row gutter={16}>
                <Col span={8}>
                  <Statistic 
                    title="平均AI耗时" 
                    value={logStats.avg_ai_time_ms?.toFixed(1) || 0} 
                    suffix="ms"
                    prefix={<ClockCircleOutlined />}
                  />
                </Col>
                <Col span={8}>
                  <Statistic 
                    title="总Token消耗" 
                    value={logStats.total_tokens || 0} 
                    prefix={<ThunderboltOutlined />}
                  />
                </Col>
                <Col span={8}>
                  <Statistic 
                    title="警告数" 
                    value={logStats.warning_count} 
                    valueStyle={{ color: '#faad14' }}
                    prefix={<WarningOutlined />}
                  />
                </Col>
              </Row>
              
              {logStats.error_count > 0 && (
                <Alert
                  type="warning"
                  message="发现错误日志"
                  description={`任务执行过程中发现 ${logStats.error_count} 个错误，建议查看详细日志排查问题。`}
                  style={{ marginTop: 16 }}
                  showIcon
                />
              )}
            </>
          ) : (
            <Empty description="暂无统计数据" />
          )}
        </TabPane>

        <TabPane tab="详细日志" key="details">
          <Table
            columns={logColumns}
            dataSource={basicLogs || []}
            loading={logsLoading}
            size="small"
            rowKey="id"
            pagination={{
              pageSize: 20,
              showSizeChanger: true,
              showQuickJumper: true,
              showTotal: (total) => `共 ${total} 条日志`
            }}
            expandable={{
              expandedRowRender: (record: AnalysisLog) => (
                <div style={{ margin: 0, padding: '8px 24px' }}>
                  {record.log_details && (
                    <Descriptions title="详细信息" size="small" column={2}>
                      {Object.entries(record.log_details).map(([key, value]) => (
                        <Descriptions.Item label={key} key={key}>
                          {typeof value === 'object' ? JSON.stringify(value, null, 2) : String(value)}
                        </Descriptions.Item>
                      ))}
                    </Descriptions>
                  )}
                  
                  {record.ai_request_prompt && (
                    <div style={{ marginTop: 16 }}>
                      <Text strong>AI请求提示词：</Text>
                      <Paragraph copyable style={{ marginTop: 8, background: '#f5f5f5', padding: 12, borderRadius: 4 }}>
                        {record.ai_request_prompt}
                      </Paragraph>
                    </div>
                  )}
                  
                  {record.ai_response_content && (
                    <div style={{ marginTop: 16 }}>
                      <Text strong>AI响应内容：</Text>
                      <Paragraph copyable style={{ marginTop: 8, background: '#f0f9ff', padding: 12, borderRadius: 4 }}>
                        {record.ai_response_content}
                      </Paragraph>
                    </div>
                  )}
                </div>
              ),
              rowExpandable: (record) => !!(record.log_details || record.ai_request_prompt || record.ai_response_content)
            }}
          />
        </TabPane>

        <TabPane tab="AI筛选过程" key="ai-screening">
          {aiScreeningLogs ? (
            <div>
              <Row gutter={16} style={{ marginBottom: 24 }}>
                <Col span={8}>
                  <Statistic 
                    title="筛选耗时" 
                    value={aiScreeningLogs.summary.total_processing_time_ms} 
                    suffix="ms"
                  />
                </Col>
                <Col span={8}>
                  <Statistic 
                    title="Token消耗" 
                    value={aiScreeningLogs.summary.total_tokens} 
                  />
                </Col>
                <Col span={8}>
                  <Statistic 
                    title="推荐股票数" 
                    value={aiScreeningLogs.summary.stocks_recommended} 
                    suffix="只"
                  />
                </Col>
              </Row>
              
              <Timeline>
                {aiScreeningLogs.ai_requests.map((request, index) => (
                  <Timeline.Item key={index} color="blue">
                    <Text strong>AI请求 #{index + 1}</Text>
                    <div style={{ marginTop: 8 }}>
                      <Tag color="processing">{request.processing_time_ms}ms</Tag>
                      <Tag color="orange">{request.tokens} tokens</Tag>
                    </div>
                    <Collapse ghost style={{ marginTop: 8 }}>
                      <Panel header="查看详情" key="1">
                        <div>
                          <Text strong>请求提示词：</Text>
                          <Paragraph copyable style={{ marginTop: 8, background: '#f5f5f5', padding: 12 }}>
                            {request.prompt}
                          </Paragraph>
                        </div>
                        <div style={{ marginTop: 16 }}>
                          <Text strong>AI响应：</Text>
                          <Paragraph copyable style={{ marginTop: 8, background: '#f0f9ff', padding: 12 }}>
                            {request.response}
                          </Paragraph>
                        </div>
                      </Panel>
                    </Collapse>
                  </Timeline.Item>
                ))}
                
                {aiScreeningLogs.fallback_events.map((event, index) => (
                  <Timeline.Item key={`fallback-${index}`} color="orange">
                    <Text strong>降级策略</Text>
                    <div style={{ marginTop: 8 }}>
                      <Text type="secondary">{event.reason}</Text>
                    </div>
                  </Timeline.Item>
                ))}
                
                {aiScreeningLogs.errors.map((error, index) => (
                  <Timeline.Item key={`error-${index}`} color="red">
                    <Text strong>错误事件</Text>
                    <div style={{ marginTop: 8 }}>
                      <Text type="danger">{error.error_message}</Text>
                    </div>
                  </Timeline.Item>
                ))}
              </Timeline>
            </div>
          ) : (
            <Empty description="暂无AI筛选日志" />
          )}
        </TabPane>

        <TabPane tab="性能监控" key="performance">
          {performanceLogs ? (
            <div>
              <Row gutter={16} style={{ marginBottom: 24 }}>
                <Col span={6}>
                  <Statistic 
                    title="AI调用次数" 
                    value={performanceLogs.ai_performance.total_calls} 
                  />
                </Col>
                <Col span={6}>
                  <Statistic 
                    title="平均AI耗时" 
                    value={performanceLogs.ai_performance.avg_time_ms.toFixed(1)} 
                    suffix="ms"
                  />
                </Col>
                <Col span={6}>
                  <Statistic 
                    title="技术分析次数" 
                    value={performanceLogs.technical_performance.total_analyses} 
                  />
                </Col>
                <Col span={6}>
                  <Statistic 
                    title="平均技术分" 
                    value={performanceLogs.technical_performance.avg_score.toFixed(2)} 
                  />
                </Col>
              </Row>
              
              <Card title="性能时间线" size="small">
                {performanceLogs.timeline.map((item, index) => (
                  <div key={index} style={{ 
                    display: 'flex', 
                    justifyContent: 'space-between', 
                    alignItems: 'center',
                    padding: '8px 0',
                    borderBottom: index < performanceLogs.timeline.length - 1 ? '1px solid #f0f0f0' : 'none'
                  }}>
                    <div>
                      <Text>{item.stock_symbol || '系统'}</Text>
                      <Text type="secondary" style={{ marginLeft: 8 }}>
                        {getLogTypeTag(item.log_type)}
                      </Text>
                    </div>
                    <div>
                      {item.processing_time_ms && (
                        <Tag color="blue">{item.processing_time_ms}ms</Tag>
                      )}
                      {item.memory_mb && (
                        <Tag color="green">{item.memory_mb.toFixed(1)}MB</Tag>
                      )}
                    </div>
                  </div>
                ))}
              </Card>
            </div>
          ) : (
            <Empty description="暂无性能数据" />
          )}
        </TabPane>
      </Tabs>

      {/* 股票分析详情弹窗 */}
      {selectedStock && stockAnalysisLogs && (
        <Card 
          title={`${selectedStock} 分析过程`}
          extra={
            <Button type="text" onClick={() => setSelectedStock(null)}>关闭</Button>
          }
          style={{ marginTop: 16 }}
        >
          <Timeline>
            {stockAnalysisLogs.technical_analysis && (
              <Timeline.Item color="green">
                <Text strong>技术分析</Text>
                <div style={{ marginTop: 8 }}>
                  <Text>技术分数: {stockAnalysisLogs.technical_analysis.score}</Text>
                </div>
              </Timeline.Item>
            )}
            
            {stockAnalysisLogs.ai_analysis.start_time && (
              <Timeline.Item color="blue">
                <Text strong>AI分析开始</Text>
                <div style={{ marginTop: 8 }}>
                  <Text type="secondary">{stockAnalysisLogs.ai_analysis.start_time}</Text>
                </div>
              </Timeline.Item>
            )}
            
            {stockAnalysisLogs.ai_analysis.chunks.map((chunk, index) => (
              <Timeline.Item key={index} color="cyan">
                <Text>AI流式数据 #{index + 1}</Text>
                <div style={{ marginTop: 8 }}>
                  <Text type="secondary">{chunk.chunk_content}</Text>
                </div>
              </Timeline.Item>
            ))}
            
            {stockAnalysisLogs.ai_analysis.final_result && (
              <Timeline.Item color="blue">
                <Text strong>AI分析完成</Text>
                <div style={{ marginTop: 8 }}>
                  <Tag color="processing">{stockAnalysisLogs.ai_analysis.final_result.processing_time_ms}ms</Tag>
                  <Tag color="orange">{stockAnalysisLogs.ai_analysis.final_result.tokens} tokens</Tag>
                </div>
              </Timeline.Item>
            )}
            
            {stockAnalysisLogs.fusion_score && (
              <Timeline.Item color="orange">
                <Text strong>融合评分</Text>
                <div style={{ marginTop: 8 }}>
                  <Text>最终分数: {stockAnalysisLogs.fusion_score.final_score}</Text>
                </div>
              </Timeline.Item>
            )}
            
            {stockAnalysisLogs.errors.map((error, index) => (
              <Timeline.Item key={index} color="red">
                <Text strong>错误</Text>
                <div style={{ marginTop: 8 }}>
                  <Text type="danger">{error.error_message}</Text>
                </div>
              </Timeline.Item>
            ))}
          </Timeline>
        </Card>
      )}
    </Card>
  );
};

export default AnalysisLogViewer;