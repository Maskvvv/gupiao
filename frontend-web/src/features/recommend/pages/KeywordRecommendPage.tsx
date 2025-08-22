import { useEffect, useRef, useState } from 'react'
import { Button, Card, Divider, Flex, Input, Space, Typography, message, Progress, Skeleton } from 'antd'
import { useMutation, useQueryClient } from '@tanstack/react-query'
import { addWatch } from '@/api/watchlist'
import ActionBadge from '@/components/ActionBadge'
import { startKeywordRecommend, getKeywordStatus, getKeywordResult, type KeywordStartPayload } from '@/api/recommend'

export default function KeywordRecommendPage() {
  const qc = useQueryClient()
  const [keyword, setKeyword] = useState('')
  const [period, setPeriod] = useState('1y')
  const [maxCandidates, setMaxCandidates] = useState<number>(5)
  const [excludeST, setExcludeST] = useState<boolean>(true)
  const [minMktCap, setMinMktCap] = useState<number | undefined>(undefined)
  const [provider, setProvider] = useState<string | undefined>(undefined)
  const [temperature, setTemperature] = useState<number | undefined>(undefined)
  const [apiKey, setApiKey] = useState<string | undefined>(undefined)

  const [taskId, setTaskId] = useState<string | null>(null)
  const [percent, setPercent] = useState(0)
  const [status, setStatus] = useState<'idle'|'running'|'success'|'error'|'timeout'|'stopped'>('idle')
  const [items, setItems] = useState<any[]>([])
  const cancelRef = useRef(false)

  const mAdd = useMutation({
    mutationFn: (code: string) => addWatch(code),
    onSuccess: () => { message.success('已加入自选'); qc.invalidateQueries({ queryKey: ['watchlist'] }) },
    onError: (e: any) => message.error(e?.message || '加入失败'),
  })

  const mStart = useMutation({
    mutationFn: async () => {
      const k = keyword.trim()
      if (!k) { throw new Error('关键词不能为空') }
      const payload: KeywordStartPayload = {
        keyword: k,
        period,
        max_candidates: maxCandidates,
        exclude_st: excludeST,
        min_market_cap: minMktCap,
        provider,
        temperature,
        api_key: apiKey,
      }
      const r = await startKeywordRecommend(payload)
      return r.task_id
    },
    onSuccess: (tid: string) => {
      if (!tid) { message.error('未获得任务ID'); return }
      setItems([])
      setPercent(0)
      setTaskId(tid)
      setStatus('running')
      try { localStorage.setItem('kw_rec_tid', String(tid)) } catch {}
    },
    onError: (e: any) => message.error(e?.message || '启动失败'),
  })

  // 轮询任务进度和结果，设置超时、错误兜底
  async function pollKeywordTask(tid: string) {
    cancelRef.current = false
    setStatus('running')
    try {
      const startAt = Date.now()
      while (!cancelRef.current) {
        const s = await getKeywordStatus(tid)
        if ((s as any)?.status === 'not_found') { message.warning('任务不存在或已过期'); setStatus('error'); break }
        const p = (s as any)?.percent
        if (typeof p === 'number') setPercent(Math.max(0, Math.min(100, p)))
        if ((s as any)?.status === 'done' || (s as any)?.status === 'error') break
        if (Date.now() - startAt > 120000) { message.warning('轮询超时，已停止'); setStatus('timeout'); cancelRef.current = true; break }
        await new Promise(r => setTimeout(r, 600))
      }
      if (!cancelRef.current) {
        const res = await getKeywordResult(tid)
        if ((res as any)?.error) { message.error(`任务失败：${(res as any).error}`); setStatus('error') }
        else if ((res as any)?.recommendations?.length) { setItems((res as any).recommendations); message.success('关键词推荐完成'); setStatus('success') }
        else { message.info('无推荐结果返回'); setStatus('success') }
        try { localStorage.removeItem('kw_rec_tid') } catch {}
      }
    } catch (e: any) {
      message.error(e?.message || '轮询失败')
      setStatus('error')
    }
  }

  useEffect(() => { if (taskId) pollKeywordTask(taskId); return () => { cancelRef.current = true } }, [taskId])
  useEffect(() => { try { const saved = localStorage.getItem('kw_rec_tid'); if (saved) { setTaskId(saved); setStatus('running') } } catch {} }, [])
  useEffect(() => { // 载入高级参数默认值
    try {
      const raw = localStorage.getItem('advanced_params')
      if (raw) {
        const cfg = JSON.parse(raw)
        setPeriod(cfg.period ?? '1y')
        setMaxCandidates(typeof cfg.max_candidates === 'number' ? cfg.max_candidates : 5)
        setExcludeST(cfg.exclude_st ?? true)
        setMinMktCap(typeof cfg.min_market_cap === 'number' ? cfg.min_market_cap : undefined)
        setProvider(cfg.provider)
        setTemperature(typeof cfg.temperature === 'number' ? cfg.temperature : undefined)
        setApiKey(cfg.api_key)
      }
    } catch {}
  }, [])

  return (
    <div className="container">
      <Card title="关键词推荐" extra={
        <Flex gap={8}>
          <Input placeholder="输入关键词，如 AI、机器人、低空经济…" value={keyword} onChange={e=>setKeyword(e.target.value)} onPressEnter={()=>mStart.mutate()} allowClear style={{ width: 420 }} />
          <Button type="primary" onClick={()=>mStart.mutate()} loading={mStart.isPending}>开始筛选</Button>
        </Flex>
      }>
        <Divider />
        {status !== 'idle' && (
          <>
            <Typography.Paragraph type={status==='error'?'danger': status==='success'?'success': undefined}>
              状态：{status==='running'? '进行中…' : status==='success'? '已完成' : status==='error'? '出错' : status==='timeout'? '超时' : '已停止'}
            </Typography.Paragraph>
            <Flex gap={8} align="center">
              <Progress percent={percent} status={percent>=100? 'success' : 'active'} style={{ width: 240 }} />
              <Space>
                <Button onClick={() => { cancelRef.current = true; setStatus('stopped'); message.info('已停止轮询') }}>停止轮询</Button>
                <Button danger onClick={() => { setItems([]); setPercent(0); setTaskId(null); setStatus('idle'); try { localStorage.removeItem('kw_rec_tid') } catch {}; message.success('已清空任务') }}>清空任务</Button>
              </Space>
            </Flex>
            <Divider />
          </>
        )}
        {status==='running' && !items.length && (
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(260px, 1fr))', gap: 12 }}>
            {Array.from({ length: 6 }).map((_, i) => (
              <Card key={i} size="small">
                <Skeleton active paragraph={{ rows: 3 }} />
              </Card>
            ))}
          </div>
        )}
        {items.length > 0 ? (
          <>
            <Typography.Paragraph>共推荐 {items.length} 只股票：</Typography.Paragraph>
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(260px, 1fr))', gap: 12 }}>
              {items.map((it: any) => (
                <Card key={it.股票代码} size="small" title={`${it.股票名称} (${it.股票代码})`}>
                  <Space direction="vertical" size={6} style={{ width: '100%' }}>
                    <div>评分：<b>{it.评分}</b></div>
                    <div>建议：<ActionBadge action={it.建议动作} /></div>
                    <Typography.Paragraph ellipsis={{ rows: 3, expandable: true, symbol: '更多' }}>{it.理由简述}</Typography.Paragraph>
                    <Flex justify="end">
                      <Button size="small" onClick={()=>mAdd.mutate(it.股票代码)} loading={mAdd.isPending}>加入自选</Button>
                    </Flex>
                  </Space>
                </Card>
              ))}
            </div>
          </>
        ) : status==='idle' ? (
          <Typography.Paragraph type="secondary">输入关键词，点击“开始筛选”～</Typography.Paragraph>
        ) : null}
      </Card>
    </div>
  )
}