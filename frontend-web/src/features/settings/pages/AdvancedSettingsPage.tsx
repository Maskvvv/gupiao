import { useEffect, useMemo, useRef, useState } from 'react'
import { App, Button, Card, Col, Divider, Flex, Form, Input, InputNumber, Row, Select, Slider, Space, Switch, Typography } from 'antd'

// 本地存储键
const LS_KEY = 'advanced_params'

// 安全读取本地存储
function loadParams(): any {
  try {
    const raw = localStorage.getItem(LS_KEY)
    return raw ? JSON.parse(raw) : {}
  } catch { return {} }
}

// 节流保存，避免频繁写入
function useThrottledSaver(delay = 400) {
  const timer = useRef<number | null>(null)
  return (obj: any) => {
    if (timer.current) window.clearTimeout(timer.current)
    timer.current = window.setTimeout(() => {
      try { localStorage.setItem(LS_KEY, JSON.stringify(obj)) } catch {}
    }, delay)
  }
}

export default function AdvancedSettingsPage() {
  const { message } = App.useApp()
  const [form] = Form.useForm()
  const save = useThrottledSaver(400)
  const [loaded, setLoaded] = useState(false)

  // 初始加载
  useEffect(() => {
    const data = loadParams()
    form.setFieldsValue({
      period: data.period ?? '1y',
      max_candidates: data.max_candidates ?? 10,
      exclude_st: data.exclude_st ?? true,
      min_market_cap: data.min_market_cap,
      provider: data.provider,
      temperature: data.temperature,
      api_key: data.api_key,
      weights: {
        technical: data?.weights?.technical ?? 0.5,
        macro_sentiment: data?.weights?.macro_sentiment ?? 0.3,
        news_events: data?.weights?.news_events ?? 0.2,
      }
    })
    setLoaded(true)
  }, [form])

  // 值变更自动保存
  const onValuesChange = (_: any, all: any) => {
    const payload = {
      period: all.period,
      max_candidates: all.max_candidates,
      exclude_st: all.exclude_st,
      min_market_cap: all.min_market_cap,
      provider: all.provider,
      temperature: all.temperature,
      api_key: all.api_key,
      weights: all.weights,
    }
    save(payload)
  }

  const resetAll = () => {
    const defaults = {
      period: '1y', max_candidates: 10, exclude_st: true, min_market_cap: undefined,
      provider: undefined, temperature: undefined, api_key: undefined,
      weights: { technical: 0.5, macro_sentiment: 0.3, news_events: 0.2 }
    }
    form.setFieldsValue(defaults)
    try { localStorage.setItem(LS_KEY, JSON.stringify(defaults)) } catch {}
    message.success('已恢复默认并保存')
  }

  const weightSum = Form.useWatch(['weights'], form)
  const sumText = useMemo(() => {
    const w = weightSum || {}
    const s = Number((w.technical ?? 0)) + Number((w.macro_sentiment ?? 0)) + Number((w.news_events ?? 0))
    return s.toFixed(2)
  }, [weightSum])

  return (
    <div className="container">
      <Card title="高级参数设置" extra={<Space>
        <Button onClick={resetAll}>恢复默认</Button>
      </Space>}>
        <Typography.Paragraph type="secondary" style={{ marginBottom: 12 }}>
          参数将自动保存到浏览器本地存储，下次访问自动加载～
        </Typography.Paragraph>
        <Form
          form={form}
          layout="vertical"
          onValuesChange={onValuesChange}
          style={{ width: '100%' }}
        >
          <Row gutter={[12, 12]}>
            <Col xs={24} sm={12} md={8}>
              <Form.Item label="分析周期" name="period">
                <Select options={[
                  { value: '6m', label: '6个月' },
                  { value: '1y', label: '1年' },
                  { value: '2y', label: '2年' },
                ]} placeholder="选择周期" allowClear />
              </Form.Item>
            </Col>
            <Col xs={24} sm={12} md={8}>
              <Form.Item label="Top 数量" name="max_candidates">
                <InputNumber min={1} max={50} style={{ width: '100%' }} />
              </Form.Item>
            </Col>
            <Col xs={24} sm={12} md={8}>
              <Form.Item label="剔除 ST" name="exclude_st" valuePropName="checked">
                <Switch />
              </Form.Item>
            </Col>
            <Col xs={24} sm={12} md={8}>
              <Form.Item label="最小市值（亿）" name="min_market_cap">
                <InputNumber min={0} placeholder="可留空" style={{ width: '100%' }} />
              </Form.Item>
            </Col>
            <Col xs={24} sm={12} md={8}>
              <Form.Item label="AI Provider" name="provider">
                <Select allowClear placeholder="自动（后端配置）" options={[
                  { value: 'deepseek', label: 'DeepSeek' },
                  { value: 'openai', label: 'OpenAI' },
                  { value: 'gemini', label: 'Gemini' },
                ]} />
              </Form.Item>
            </Col>
            <Col xs={24} sm={12} md={8}>
              <Form.Item label="Temperature" name="temperature">
                <InputNumber min={0} max={1} step={0.1} placeholder="可留空" style={{ width: '100%' }} />
              </Form.Item>
            </Col>
            <Col xs={24} sm={24} md={16}>
              <Form.Item label="API Key" name="api_key">
                <Input.Password placeholder="可留空，使用服务器配置" autoComplete="off" />
              </Form.Item>
            </Col>
          </Row>

          <Divider>权重设置</Divider>
          <Row gutter={[12, 12]}>
            <Col xs={24} sm={12} md={8}>
              <Form.Item label="技术面" name={['weights','technical']}>
                <Slider min={0} max={1} step={0.05} tooltip={{ formatter: v => `${v}` }} />
              </Form.Item>
            </Col>
            <Col xs={24} sm={12} md={8}>
              <Form.Item label="宏观情绪" name={['weights','macro_sentiment']}>
                <Slider min={0} max={1} step={0.05} tooltip={{ formatter: v => `${v}` }} />
              </Form.Item>
            </Col>
            <Col xs={24} sm={12} md={8}>
              <Form.Item label="新闻事件" name={['weights','news_events']}>
                <Slider min={0} max={1} step={0.05} tooltip={{ formatter: v => `${v}` }} />
              </Form.Item>
            </Col>
          </Row>
          <Typography.Paragraph type="secondary">
            当前权重和：{sumText}（不强制等于1，可根据需要调整）
          </Typography.Paragraph>
        </Form>
      </Card>
    </div>
  )
}