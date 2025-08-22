import { useMemo, useState, useEffect, useRef } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { listWatchlist, addWatch, removeWatch, analyzeOne, type WatchItem, listHistory, startBatchAnalyze, getBatchStatus, getBatchResult } from '@/api/watchlist'
import { App, Button, Card, Flex, Input, Space, Table, Typography, Drawer, Pagination, Divider, Progress, Modal, Tabs } from 'antd'
import ActionBadge from '@/components/ActionBadge'
import ReactECharts from 'echarts-for-react'

export default function WatchlistPage() {
  const qc = useQueryClient()
  const { message, modal } = App.useApp()
  const { data: items = [], isLoading } = useQuery({ queryKey: ['watchlist'], queryFn: listWatchlist, refetchOnWindowFocus: false, retry: 1 })
  const [symbol, setSymbol] = useState('')
  const [openHist, setOpenHist] = useState(false)
  const [histSymbol, setHistSymbol] = useState<string | null>(null)
  const [page, setPage] = useState(1)
  const [pageSize, setPageSize] = useState(10)
  const [selected, setSelected] = useState<string[]>([])
  const [batchOpen, setBatchOpen] = useState(false)
  const [taskId, setTaskId] = useState<string | null>(null)
  const [percent, setPercent] = useState(0)
  const [batchItems, setBatchItems] = useState<any[]>([])
  const cancelRef = useRef(false)
  const [batchStatus, setBatchStatus] = useState<'idle'|'running'|'success'|'error'|'timeout'|'stopped'>('idle')
  const [openQuote, setOpenQuote] = useState(false)
  const [quoteSymbol, setQuoteSymbol] = useState<string | null>(null)
  const [chartIdx, setChartIdx] = useState(0)
  const [isResizing, setIsResizing] = useState(false)
  const [quoteSize, setQuoteSize] = useState<{ w: number; h: number }>({ w: 1100, h: Math.max(560, Math.round(window.innerHeight * 0.75)) })
  
  const handleResizeMouseDown = (e: React.MouseEvent<HTMLDivElement>) => {
    e.preventDefault()
    setIsResizing(true)
    const prevSelect = document.body.style.userSelect
    document.body.style.userSelect = 'none'
    const startX = e.clientX
    const startY = e.clientY
    const startW = quoteSize.w
    const startH = quoteSize.h
    const onMove = (ev: MouseEvent) => {
      const dw = ev.clientX - startX
      const dh = ev.clientY - startY
      setQuoteSize({ w: Math.max(780, startW + dw), h: Math.max(480, startH + dh) })
    }
    const onUp = () => {
      window.removeEventListener('mousemove', onMove)
      window.removeEventListener('mouseup', onUp)
      setIsResizing(false)
      document.body.style.userSelect = prevSelect
    }
    window.addEventListener('mousemove', onMove)
    window.addEventListener('mouseup', onUp)
  }

  useEffect(() => {
    if (openQuote && quoteSymbol) setChartIdx(0)
  }, [openQuote, quoteSymbol])

  // 读取高级参数（provider/temperature/api_key），兜底处理异常
  const [provider, setProvider] = useState<string | undefined>(undefined)
  const [temperature, setTemperature] = useState<number | undefined>(undefined)
  const [apiKey, setApiKey] = useState<string | undefined>(undefined)
  useEffect(() => {
    try {
      const raw = localStorage.getItem('advanced_params')
      if (!raw) return
      const cfg = JSON.parse(raw || '{}') || {}
      setProvider(cfg.provider || undefined)
      setTemperature(typeof cfg.temperature === 'number' ? cfg.temperature : undefined)
      setApiKey(cfg.api_key || undefined)
    } catch (e) {
      // 忽略解析错误
    }
  }, [])

  const { data: hist, refetch: refetchHist, isFetching: fetchingHist } = useQuery({
    queryKey: ['history', histSymbol, page, pageSize],
    queryFn: () => listHistory(histSymbol || '', page, pageSize),
    enabled: !!histSymbol,
  })

  // 历史评分趋势图配置（空数据也要兜底）
  const chartOption = useMemo(() => {
    const ds = (hist?.items || [])
      .filter(it => it.综合评分 !== null && it.综合评分 !== undefined)
      .map(it => ({ t: it.时间 || '', s: Number(it.综合评分) }))
    return {
      tooltip: { trigger: 'axis' },
      grid: { left: 8, right: 8, top: 24, bottom: 24, containLabel: true },
      xAxis: { type: 'category', data: ds.map(d => d.t) },
      yAxis: { type: 'value' },
      series: [{ type: 'line', data: ds.map(d => d.s), smooth: true, areaStyle: {}, symbol: 'circle' }],
    }
  }, [hist?.items])

  const mAdd = useMutation({
    mutationFn: (s: string) => addWatch(s.trim()),
    onSuccess: () => { message.success('已加入自选'); qc.invalidateQueries({ queryKey: ['watchlist'] }) },
    onError: (e: any) => message.error(e.message || '添加失败'),
  })

  const mRemove = useMutation({
    mutationFn: (s: string) => removeWatch(s),
    onSuccess: () => { message.success('已移除'); qc.invalidateQueries({ queryKey: ['watchlist'] }) },
    onError: (e: any) => message.error(e.message || '移除失败'),
  })

  const mAnalyze = useMutation({
    mutationFn: async (s: string) => {
      if ((provider || '').toLowerCase() === 'deepseek' && !apiKey) {
        message.warning('DeepSeek API Key 未配置，将尝试使用后端默认密钥')
      }
      return analyzeOne(s, { provider, temperature, api_key: apiKey })
    },
    onSuccess: () => { message.success('已触发分析'); qc.invalidateQueries({ queryKey: ['watchlist'] }) },
    onError: (e: any) => message.error(e.message || '分析失败'),
  })

  const mBatchStart = useMutation({
    mutationFn: async (symbols: string[] | undefined) => {
      if ((provider || '').toLowerCase() === 'deepseek' && !apiKey) {
        message.warning('DeepSeek API Key 未配置，将尝试使用后端默认密钥')
      }
      const payload: any = { symbols: symbols && symbols.length ? symbols : undefined }
      if (provider) payload.provider = provider
      if (typeof temperature === 'number') payload.temperature = temperature
      if (apiKey) payload.api_key = apiKey
      const r = await startBatchAnalyze(payload)
      return r.task_id
    },
    onSuccess: (tid) => {
      if (!tid) { message.error('未获得任务ID'); return }
      setBatchItems([])
      setPercent(0)
      setTaskId(tid)
      setBatchOpen(true)
      setBatchStatus('running')
      try { localStorage.setItem('watch_batch_tid', String(tid)) } catch {}
    },
    onError: (e: any) => message.error(e?.message || '批量分析启动失败'),
  })

  async function pollBatch(tid: string) {
    cancelRef.current = false
    setBatchStatus('running')
    try {
      const startAt = Date.now()
      // 轮询进度
      while (!cancelRef.current) {
        const s = await getBatchStatus(tid)
        if (s?.status === 'not_found') { message.warning('任务不存在或已过期'); setBatchStatus('error'); break }
        if (typeof s?.percent === 'number') setPercent(Math.max(0, Math.min(100, s.percent)))
        if (s?.status === 'done' || s?.status === 'error') break
        if (Date.now() - startAt > 120000) { message.warning('轮询超时，已停止'); setBatchStatus('timeout'); cancelRef.current = true; break }
        await new Promise(r => setTimeout(r, 600))
      }
      // 获取结果
      if (!cancelRef.current) {
        const res = await getBatchResult(tid)
        if ((res as any)?.error) {
          message.error(`任务失败：${(res as any).error}`)
          setBatchStatus('error')
        } else if (res && Array.isArray(res.items) && res.items.length) {
          setBatchItems(res.items)
          message.success('批量分析完成')
          setBatchStatus('success')
          qc.invalidateQueries({ queryKey: ['watchlist'] })
        } else {
          message.info('批量任务无结果返回')
          setBatchStatus('success')
        }
        try { localStorage.removeItem('watch_batch_tid') } catch {}
      }
    } catch (e: any) {
      message.error(e?.message || '轮询失败')
      setBatchStatus('error')
    }
  }

  useEffect(() => {
    if (taskId) {
      pollBatch(taskId)
    }
    return () => { cancelRef.current = true }
  }, [taskId])

  // 页面刷新后尝试恢复批量任务
  useEffect(() => {
    try {
      const saved = localStorage.getItem('watch_batch_tid')
      if (saved) { setTaskId(saved); setBatchOpen(true); setBatchStatus('running') }
    } catch {}
  }, [])

  const columns = [
    { title: '股票代码', dataIndex: '股票代码', width: 120 },
    { title: '股票名称', dataIndex: '股票名称', width: 140 },
    { title: '综合评分', dataIndex: '综合评分', width: 100, render: (v: number | null) => v ?? '-' },
    { title: '操作建议', dataIndex: '操作建议', width: 120, render: (v: string | null) => <ActionBadge action={v} /> },
    { title: '理由摘要', dataIndex: '分析理由摘要' },
    { title: '加入日期', dataIndex: '加入日期', width: 110 },
    { title: '累计涨跌幅', dataIndex: '累计涨跌幅(%)', width: 110, render: (v: number | null) => {
      if (v === null || v === undefined || isNaN(Number(v))) return '-'
      const num = Number(v)
      const color = num > 0 ? '#16a34a' : (num < 0 ? '#dc2626' : undefined)
      const sign = num > 0 ? '+' : ''
      return <span style={{ color }}>{sign}{num.toFixed(2)}%</span>
    } },
    { title: '累计涨跌额', dataIndex: '累计涨跌额', width: 110, render: (v: number | null) => {
      if (v === null || v === undefined || isNaN(Number(v))) return '-'
      const num = Number(v)
      const color = num > 0 ? '#16a34a' : (num < 0 ? '#dc2626' : undefined)
      const sign = num > 0 ? '+' : ''
      return <span style={{ color }}>{sign}{num.toFixed(2)}</span>
    } },
    { title: '最近分析时间', dataIndex: '最近分析时间', width: 180 },
    {
      title: '操作', key: 'ops', width: 280,
      render: (_: any, r: WatchItem) => (
        <Space>
          <Button size="small" onClick={() => mAnalyze.mutate(r.股票代码)} loading={mAnalyze.isPending}>重新分析</Button>
          <Button size="small" onClick={() => { setHistSymbol(r.股票代码); setOpenHist(true); refetchHist() }}>历史</Button>
          <Button size="small" onClick={() => { setQuoteSymbol(r.股票代码); setOpenQuote(true) }}>行情</Button>
          <Button size="small" danger onClick={() => mRemove.mutate(r.股票代码)} loading={mRemove.isPending}>移除</Button>
        </Space>
      )
    },
  ] as any

  const buildQuoteSources = (sym?: string | null): { name: string; url: string }[] => {
    if (!sym) return []
    const raw = (sym || '').trim().toUpperCase()
    const s = raw.replace(/[^\d]/g, '').slice(0, 6)
    if (!s) return []
    return [
      { name: '百度股市通', url: `https://gushitong.baidu.com/stock/ab-${s}` },
      { name: '同花顺', url: `https://stockpage.10jqka.com.cn/${s}/` },
    ]
  }
  
  // 兼容旧调用（默认取第一个）
  const buildQuoteUrl = (sym?: string | null) => {
    const s = buildQuoteSources(sym)
    return s[0]?.url || ''
  }

  return (
    <div className="container">
      <Card title="自选股票">
        <Flex gap={8} style={{ marginBottom: 12 }}>
          <Input
            value={symbol}
            onChange={(e) => setSymbol(e.target.value)}
            placeholder="输入股票代码，如 600036 或 000001"
            style={{ width: 260 }}
            onPressEnter={() => symbol.trim() && mAdd.mutate(symbol)}
            allowClear
          />
          <Button type="primary" onClick={() => symbol.trim() && mAdd.mutate(symbol)} loading={mAdd.isPending}>加入自选</Button>
          <Button
            onClick={() => {
              if (!items || items.length === 0) { message.info('暂无自选股票可分析'); return }
              if (selected.length === 0) {
                modal.confirm({
                  title: '确认分析全部自选股票？',
                  content: '未选择任何股票，将默认分析当前全部自选列表。',
                  okText: '开始分析',
                  cancelText: '取消',
                  onOk: () => mBatchStart.mutate(undefined),
                })
              } else {
                mBatchStart.mutate(selected)
              }
            }}
            disabled={!items || items.length === 0 || !!taskId}
            loading={mBatchStart.isPending}
          >
             批量分析{selected.length ? `（${selected.length}）` : ''}
          </Button>
         </Flex>
 
         <Table
           size="small"
           rowKey={(r: WatchItem) => r.股票代码}
           rowSelection={{ selectedRowKeys: selected, onChange: (keys) => setSelected(keys as string[]) }}
           dataSource={items}
           columns={columns}
           loading={isLoading}
           pagination={false}
           locale={{ emptyText: '暂无自选股票，先添加一只吧～' }}
         />
      </Card>

      <Drawer title={`${histSymbol || ''} 历史分析`} width={720} open={openHist} onClose={() => setOpenHist(false)} destroyOnClose>
        {fetchingHist ? '加载中...' : (
          <>
            {(hist?.items?.length || 0) > 0 && (
              <>
                <ReactECharts option={chartOption} style={{ height: 240 }} notMerge lazyUpdate />
                <Divider style={{ margin: '12px 0' }} />
              </>
            )}
            <Table
              size="small"
              rowKey={(_, idx) => String(idx)}
              dataSource={hist?.items || []}
              columns={[
                { title: '时间', dataIndex: '时间', key: 't', width: 180 },
                { title: '评分', dataIndex: '综合评分', key: 's', width: 80 },
                { title: '建议', dataIndex: '操作建议', key: 'a', width: 120, render: (v: any) => <ActionBadge action={v} /> },
                { title: '理由摘要', dataIndex: '分析理由摘要', key: 'b' },
              ] as any}
              pagination={false}
            />
            <Flex justify="end" style={{ marginTop: 12 }}>
              <Pagination
                current={hist?.page || page}
                pageSize={hist?.page_size || pageSize}
                total={hist?.total || 0}
                showSizeChanger
                onChange={(p, ps) => { setPage(p); setPageSize(ps); refetchHist() }}
              />
            </Flex>
          </>
        )}
      </Drawer>

      <Drawer title="批量分析" width={720} open={batchOpen} onClose={() => { cancelRef.current = true; setBatchOpen(false); /* 不清除 taskId/localStorage，便于后续恢复 */ }} destroyOnClose>
        <Space direction="vertical" style={{ width: '100%' }} size={12}>
          {batchStatus !== 'idle' && (
            <>
              <Typography.Paragraph type={batchStatus==='error'?'danger': batchStatus==='success'?'success': undefined}>
                状态：{batchStatus === 'running' ? '分析中…' : batchStatus === 'success' ? '已完成' : batchStatus === 'error' ? '出错' : batchStatus === 'timeout' ? '超时' : '已停止'}
              </Typography.Paragraph>
              <Progress percent={percent} status={percent>=100? 'success' : 'active'} />
              <Space>
                <Button onClick={() => { cancelRef.current = true; setBatchStatus('stopped'); message.info('已停止轮询') }}>停止轮询</Button>
                <Button danger onClick={() => { setBatchItems([]); setPercent(0); setTaskId(null); setBatchStatus('idle'); try { localStorage.removeItem('watch_batch_tid') } catch {}; message.success('已清空任务状态') }}>清空任务</Button>
              </Space>
            </>
          )}

          {batchItems && batchItems.length > 0 ? (
            <Table
              size="small"
              rowKey={(r) => r.股票代码}
              dataSource={batchItems}
              columns={[
                { title: '股票代码', dataIndex: '股票代码', width: 120 },
                { title: '股票名称', dataIndex: '股票名称', width: 140 },
                { title: '评分', dataIndex: '评分', width: 80 },
                { title: '建议动作', dataIndex: '建议动作', width: 120, render: (v: any) => <ActionBadge action={v} /> },
                { title: '理由简述', dataIndex: '理由简述' },
                { title: '错误', dataIndex: '错误', width: 160 },
              ] as any}
              pagination={false}
            />
          ) : (
            <Typography.Text type="secondary">暂无结果</Typography.Text>
          )}
        </Space>
      </Drawer>
      <Modal title={`${quoteSymbol || ''} 实时行情`} width={quoteSize.w} open={openQuote} onCancel={() => setOpenQuote(false)} destroyOnHidden footer={null}>
        {quoteSymbol ? (
          <div style={{ position: 'relative', height: quoteSize.h, border: '1px solid #eee', display: 'flex', flexDirection: 'column' }}>
             <div style={{ padding: '6px 8px', borderBottom: '1px solid #f0f0f0' }}>
               <Tabs
                 size="small"
                 activeKey={String(chartIdx)}
                 onChange={(k) => setChartIdx(Number(k))}
                 items={buildQuoteSources(quoteSymbol).map((src, i) => ({ key: String(i), label: src.name }))}
               />
             </div>
             <div style={{ flex: 1 }}>
               {(() => {
                 const s = buildQuoteSources(quoteSymbol)
                 const cur = s[chartIdx] || s[0]
                 const url = cur ? cur.url : ''
                 return (
                   <iframe
                     src={url}
                     style={{ width: '100%', height: '100%', border: '0' }}
                     title="行情"
                   />
                 )
               })()}
             </div>
            {isResizing && <div style={{ position: 'absolute', inset: 0, zIndex: 20, cursor: 'nwse-resize' }} />}
            {/* 底部右下角拖拽手柄：可调整弹窗宽高 */}
            <div
              onMouseDown={handleResizeMouseDown}
              title="拖拽调整大小"
              style={{ position: 'absolute', right: 2, bottom: 2, width: 16, height: 16, cursor: 'nwse-resize', background: '#d9d9d9', borderRadius: 2, zIndex: 30 }}
            />
           </div>
         ) : (
           <Typography.Text type="secondary">请选择一只股票查看</Typography.Text>
         )}
      </Modal>
    </div>
  )
}