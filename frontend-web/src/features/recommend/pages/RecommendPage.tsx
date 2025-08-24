import { useMutation, useQueryClient } from '@tanstack/react-query'
import { App, Button, Card, Divider, Flex, Input, Space, Typography, Skeleton, Segmented, InputNumber } from 'antd'
import { recommend, type RecommendItem, recommendMarket, type MarketRecommendPayload } from '@/api/recommend'
import ActionBadge from '@/components/ActionBadge'
import { useEffect, useMemo, useState } from 'react'
import { addWatch } from '@/api/watchlist'

export default function RecommendPage() {
  const [symbols, setSymbols] = useState('')
  const [provider, setProvider] = useState<string | undefined>(undefined)
  const [temperature, setTemperature] = useState<number | undefined>(undefined)
  const [apiKey, setApiKey] = useState<string | undefined>(undefined)
  const [board, setBoard] = useState<'all'|'main'|'gem'|'star'>('all')
  const [maxCandidates, setMaxCandidates] = useState<number | undefined>(undefined)
  const [excludeST, setExcludeST] = useState<boolean | undefined>(undefined)
  const [minMktCap, setMinMktCap] = useState<number | undefined>(undefined)
  const { message } = App.useApp()
  const qc = useQueryClient()

  const isMarketWide = useMemo(() => symbols.split(',').map(s=>s.trim()).filter(Boolean).length === 0, [symbols])

  const m = useMutation({
    mutationFn: async () => {
      if (isMarketWide) {
        // 全市场推荐（无 symbols）
        const payload: MarketRecommendPayload = {
          provider, temperature, api_key: apiKey,
          board: board === 'all' ? undefined : board,
          max_candidates: maxCandidates,
          exclude_st: excludeST,
          min_market_cap: minMktCap,
        }
        return await recommendMarket(payload)
      } else {
        // 指定 symbols 的传统推荐
        return await recommend({ symbols: symbols.split(',').map(s=>s.trim()).filter(Boolean), provider, temperature, api_key: apiKey })
      }
    },
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
        setMaxCandidates(typeof cfg.max_candidates === 'number' ? cfg.max_candidates : undefined)
        setExcludeST(typeof cfg.exclude_st === 'boolean' ? cfg.exclude_st : undefined)
        setMinMktCap(typeof cfg.min_market_cap === 'number' ? cfg.min_market_cap : undefined)
      }
    } catch {}
  }, [])

  const extraControls = (
    <Flex gap={8} wrap="wrap" align="center">
      <Input placeholder="输入股票代码，逗号分隔，可留空尝试全市场筛选" value={symbols} onChange={e=>setSymbols(e.target.value)} onPressEnter={()=>m.mutate()} allowClear style={{ width: 420 }} />
      {isMarketWide ? (
        <>
          <Segmented
            value={board}
            onChange={(v)=>setBoard(v as any)}
            options={[
              { label: '全部', value: 'all' },
              { label: '主板', value: 'main' },
              { label: '创业板', value: 'gem' },
              { label: '科创板', value: 'star' },
            ]}
          />
          <InputNumber min={1} max={200} placeholder="候选上限" value={maxCandidates} onChange={(v)=>setMaxCandidates(v ?? undefined)} />
          <Segmented
            value={excludeST === undefined ? 'auto' : (excludeST ? 'yes' : 'no')}
            onChange={(v)=>setExcludeST(v === 'auto' ? undefined : v === 'yes')}
            options={[{label:'ST', value:'auto'}, {label:'排除ST', value:'yes'}, {label:'包含ST', value:'no'}]}
          />
          <InputNumber min={0} step={1} placeholder="最小市值（亿）" value={minMktCap} onChange={(v)=>setMinMktCap(v ?? undefined)} />
        </>
      ) : null}
      <Button type="primary" onClick={()=>m.mutate()} loading={m.isPending}>开始推荐</Button>
    </Flex>
  )

  return (
    <div className="container">
      <Card title="AI 推荐" extra={extraControls}>
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