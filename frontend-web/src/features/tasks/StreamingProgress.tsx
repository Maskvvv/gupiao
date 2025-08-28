import React, { useState, useEffect, useRef } from 'react';
import { Card, Timeline, Progress, Alert, Typography, Tag, Space, Divider } from 'antd';
import { ClockCircleOutlined, CheckCircleOutlined, ExclamationCircleOutlined } from '@ant-design/icons';
import { useQuery } from '@tanstack/react-query';
import { taskApi } from '../../api/tasks';

const { Text, Paragraph } = Typography;

interface ProgressEvent {
  event: string;
  data: any;
  timestamp: string;
  task_id: string;
}

interface StreamingProgressProps {
  taskId: string;
  isRunning: boolean;
}

export const StreamingProgress: React.FC<StreamingProgressProps> = ({ taskId, isRunning }) => {
  const [events, setEvents] = useState<ProgressEvent[]>([]);
  const [currentProgress, setCurrentProgress] = useState(0);
  const [currentSymbol, setCurrentSymbol] = useState('');
  const [currentPhase, setCurrentPhase] = useState('');
  const [aiContent, setAiContent] = useState<{[symbol: string]: string}>({});
  const [connectionStatus, setConnectionStatus] = useState<'connecting' | 'connected' | 'disconnected'>('disconnected');
  
  const eventSourceRef = useRef<EventSource | null>(null);
  const timelineRef = useRef<HTMLDivElement>(null);

  // 获取历史进度数据（对于已完成的任务）
  const { data: historicalProgress, isLoading: progressLoading } = useQuery({
    queryKey: ['task-progress', taskId],
    queryFn: () => taskApi.getTaskProgress(taskId),
    enabled: !isRunning, // 只在任务不运行时获取历史数据
    staleTime: 5 * 60 * 1000 // 5分钟缓存
  });

  // 处理历史进度数据
  useEffect(() => {
    if (historicalProgress && historicalProgress.length > 0 && !isRunning) {
      console.log('加载历史进度数据:', historicalProgress.length, '条记录');
      
      // 转换历史进度数据为组件所需格式，按时间正序排列
      const progressEvents = historicalProgress
        .sort((a, b) => new Date(a.timestamp).getTime() - new Date(b.timestamp).getTime())
        .map(progress => {
          let eventData = progress.progress_data;
          
          // 如果progress_data是字符串，尝试解析为JSON
          if (typeof eventData === 'string') {
            try {
              eventData = JSON.parse(eventData);
            } catch (e) {
              eventData = {};
            }
          }
          
          // 确保事件数据包含必要信息
          if (!eventData || typeof eventData !== 'object') {
            eventData = {};
          }
          
          // 如果eventData没有symbol但progress有，补充进去
          if (!eventData.symbol && progress.symbol) {
            eventData.symbol = progress.symbol;
          }
          
          // 如果eventData没有phase但progress有，补充进去
          if (!eventData.phase && progress.phase) {
            eventData.phase = progress.phase;
          }
          
          return {
            event: progress.event_type,
            data: eventData,
            timestamp: progress.timestamp,
            task_id: progress.task_id
          };
        });
      
      setEvents(progressEvents);
      
      // 从历史数据中重建AI内容累积
      const aiContentMap: {[symbol: string]: string} = {};
      progressEvents.forEach(event => {
        if (event.event === 'ai_chunk' && event.data.symbol && event.data.accumulated) {
          aiContentMap[event.data.symbol] = event.data.accumulated;
        }
      });
      setAiContent(aiContentMap);
      
      // 设置最新状态（取最后的进度事件）
      const progressUpdateEvents = progressEvents.filter(e => e.event === 'progress');
      if (progressUpdateEvents.length > 0) {
        const latestProgressEvent = progressUpdateEvents[progressUpdateEvents.length - 1];
        if (latestProgressEvent.data.progress !== undefined) {
          setCurrentProgress(latestProgressEvent.data.progress);
        }
      }
      
      // 设置当前处理的股票（取最后的current_symbol事件）
      const symbolEvents = progressEvents.filter(e => e.event === 'current_symbol');
      if (symbolEvents.length > 0) {
        const latestSymbolEvent = symbolEvents[symbolEvents.length - 1];
        if (latestSymbolEvent.data.symbol) {
          setCurrentSymbol(latestSymbolEvent.data.symbol);
        }
      }
      
      // 设置当前阶段（取最后的phase_change事件）
      const phaseEvents = progressEvents.filter(e => e.event === 'phase_change');
      if (phaseEvents.length > 0) {
        const latestPhaseEvent = phaseEvents[phaseEvents.length - 1];
        if (latestPhaseEvent.data.phase) {
          setCurrentPhase(latestPhaseEvent.data.phase);
        }
      }
      
      console.log('历史进度数据处理完成:', {
        totalEvents: progressEvents.length,
        currentProgress,
        currentSymbol,
        currentPhase,
        aiContentSymbols: Object.keys(aiContentMap)
      });
    }
  }, [historicalProgress, isRunning]);

  useEffect(() => {
    if (!isRunning) {
      return;
    }

    // 创建SSE连接
    const clientId = `client_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;
    const eventSource = new EventSource(`/api/v2/stream/${taskId}?client_id=${clientId}`);
    eventSourceRef.current = eventSource;

    setConnectionStatus('connecting');

    eventSource.onopen = () => {
      console.log('SSE连接已建立');
      setConnectionStatus('connected');
    };

    eventSource.onmessage = (event) => {
      try {
        const data: ProgressEvent = JSON.parse(event.data);
        handleProgressEvent(data);
      } catch (error) {
        console.error('解析SSE消息失败:', error);
      }
    };

    eventSource.addEventListener('connected', (event) => {
      const data = JSON.parse((event as MessageEvent).data);
      console.log('SSE连接确认:', data);
      setConnectionStatus('connected');
    });

    eventSource.addEventListener('progress', (event) => {
      const data = JSON.parse((event as MessageEvent).data);
      handleProgressEvent({ event: 'progress', data, timestamp: new Date().toISOString(), task_id: taskId });
    });

    eventSource.addEventListener('current_symbol', (event) => {
      const data = JSON.parse((event as MessageEvent).data);
      handleProgressEvent({ event: 'current_symbol', data, timestamp: new Date().toISOString(), task_id: taskId });
    });

    eventSource.addEventListener('ai_chunk', (event) => {
      const data = JSON.parse((event as MessageEvent).data);
      handleProgressEvent({ event: 'ai_chunk', data, timestamp: new Date().toISOString(), task_id: taskId });
    });

    eventSource.addEventListener('symbol_completed', (event) => {
      const data = JSON.parse((event as MessageEvent).data);
      handleProgressEvent({ event: 'symbol_completed', data, timestamp: new Date().toISOString(), task_id: taskId });
    });

    eventSource.addEventListener('symbol_failed', (event) => {
      const data = JSON.parse((event as MessageEvent).data);
      handleProgressEvent({ event: 'symbol_failed', data, timestamp: new Date().toISOString(), task_id: taskId });
    });

    eventSource.addEventListener('phase_change', (event) => {
      const data = JSON.parse((event as MessageEvent).data);
      handleProgressEvent({ event: 'phase_change', data, timestamp: new Date().toISOString(), task_id: taskId });
    });

    eventSource.addEventListener('heartbeat', (event) => {
      console.log('收到心跳包');
    });

    eventSource.onerror = (error) => {
      console.error('SSE连接错误:', error);
      setConnectionStatus('disconnected');
    };

    return () => {
      if (eventSource) {
        eventSource.close();
        setConnectionStatus('disconnected');
      }
    };
  }, [taskId, isRunning]);

  const handleProgressEvent = (event: ProgressEvent) => {
    setEvents(prev => [...prev, event]);

    // 滚动到底部
    setTimeout(() => {
      if (timelineRef.current) {
        timelineRef.current.scrollTop = timelineRef.current.scrollHeight;
      }
    }, 100);

    // 更新状态
    switch (event.event) {
      case 'progress':
        setCurrentProgress(event.data.progress || 0);
        break;
      case 'current_symbol':
        setCurrentSymbol(event.data.symbol || '');
        break;
      case 'phase_change':
        setCurrentPhase(event.data.phase || '');
        break;
      case 'ai_chunk':
        const symbol = event.data.symbol;
        const accumulated = event.data.accumulated || '';
        if (symbol && accumulated) {
          setAiContent(prev => ({
            ...prev,
            [symbol]: accumulated
          }));
        }
        break;
    }
  };

  const getEventIcon = (eventType: string) => {
    switch (eventType) {
      case 'connected':
        return <CheckCircleOutlined style={{ color: '#52c41a' }} />;
      case 'symbol_completed':
        return <CheckCircleOutlined style={{ color: '#52c41a' }} />;
      case 'symbol_failed':
        return <ExclamationCircleOutlined style={{ color: '#ff4d4f' }} />;
      default:
        return <ClockCircleOutlined style={{ color: '#1890ff' }} />;
    }
  };

  const getEventColor = (eventType: string) => {
    switch (eventType) {
      case 'connected':
      case 'symbol_completed':
        return 'green';
      case 'symbol_failed':
        return 'red';
      case 'phase_change':
        return 'blue';
      default:
        return 'gray';
    }
  };

  const getEventDescription = (event: ProgressEvent) => {
    switch (event.event) {
      case 'connected':
        return '连接已建立';
      case 'progress':
        return `进度更新: ${Math.round(event.data.progress || 0)}%`;
      case 'current_symbol':
        return `开始分析: ${event.data.symbol}`;
      case 'phase_change':
        return `阶段变更: ${event.data.phase}`;
      case 'ai_chunk':
        return `AI分析中: ${event.data.symbol}`;
      case 'symbol_completed':
        return `分析完成: ${event.data.symbol}`;
      case 'symbol_failed':
        return `分析失败: ${event.data.symbol} - ${event.data.error}`;
      case 'ai_analysis_start':
        return `开始AI分析: ${event.data.symbol}`;
      case 'symbol_analysis_complete':
        return `股票分析完成: ${event.data.symbol}`;
      default:
        return `${event.event}: ${JSON.stringify(event.data).substring(0, 100)}`;
    }
  };

  const getPhaseText = (phase: string) => {
    const phaseMap = {
      'screening': '股票筛选',
      'analyzing': '技术分析', 
      'ranking': '结果排序'
    };
    return phaseMap[phase as keyof typeof phaseMap] || phase;
  };

  return (
    <div className="streaming-progress">
      {/* 连接状态 */}
      {isRunning ? (
        <Alert
          message={
            connectionStatus === 'connected' ? '实时连接已建立' :
            connectionStatus === 'connecting' ? '正在连接...' : '连接已断开'
          }
          type={
            connectionStatus === 'connected' ? 'success' :
            connectionStatus === 'connecting' ? 'info' : 'warning'
          }
          showIcon
          style={{ marginBottom: 16 }}
        />
      ) : (
        <Alert
          message={progressLoading ? '正在加载历史进度...' : 
                   historicalProgress && historicalProgress.length > 0 ? 
                   '显示历史执行记录' : '该任务暂无执行记录'}
          type={progressLoading ? 'info' : 
                historicalProgress && historicalProgress.length > 0 ? 'info' : 'warning'}
          showIcon
          style={{ marginBottom: 16 }}
        />
      )}

      {/* 当前状态 */}
      <Card title="当前状态" size="small" style={{ marginBottom: 16 }}>
        <Space direction="vertical" style={{ width: '100%' }}>
          <div>
            <Text strong>总体进度: </Text>
            <Progress percent={Math.round(currentProgress)} size="small" />
          </div>
          
          {currentPhase && (
            <div>
              <Text strong>当前阶段: </Text>
              <Tag color="blue">{getPhaseText(currentPhase)}</Tag>
            </div>
          )}
          
          {currentSymbol && (
            <div>
              <Text strong>正在处理: </Text>
              <Tag color="processing">{currentSymbol}</Tag>
            </div>
          )}
        </Space>
      </Card>

      {/* AI分析内容 */}
      {Object.keys(aiContent).length > 0 && (
        <Card title="AI分析内容" size="small" style={{ marginBottom: 16 }}>
          {Object.entries(aiContent).map(([symbol, content]) => (
            <div key={symbol} style={{ marginBottom: 12 }}>
              <Text strong>{symbol}:</Text>
              <Paragraph 
                style={{ 
                  marginTop: 4, 
                  padding: 8, 
                  backgroundColor: '#f5f5f5',
                  borderRadius: 4,
                  maxHeight: 200,
                  overflow: 'auto'
                }}
              >
                {content || '分析中...'}
              </Paragraph>
            </div>
          ))}
        </Card>
      )}

      {/* 事件时间轴 */}
      <Card title="执行日志" size="small">
        <div 
          ref={timelineRef}
          style={{ 
            maxHeight: 400, 
            overflow: 'auto',
            padding: '0 16px'
          }}
        >
          <Timeline>
            {events.map((event, index) => (
              <Timeline.Item
                key={index}
                dot={getEventIcon(event.event)}
                color={getEventColor(event.event)}
              >
                <Space direction="vertical" size="small">
                  <div>
                    <Text strong>{getEventDescription(event)}</Text>
                    <Text type="secondary" style={{ marginLeft: 8 }}>
                      {new Date(event.timestamp).toLocaleTimeString()}
                    </Text>
                  </div>
                  
                  {event.data && Object.keys(event.data).length > 0 && (
                    <details style={{ fontSize: '12px', color: '#666' }}>
                      <summary>详细信息</summary>
                      <pre style={{ marginTop: 4, fontSize: '11px' }}>
                        {JSON.stringify(event.data, null, 2)}
                      </pre>
                    </details>
                  )}
                </Space>
              </Timeline.Item>
            ))}
            
            {events.length === 0 && (
              <Timeline.Item dot={<ClockCircleOutlined />}>
                <Text type="secondary">
                  {isRunning ? '等待任务事件...' : 
                   progressLoading ? '正在加载历史记录...' : 
                   '该任务暂无执行记录'}
                </Text>
              </Timeline.Item>
            )}
          </Timeline>
        </div>
      </Card>
    </div>
  );
};

export default StreamingProgress;