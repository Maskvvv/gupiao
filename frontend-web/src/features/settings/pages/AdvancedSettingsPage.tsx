import { useEffect, useMemo, useRef, useState } from 'react'
import { App, Button, Card, Col, Divider, Form, Input, InputNumber, Row, Select, Slider, Space, Switch, Typography, Tooltip } from 'antd'

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

// 说明标签组件（含 hover 提示与内联 SVG 图标）
function LabelWithTip({ text, tip }: { text: string; tip: string }) {
  return (
    <div style={{ display: 'inline-flex', alignItems: 'center', gap: 6 }}>
      <span>{text}</span>
      <Tooltip title={tip} placement="top">
        <span aria-label="说明" style={{ display: 'inline-flex', cursor: 'help', color: '#999' }}>
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
            <circle cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="1.6" fill="none" />
            <path d="M12 10.5c-.8 0-1.3.5-1.3 1.1 0 .6.5 1 .9 1.2.7.3 1.3.6 1.3 1.4 0 .9-.8 1.6-1.9 1.6" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round" strokeLinejoin="round" />
            <circle cx="12" cy="7.5" r="1.2" fill="currentColor" />
          </svg>
        </span>
      </Tooltip>
    </div>
  )
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
              <Form.Item label={<LabelWithTip text="分析周期" tip="用于抓取历史K线数据的时间跨度，影响技术指标与AI分析上下文。值越长越全面但更耗时；支持 6m/1y/2y，留空或无效默认 1y。对自选分析、AI推荐、关键词推荐均生效。" />} name="period">
                <Select options={[
                  { value: '6m', label: '6个月' },
                  { value: '1y', label: '1年' },
                  { value: '2y', label: '2年' },
                ]} placeholder="选择周期" allowClear />
              </Form.Item>
            </Col>
            <Col xs={24} sm={12} md={8}>
              <Form.Item label={<LabelWithTip text="Top 数量" tip="结果保留的候选上限。在关键词推荐中还用于控制第二阶段的分析数量（约取 TopN 的两倍再筛选）。数值越大耗时越长，建议 5~20。" />} name="max_candidates">
                <InputNumber min={1} max={50} style={{ width: '100%' }} />
              </Form.Item>
            </Col>
            <Col xs={24} sm={12} md={8}>
              <Form.Item label={<LabelWithTip text="剔除 ST" tip="是否在市场筛选阶段排除名称包含 ST 或 *ST 的股票，仅对关键词/市场自动筛选生效；不影响手动单股分析及自选中已有标的。" />} name="exclude_st" valuePropName="checked">
                <Switch />
              </Form.Item>
            </Col>
            <Col xs={24} sm={12} md={8}>
              <Form.Item label={<LabelWithTip text="最小市值（亿）" tip="按总市值阈值过滤股票池，仅对关键词/市场自动筛选生效；单位为亿元。留空表示不限。注：市值来自行情快照，偶有解析失败时将忽略该过滤。" />} name="min_market_cap">
                <InputNumber min={0} placeholder="可留空" style={{ width: '100%' }} />
              </Form.Item>
            </Col>
            <Col xs={24} sm={12} md={8}>
              <Form.Item label={<LabelWithTip text="AI Provider" tip="指定调用的AI服务商，留空使用服务器默认。可选：DeepSeek / OpenAI / Gemini。不同服务商能力与计费不同，请按需选择。" />} name="provider">
                <Select allowClear placeholder="自动（后端配置）" options={[
                  { value: 'deepseek', label: 'DeepSeek' },
                  { value: 'openai', label: 'OpenAI' },
                  { value: 'gemini', label: 'Gemini' },
                ]} />
              </Form.Item>
            </Col>
            <Col xs={24} sm={12} md={8}>
              <Form.Item label={<LabelWithTip text="Temperature" tip="取值 0~1，控制AI输出的随机性：越低越稳定、越高越发散。建议 0.2~0.7；留空使用后端默认值。" />} name="temperature">
                <InputNumber min={0} max={1} step={0.1} placeholder="可留空" style={{ width: '100%' }} />
              </Form.Item>
            </Col>
            <Col xs={24} sm={24} md={16}>
              <Form.Item label={<LabelWithTip text="API Key" tip="当选择需要密钥的服务商时可在此填写；不填则尝试使用服务器端配置（若有）。密钥将保存在本地浏览器并随请求发送，请妥善保管。" />} name="api_key">
                <Input.Password placeholder="可留空，使用服务器配置" autoComplete="off" />
              </Form.Item>
            </Col>
          </Row>

          <Divider>权重设置</Divider>
          <Row gutter={[12, 12]}>
            <Col xs={24} sm={12} md={8}>
              <Form.Item label={<LabelWithTip text="技术面" tip="控制AI分析中对技术指标（均线/RSI/MACD等）的重视程度。不会改变技术指标的计算本身，但会影响AI建议与理由的侧重。" />} name={['weights','technical']}>
                <Slider min={0} max={1} step={0.05} tooltip={{ formatter: v => `${v}` }} />
              </Form.Item>
            </Col>
            <Col xs={24} sm={12} md={8}>
              <Form.Item label={<LabelWithTip text="宏观情绪" tip="控制AI对市场情绪/宏观环境（政策、流动性、经济数据、行业周期等）的重视程度，仅影响AI结论的权重比重。" />} name={['weights','macro_sentiment']}>
                <Slider min={0} max={1} step={0.05} tooltip={{ formatter: v => `${v}` }} />
              </Form.Item>
            </Col>
            <Col xs={24} sm={12} md={8}>
              <Form.Item label={<LabelWithTip text="新闻事件" tip="控制AI对公司公告、行业政策与突发事件等信息的重视程度，仅影响AI分析的侧重与表述。" />} name={['weights','news_events']}>
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