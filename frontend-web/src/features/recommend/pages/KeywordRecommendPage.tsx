import { useEffect, useRef, useState } from 'react'
import { App, Button, Card, Divider, Flex, Input, Space, Typography, Progress, Skeleton, InputNumber, Segmented, Tooltip } from 'antd'
import { useMutation, useQueryClient } from '@tanstack/react-query'
import { addWatch } from '@/api/watchlist'
import ActionBadge from '@/components/ActionBadge'
import { startKeywordRecommend, getKeywordStatus, getKeywordResult, type KeywordStartPayload, type KeywordTaskStatus } from '@/api/recommend'

export default function KeywordRecommendPage() {
  const qc = useQueryClient()
  const { message } = App.useApp()
  const [keyword, setKeyword] = useState('')
  const [period, setPeriod] = useState('1y')
  const [maxCandidates, setMaxCandidates] = useState<number>(5)
  const [excludeST, setExcludeST] = useState<boolean>(true)
  const [minMktCap, setMinMktCap] = useState<number | undefined>(undefined)
  const [provider, setProvider] = useState<string | undefined>(undefined)
  const [temperature, setTemperature] = useState<number | undefined>(undefined)
  const [apiKey, setApiKey] = useState<string | undefined>(undefined)
  const [board, setBoard] = useState<'all'|'main'|'gem'|'star'>('all')

  const [taskId, setTaskId] = useState<string | null>(null)
  const [percent, setPercent] = useState(0)
  const [phase, setPhase] = useState<'screen'|'analyze'|'done'|undefined>(undefined)
  const [phasePerc, setPhasePerc] = useState<{screen:number; analyze:number}>({ screen: 0, analyze: 0 })
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
      if (!k) throw new Error('请输入关键词')
      const payload: KeywordStartPayload = {
        keyword: k,
        period,
        max_candidates: maxCandidates,
        weights: undefined,
        exclude_st: excludeST,
        min_market_cap: minMktCap,
        board: board === 'all' ? undefined : board,
        provider,
        temperature,
        api_key: apiKey,
      }
      const r = await startKeywordRecommend(payload)
      return r
    },
    onSuccess: (r) => {
      if (r?.task_id) {
        setTaskId(r.task_id)
        setStatus('running')
        cancelRef.current = false
        try { localStorage.setItem('kw_rec_tid', r.task_id) } catch {}
        poll()
      } else {
        message.error('启动任务失败')
      }
    },
    onError: (e: any) => message.error(e?.message || '启动失败'),
  })

  useEffect(() => {
    // 读取高级参数
    try {
      const raw = localStorage.getItem('advanced_params')
      if (raw) {
        const cfg = JSON.parse(raw)
        setProvider(cfg.provider)
        setTemperature(typeof cfg.temperature === 'number' ? cfg.temperature : undefined)
        setApiKey(typeof cfg.api_key === 'string' && cfg.api_key.trim() ? cfg.api_key : undefined)
      }
    } catch {}

    // 恢复未完成任务
    try {
      const tid = localStorage.getItem('kw_rec_tid')
      if (tid) { setTaskId(tid); setStatus('running'); cancelRef.current = false; poll() }
    } catch {}
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  // 推断阶段进度（后端未返回 phases 时的兜底）
  const inferPhases = (p: number): {screen:number; analyze:number} => {
    const pct = Math.max(0, Math.min(100, p))
    if (pct <= 50) return { screen: pct * 2, analyze: 0 }
    const analyze = Math.min(100, (pct - 50) * 2)
    return { screen: 100, analyze }
  }

  const poll = async () => {
    if (!taskId) return
    try {
      const s: KeywordTaskStatus = await getKeywordStatus(taskId)
      if ((s as any)?.status === 'not_found') { setStatus('timeout'); return }
      const done = (s as any)?.done || 0
      const total = (s as any)?.total || 100
      const pct = Math.round((done / Math.max(1, total)) * 100)
      setPercent(pct)
      const phases = (s as any)?.phases || null
      const pp = phases ? { screen: Math.round((phases.screen || 0)), analyze: Math.round((phases.analyze || 0)) } : inferPhases(pct)
      setPhasePerc(pp)
      setPhase((s as any)?.phase)

      if (pct >= 100 || (s as any)?.status === 'done') {
        const res = await getKeywordResult(taskId)
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

  // 数值格式化：两位小数；异常/空值返回 “-”
  const fmt2 = (v: any) => (v === null || v === undefined || isNaN(Number(v)) ? '-' : Number(v).toFixed(2))

  return (
    <div className="container">
      <Card title="关键词推荐" extra={
        <Flex gap={8}>
          <Input placeholder="输入关键词" value={keyword} onChange={e=>setKeyword(e.target.value)} onPressEnter={()=>mStart.mutate()} allowClear style={{ width: 200 }} />
          <Segmented
            options={[
              { label: '全部', value: 'all' },
              { label: '主板', value: 'main' },
              { label: '创业板', value: 'gem' },
              { label: '科创板', value: 'star' },
            ]}
            value={board}
            onChange={(v)=>setBoard(v as any)}
          />
          <Input placeholder="周期(如1y)" value={period} onChange={e=>setPeriod(e.target.value)} style={{ width: 100 }} />
          <InputNumber placeholder="候选上限" value={maxCandidates} onChange={(v)=>setMaxCandidates(Number(v||0))} style={{ width: 120 }} min={1} />
          <Input placeholder="最小市值(可空)" value={minMktCap ?? ''} onChange={e=>setMinMktCap(e.target.value ? Number(e.target.value) : undefined)} style={{ width: 140 }} />
          <Button type="primary" onClick={()=>mStart.mutate()} loading={mStart.isPending}>开始筛选</Button>
        </Flex>
      }>
        {status==='running' ? (
          <Space direction="vertical" style={{ width: '100%' }}>
            <Progress percent={percent} status={percent>=100?'success':'active'} format={(p)=>`进度 ${p}%`} />
            <Flex gap={8}>
              <Card size="small" title="阶段进度" style={{ flex: 1 }}>
                <div>筛选：{phasePerc.screen}%</div>
                <div>分析：{phasePerc.analyze}%</div>
              </Card>
              <Card size="small" title="状态" style={{ width: 240 }}>
                <div>阶段：{phase || '推断中'}</div>
                <div>任务ID：{taskId}</div>
              </Card>
            </Flex>
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(260px, 1fr))', gap: 12 }}>
              {Array.from({ length: Math.max(3, Math.min(12, Math.ceil((percent||0)/10))) }).map((_, i) => (
                <Card key={i} size="small">
                  <Skeleton active paragraph={{ rows: 3 }} />
                </Card>
              ))}
            </div>
          </Space>
        ) : status==='success' && items?.length ? (
          <>
            <Typography.Paragraph>共推荐 {items.length} 只股票：</Typography.Paragraph>
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(260px, 1fr))', gap: 12 }}>
              {items.map((it: any) => (
                <Card key={it.股票代码} size="small" title={`${it.股票名称} (${it.股票代码})`}>
                  <Space direction="vertical" size={6} style={{ width: '100%' }}>
                    <Flex gap={8} wrap align="center">
                      <Tooltip title="技术面打分，范围 0-10"><span>技术分：<b>{fmt2(it.评分)}</b></span></Tooltip>
                      <Tooltip title="AI 给出的分析信心，范围 0-10"><span>AI信心：<b>{fmt2(it?.AI信心)}</b></span></Tooltip>
                      <Tooltip title="融合分 = 技术分 与 AI信心 的加权融合，范围 0-10"><span>融合分：<b>{fmt2(it?.融合分)}</b></span></Tooltip>
                    </Flex>
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
          </>
        ) : status==='idle' ? (
          <Typography.Paragraph type="secondary">输入关键词，点击“开始筛选”～</Typography.Paragraph>
        ) : null}
      </Card>
    </div>
  )
}