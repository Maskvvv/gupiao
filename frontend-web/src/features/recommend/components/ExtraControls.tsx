import React, { useState } from 'react';
import { Form, Button, Space, Input, Select, InputNumber, Switch } from 'antd';
import { PlayCircleOutlined } from '@ant-design/icons';
import type { RecommendConfig } from '../../../api/recommend';

const { Option } = Select;

interface ExtraControlsProps {
  onRecommend: (config: RecommendConfig) => void;
  loading?: boolean;
}

export const ExtraControls: React.FC<ExtraControlsProps> = ({ onRecommend, loading }) => {
  const [form] = Form.useForm();

  const handleSubmit = (values: any) => {
    const config: RecommendConfig = {
      symbols: values.symbols ? values.symbols.split(',').map((s: string) => s.trim()).filter(Boolean) : undefined,
      period: values.period,
      weights: {
        technical: values.technical_weight,
        macro_sentiment: values.macro_weight,
        news_events: values.news_weight,
      },
      provider: values.provider,
      temperature: values.temperature,
      api_key: values.api_key,
    };

    onRecommend(config);
  };

  return (
    <Form
      form={form}
      layout="vertical"
      onFinish={handleSubmit}
      initialValues={{
        period: '1y',
        technical_weight: 0.4,
        macro_weight: 0.35,
        news_weight: 0.25,
        temperature: 0.7
      }}
    >
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))', gap: 16 }}>
        <Form.Item
          name="symbols"
          label="指定股票（可选）"
          help="多个股票代码用逗号分隔，如：000001,000002"
        >
          <Input placeholder="留空则推荐全市场" />
        </Form.Item>

        <Form.Item name="period" label="分析周期">
          <Select>
            <Option value="1y">1年</Option>
            <Option value="6mo">6个月</Option>
            <Option value="3mo">3个月</Option>
            <Option value="1mo">1个月</Option>
          </Select>
        </Form.Item>

        <Form.Item name="provider" label="AI提供商">
          <Select placeholder="使用默认">
            <Option value="openai">OpenAI</Option>
            <Option value="deepseek">DeepSeek</Option>
            <Option value="gemini">Gemini</Option>
          </Select>
        </Form.Item>

        <Form.Item name="temperature" label="AI创造性">
          <InputNumber min={0} max={2} step={0.1} style={{ width: '100%' }} />
        </Form.Item>

        <Form.Item name="technical_weight" label="技术权重">
          <InputNumber min={0} max={1} step={0.1} style={{ width: '100%' }} />
        </Form.Item>

        <Form.Item name="macro_weight" label="宏观权重">
          <InputNumber min={0} max={1} step={0.1} style={{ width: '100%' }} />
        </Form.Item>

        <Form.Item name="news_weight" label="新闻权重">
          <InputNumber min={0} max={1} step={0.1} style={{ width: '100%' }} />
        </Form.Item>

        <Form.Item name="api_key" label="API密钥（可选）">
          <Input.Password placeholder="使用环境变量配置" />
        </Form.Item>
      </div>

      <Form.Item style={{ marginTop: 16 }}>
        <Button 
          type="primary" 
          htmlType="submit" 
          loading={loading}
          icon={<PlayCircleOutlined />}
          size="large"
        >
          开始推荐
        </Button>
      </Form.Item>
    </Form>
  );
};

export default ExtraControls;