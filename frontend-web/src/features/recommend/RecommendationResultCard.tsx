import React from 'react';
import {
  Card,
  Tag,
  Space,
  Typography,
  Tooltip,
  Progress,
  Button
} from 'antd';
import {
  TrophyOutlined,
  RobotOutlined,
  LineChartOutlined,
  PlusOutlined
} from '@ant-design/icons';
import { useMutation, useQueryClient } from '@tanstack/react-query';
import { addWatch } from '../../api/watchlist';
import type { TaskResult } from '../../types/tasks';

const { Text, Paragraph } = Typography;

interface RecommendationResultCardProps {
  result: TaskResult;
}

const ActionBadge: React.FC<{ action: string | undefined }> = ({ action }) => {
  const getActionProps = (action: string | undefined) => {
    switch (action) {
      case 'buy':
        return { color: 'success', text: '买入' };
      case 'hold':
        return { color: 'warning', text: '持有' };
      case 'sell':
        return { color: 'error', text: '卖出' };
      default:
        return { color: 'default', text: '观望' };
    }
  };

  const props = getActionProps(action);
  return <Tag color={props.color}>{props.text}</Tag>;
};

export const RecommendationResultCard: React.FC<RecommendationResultCardProps> = ({ 
  result 
}) => {
  const queryClient = useQueryClient();
  
  const addToWatchlistMutation = useMutation({
    mutationFn: (symbol: string) => addWatch(symbol),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['watchlist'] });
    }
  });

  const getScoreColor = (score: number | undefined) => {
    if (!score) return '#8c8c8c';
    if (score >= 7) return '#52c41a';
    if (score >= 5) return '#faad14';
    return '#ff4d4f';
  };

  const formatScore = (score: number | undefined) => {
    return score ? score.toFixed(2) : '-';
  };

  return (
    <Card
      size="small"
      title={
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
          <span>{result.name || result.symbol}</span>
          <Tag color="blue">{result.symbol}</Tag>
        </div>
      }
      extra={
        result.rank_in_task && (
          <Tooltip title="在任务中的排名">
            <Tag color={result.rank_in_task <= 3 ? 'gold' : 'default'} icon={<TrophyOutlined />}>
              #{result.rank_in_task}
            </Tag>
          </Tooltip>
        )
      }
      actions={[
        <Button
          key="add"
          type="text"
          icon={<PlusOutlined />}
          onClick={() => addToWatchlistMutation.mutate(result.symbol)}
          loading={addToWatchlistMutation.isPending}
        >
          加入自选
        </Button>
      ]}
    >
      <Space direction="vertical" size={12} style={{ width: '100%' }}>
        {/* 评分区域 */}
        <div>
          <Space wrap>
            <Tooltip title="技术面评分">
              <div style={{ textAlign: 'center' }}>
                <LineChartOutlined style={{ color: '#1890ff', marginBottom: 4 }} />
                <div>
                  <Text strong style={{ color: getScoreColor(result.technical_score) }}>
                    {formatScore(result.technical_score)}
                  </Text>
                </div>
                <Text type="secondary" style={{ fontSize: '12px' }}>技术分</Text>
              </div>
            </Tooltip>
            
            <Tooltip title="AI分析评分">
              <div style={{ textAlign: 'center' }}>
                <RobotOutlined style={{ color: '#52c41a', marginBottom: 4 }} />
                <div>
                  <Text strong style={{ color: getScoreColor(result.ai_score) }}>
                    {formatScore(result.ai_score)}
                  </Text>
                </div>
                <Text type="secondary" style={{ fontSize: '12px' }}>AI分</Text>
              </div>
            </Tooltip>
            
            <Tooltip title="最终综合评分">
              <div style={{ textAlign: 'center' }}>
                <TrophyOutlined style={{ color: '#faad14', marginBottom: 4 }} />
                <div>
                  <Text strong style={{ color: getScoreColor(result.final_score), fontSize: '16px' }}>
                    {formatScore(result.final_score)}
                  </Text>
                </div>
                <Text type="secondary" style={{ fontSize: '12px' }}>综合分</Text>
              </div>
            </Tooltip>
          </Space>
          
          {result.final_score && (
            <Progress 
              percent={result.final_score * 10} 
              size="small" 
              showInfo={false}
              strokeColor={getScoreColor(result.final_score)}
              style={{ marginTop: 8 }}
            />
          )}
        </div>

        {/* 建议动作 */}
        {result.action && (
          <div>
            <Text type="secondary">建议动作: </Text>
            <ActionBadge action={result.action} />
          </div>
        )}

        {/* AI信心度 */}
        {result.ai_confidence && (
          <div>
            <Text type="secondary">AI信心度: </Text>
            <Text strong style={{ color: getScoreColor(result.ai_confidence * 10) }}>
              {(result.ai_confidence * 100).toFixed(1)}%
            </Text>
          </div>
        )}

        {/* 简要分析 */}
        {result.summary && (
          <Paragraph 
            ellipsis={{ rows: 3, expandable: true, symbol: '展开' }}
            style={{ margin: 0 }}
          >
            <Text strong>分析摘要: </Text>
            {result.summary}
          </Paragraph>
        )}

        {/* AI详细分析 */}
        {result.ai_analysis && (
          <Paragraph 
            type="secondary"
            ellipsis={{ rows: 4, expandable: true, symbol: '展开AI分析' }}
            style={{ margin: 0, fontSize: '12px' }}
          >
            <Text strong>AI详细分析: </Text>
            {result.ai_analysis}
          </Paragraph>
        )}

        {/* 推荐理由 */}
        {result.recommendation_reason && result.is_recommended && (
          <div>
            <Tag color="success">推荐</Tag>
            <Text type="secondary" style={{ fontSize: '12px' }}>
              {result.recommendation_reason}
            </Text>
          </div>
        )}

        {/* 价格信息 */}
        {result.current_price && (
          <div style={{ fontSize: '12px', color: '#8c8c8c' }}>
            <Text type="secondary">
              当前价格: ¥{result.current_price.toFixed(2)}
            </Text>
            {result.analyzed_at && (
              <Text type="secondary" style={{ marginLeft: 8 }}>
                分析时间: {new Date(result.analyzed_at).toLocaleString()}
              </Text>
            )}
          </div>
        )}
      </Space>
    </Card>
  );
};

export default RecommendationResultCard;