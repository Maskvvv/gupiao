import React, { useState } from 'react';
import {
  Card,
  Form,
  Input,
  Select,
  Button,
  Space,
  InputNumber,
  Switch,
  Divider,
  Alert,
  Modal,
  Progress,
  Tag,
  Typography,
  message
} from 'antd';
import { PlayCircleOutlined, SettingOutlined, EyeOutlined } from '@ant-design/icons';
import { useMutation } from '@tanstack/react-query';
import { taskApi } from '../../api/tasks';
import { StreamingProgress } from '../tasks/StreamingProgress';
import type { 
  AIRecommendationRequest, 
  KeywordRecommendationRequest, 
  CreateTaskResponse 
} from '../../types/tasks';

const { Option } = Select;
const { TextArea } = Input;
const { Text } = Typography;

const StreamingRecommendForm: React.FC = () => {
  const [form] = Form.useForm();
  const [recommendType, setRecommendType] = useState<'ai' | 'keyword'>('ai');
  const [showAdvanced, setShowAdvanced] = useState(false);
  const [currentTask, setCurrentTask] = useState<CreateTaskResponse | null>(null);
  const [progressVisible, setProgressVisible] = useState(false);

  // AI推荐任务
  const aiRecommendMutation = useMutation({
    mutationFn: (request: AIRecommendationRequest) => 
      taskApi.createAndStartAIRecommendation(request),
    onSuccess: (response) => {
      message.success('AI推荐任务已启动！');
      setCurrentTask(response);
      setProgressVisible(true);
    },
    onError: (error: any) => {
      message.error(`启动任务失败: ${error.response?.data?.detail || error.message}`);
    }
  });

  // 关键词推荐任务
  const keywordRecommendMutation = useMutation({
    mutationFn: (request: KeywordRecommendationRequest) => 
      taskApi.createAndStartKeywordRecommendation(request),
    onSuccess: (response) => {
      message.success('关键词推荐任务已启动！');
      setCurrentTask(response);
      setProgressVisible(true);
    },
    onError: (error: any) => {
      message.error(`启动任务失败: ${error.response?.data?.detail || error.message}`);
    }
  });

  const onFinish = (values: any) => {
    if (recommendType === 'ai') {
      const symbols = values.symbols
        .split(/[,，\s\n]+/)
        .map((s: string) => s.trim())
        .filter((s: string) => s.length > 0);

      if (symbols.length === 0) {
        message.error('请输入至少一个股票代码');
        return;
      }

      const request: AIRecommendationRequest = {
        symbols,
        period: values.period || '1y',
        weights: showAdvanced ? {
          technical: values.technical_weight / 100,
          macro_sentiment: values.macro_weight / 100,
          news_events: values.news_weight / 100
        } : undefined,
        ai_config: showAdvanced ? {
          provider: values.ai_provider,
          temperature: values.temperature,
          api_key: values.api_key
        } : undefined,
        priority: values.priority || 5
      };

      aiRecommendMutation.mutate(request);
    } else {
      const request: KeywordRecommendationRequest = {
        keyword: values.keyword,
        period: values.period || '1y',
        max_candidates: values.max_candidates || 5,
        weights: showAdvanced ? {
          technical: values.technical_weight / 100,
          macro_sentiment: values.macro_weight / 100,
          news_events: values.news_weight / 100
        } : undefined,
        filter_config: {
          exclude_st: values.exclude_st !== false,
          min_market_cap: values.min_market_cap,
          board: values.board,
          max_candidates: values.screen_max_candidates || 20
        },
        ai_config: showAdvanced ? {
          provider: values.ai_provider,
          temperature: values.temperature,
          api_key: values.api_key
        } : undefined,
        priority: values.priority || 5
      };

      keywordRecommendMutation.mutate(request);
    }
  };

  const isLoading = aiRecommendMutation.isPending || keywordRecommendMutation.isPending;

  return (
    <>
      <Card title="流式股票推荐" extra={
        <Space>
          <Button 
            icon={<SettingOutlined />}
            onClick={() => setShowAdvanced(!showAdvanced)}
          >
            {showAdvanced ? '隐藏' : '显示'}高级设置
          </Button>
          {currentTask && (
            <Button 
              icon={<EyeOutlined />}
              onClick={() => setProgressVisible(true)}
            >
              查看进度
            </Button>
          )}
        </Space>
      }>
        <Alert
          message="流式推荐系统"
          description="支持实时展示AI分析过程，可以观察推荐算法的工作过程，提供更透明的分析体验。"
          type="info"
          showIcon
          style={{ marginBottom: 16 }}
        />

        <Form
          form={form}
          layout="vertical"
          onFinish={onFinish}
          initialValues={{
            period: '1y',
            technical_weight: 40,
            macro_weight: 35,
            news_weight: 25,
            temperature: 0.3,
            ai_provider: 'deepseek',
            priority: 5,
            max_candidates: 5,
            exclude_st: true,
            screen_max_candidates: 20
          }}
        >
          {/* 推荐类型选择 */}
          <Form.Item label="推荐类型" required>
            <Select value={recommendType} onChange={setRecommendType}>
              <Option value="ai">AI推荐（手动输入股票）</Option>
              <Option value="keyword">关键词推荐（AI筛选股票）</Option>
            </Select>
          </Form.Item>

          {/* AI推荐表单 */}
          {recommendType === 'ai' && (
            <Form.Item
              name="symbols"
              label="股票代码"
              rules={[{ required: true, message: '请输入股票代码' }]}
              extra="支持多个股票代码，用逗号、空格或换行分隔，如：000001,600036,300750"
            >
              <TextArea
                rows={4}
                placeholder="请输入股票代码，例如：&#10;000001&#10;600036&#10;300750"
              />
            </Form.Item>
          )}

          {/* 关键词推荐表单 */}
          {recommendType === 'keyword' && (
            <>
              <Form.Item
                name="keyword"
                label="搜索关键词"
                rules={[{ required: true, message: '请输入搜索关键词' }]}
                extra="输入行业、概念或主题关键词，AI将筛选相关股票"
              >
                <Input placeholder="例如：新能源、人工智能、医药、消费等" />
              </Form.Item>

              <Form.Item
                name="max_candidates"
                label="最大推荐数量"
              >
                <InputNumber min={1} max={50} style={{ width: '100%' }} />
              </Form.Item>
            </>
          )}

          {/* 基础设置 */}
          <Form.Item name="period" label="分析周期">
            <Select>
              <Option value="3mo">3个月</Option>
              <Option value="6mo">6个月</Option>
              <Option value="1y">1年</Option>
              <Option value="2y">2年</Option>
            </Select>
          </Form.Item>

          {/* 高级设置 */}
          {showAdvanced && (
            <>
              <Divider orientation="left">权重配置</Divider>
              
              <Form.Item label="分析权重分配" style={{ marginBottom: 8 }}>
                <Text type="secondary">调整不同维度的权重比例</Text>
              </Form.Item>

              <Form.Item name="technical_weight" label="技术面权重 (%)">
                <InputNumber min={0} max={100} style={{ width: '100%' }} />
              </Form.Item>

              <Form.Item name="macro_weight" label="宏观情绪权重 (%)">
                <InputNumber min={0} max={100} style={{ width: '100%' }} />
              </Form.Item>

              <Form.Item name="news_weight" label="新闻事件权重 (%)">
                <InputNumber min={0} max={100} style={{ width: '100%' }} />
              </Form.Item>

              <Divider orientation="left">AI配置</Divider>

              <Form.Item name="ai_provider" label="AI模型">
                <Select>
                  <Option value="openai">OpenAI GPT</Option>
                  <Option value="deepseek">DeepSeek</Option>
                  <Option value="gemini">Google Gemini</Option>
                </Select>
              </Form.Item>

              <Form.Item 
                name="temperature" 
                label="创造性程度"
                extra="0-1之间，越高越有创造性，越低越保守"
              >
                <InputNumber min={0} max={1} step={0.1} style={{ width: '100%' }} />
              </Form.Item>

              <Form.Item 
                name="api_key" 
                label="自定义API密钥"
                extra="可选，使用自己的API密钥"
              >
                <Input.Password placeholder="留空使用系统默认配置" />
              </Form.Item>

              {recommendType === 'keyword' && (
                <>
                  <Divider orientation="left">筛选条件</Divider>
                  
                  <Form.Item name="exclude_st" valuePropName="checked">
                    <Switch checkedChildren="排除ST股票" unCheckedChildren="包含ST股票" />
                  </Form.Item>

                  <Form.Item name="min_market_cap" label="最小市值 (亿元)">
                    <InputNumber min={0} style={{ width: '100%' }} placeholder="不限制" />
                  </Form.Item>

                  <Form.Item name="board" label="交易板块">
                    <Select placeholder="不限制">
                      <Option value="main">主板</Option>
                      <Option value="gem">创业板</Option>
                      <Option value="star">科创板</Option>
                    </Select>
                  </Form.Item>

                  <Form.Item name="screen_max_candidates" label="初筛最大数量">
                    <InputNumber min={10} max={100} style={{ width: '100%' }} />
                  </Form.Item>
                </>
              )}

              <Divider orientation="left">任务设置</Divider>

              <Form.Item 
                name="priority" 
                label="任务优先级"
                extra="1-10，数字越大优先级越高"
              >
                <InputNumber min={1} max={10} style={{ width: '100%' }} />
              </Form.Item>
            </>
          )}

          <Form.Item>
            <Button 
              type="primary" 
              htmlType="submit" 
              icon={<PlayCircleOutlined />}
              loading={isLoading}
              size="large"
              block
            >
              {isLoading ? '正在启动任务...' : '启动流式推荐'}
            </Button>
          </Form.Item>
        </Form>
      </Card>

      {/* 进度监控弹窗 */}
      <Modal
        title={
          <Space>
            <span>任务执行进度</span>
            {currentTask && (
              <Tag color="blue">
                任务ID: {currentTask.task_id.substring(0, 8)}
              </Tag>
            )}
          </Space>
        }
        open={progressVisible}
        onCancel={() => setProgressVisible(false)}
        footer={[
          <Button key="close" onClick={() => setProgressVisible(false)}>
            关闭
          </Button>,
          currentTask && (
            <Button 
              key="dashboard" 
              type="primary"
              onClick={() => {
                window.open('/tasks', '_blank');
                setProgressVisible(false);
              }}
            >
              打开任务管理
            </Button>
          )
        ]}
        width={800}
        style={{ top: 20 }}
        bodyStyle={{ maxHeight: '70vh', overflow: 'auto' }}
      >
        {currentTask && (
          <StreamingProgress 
            taskId={currentTask.task_id} 
            isRunning={true} 
          />
        )}
      </Modal>
    </>
  );
};

export default StreamingRecommendForm;