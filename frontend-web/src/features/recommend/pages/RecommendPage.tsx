import { useMutation, useQueryClient } from '@tanstack/react-query'
import { App, Button, Card, Divider, Flex, Input, Space, Typography, Skeleton } from 'antd'
import { recommend, type RecommendItem } from '@/api/recommend'
import ActionBadge from '@/components/ActionBadge'
import { useEffect, useState } from 'react'
import { addWatch } from '@/api/watchlist'

export default function RecommendPage() {
  const [symbols, setSymbols] = useState('')
  const [provider, setProvider] = useState<string | undefined>(undefined)
  const [temperature, setTemperature] = useState<number | undefined>(undefined)
  const [apiKey, setApiKey] = useState<string | undefined>(undefined)
  const { message } = App.useApp()
  const qc = useQueryClient()
  const m = useMutation({
    mutationFn: () => recommend({ symbols: symbols.split(',').map(s=>s.trim()).filter(Boolean), provider, temperature, api_key: apiKey }),
    onError: (e: any) => message.error(e.message || '推荐失败'),
  })
  const mAdd = useMutation({
    mutationFn: (code: string) => addWatch(code),
    onSuccess: () => { message.success('已加入自选'); qc.invalidateQueries({ queryKey: ['watchlist'] }) },
    onError: (e: any) => message.error(e.message || '加入失败'),
  })

  useEffect(() => {
    try {
      const raw = localStorage.getItem('advanced_params')
      if (raw) {
        const cfg = JSON.parse(raw)
        setProvider(cfg.provider)
        setTemperature(typeof cfg.temperature === 'number' ? cfg.temperature : undefined)
        setApiKey(typeof cfg.api_key === 'string' && cfg.api_key.trim() ? cfg.api_key : undefined)
      }
    } catch {}
  }, [])

  return (
    <div className="container">
      <Card title="AI 推荐" extra={
        <Flex gap={8}>
          <Input placeholder="输入股票代码，逗号分隔，可留空尝试全市场筛选" value={symbols} onChange={e=>setSymbols(e.target.value)} onPressEnter={()=>m.mutate()} allowClear style={{ width: 420 }} />
          <Button type="primary" onClick={()=>m.mutate()} loading={m.isPending}>开始推荐</Button>
        </Flex>
      }>
        {m.isPending ? (
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(260px, 1fr))', gap: 12 }}>
            {Array.from({ length: 6 }).map((_, i) => (
              <Card key={i} size="small">
                <Skeleton active paragraph={{ rows: 3 }} />
              </Card>
            ))}
          </div>
        ) : m.data?.recommendations?.length ? (
          <>
            <Typography.Paragraph>共推荐 {m.data.recommendations.length} 只股票：</Typography.Paragraph>
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(260px, 1fr))', gap: 12 }}>
              {m.data.recommendations.map((it: RecommendItem) => (
                <Card key={it.股票代码} size="small" title={`${it.股票名称} (${it.股票代码})`}>
                  <Space direction="vertical" size={6} style={{ width: '100%' }}>
                    <div>评分：<b>{it.评分}</b></div>
                    <div>建议：<ActionBadge action={it.建议动作} /></div>
                    <Typography.Paragraph ellipsis={{ rows: 3, expandable: true, symbol: '更多' }}>{it.理由简述}</Typography.Paragraph>
                    {it.AI详细分析 ? (
                      <Typography.Paragraph type="secondary" ellipsis={{ rows: 6, expandable: true, symbol: '展开AI分析' }}>
                        <b>AI详细分析：</b>{it.AI详细分析}
                      </Typography.Paragraph>
                    ) : null}
                    <Flex justify="end">
                      <Button size="small" onClick={()=>mAdd.mutate(it.股票代码)} loading={mAdd.isPending}>加入自选</Button>
                    </Flex>
                  </Space>
                </Card>
              ))}
            </div>
            <Divider />
            <Typography.Paragraph type="secondary">
              推荐记录ID：<Typography.Text copyable={{ text: String(m.data.rec_id) }}>{m.data.rec_id}</Typography.Text>
            </Typography.Paragraph>
          </>
        ) : (
          <Typography.Paragraph type="secondary">点击“开始推荐”获取结果～</Typography.Paragraph>
        )}
      </Card>
    </div>
  )
}