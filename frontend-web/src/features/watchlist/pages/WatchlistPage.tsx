import { useMemo, useState } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { listWatchlist, addWatch, removeWatch, analyzeOne, type WatchItem, listHistory } from '@/api/watchlist'
import { Button, Card, Flex, Input, message, Space, Table, Typography, Drawer, Pagination, Divider } from 'antd'
import ActionBadge from '@/components/ActionBadge'
import ReactECharts from 'echarts-for-react'

export default function WatchlistPage() {
  const qc = useQueryClient()
  const { data: items = [], isLoading } = useQuery({ queryKey: ['watchlist'], queryFn: listWatchlist })
  const [symbol, setSymbol] = useState('')
  const [openHist, setOpenHist] = useState(false)
  const [histSymbol, setHistSymbol] = useState<string | null>(null)
  const [page, setPage] = useState(1)
  const [pageSize, setPageSize] = useState(10)

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
    mutationFn: (s: string) => analyzeOne(s),
    onSuccess: () => { message.success('已触发分析'); qc.invalidateQueries({ queryKey: ['watchlist'] }) },
    onError: (e: any) => message.error(e.message || '分析失败'),
  })

  const columns = [
    { title: '股票代码', dataIndex: '股票代码', width: 120 },
    { title: '股票名称', dataIndex: '股票名称', width: 140 },
    { title: '综合评分', dataIndex: '综合评分', width: 100, render: (v: number | null) => v ?? '-' },
    { title: '操作建议', dataIndex: '操作建议', width: 120, render: (v: string | null) => <ActionBadge action={v} /> },
    { title: '理由摘要', dataIndex: '分析理由摘要' },
    { title: '最近分析时间', dataIndex: '最近分析时间', width: 180 },
    {
      title: '操作', key: 'ops', width: 220,
      render: (_: any, r: WatchItem) => (
        <Space>
          <Button size="small" onClick={() => mAnalyze.mutate(r.股票代码)} loading={mAnalyze.isPending}>重新分析</Button>
          <Button size="small" onClick={() => { setHistSymbol(r.股票代码); setOpenHist(true); refetchHist() }}>历史</Button>
          <Button size="small" danger onClick={() => mRemove.mutate(r.股票代码)} loading={mRemove.isPending}>移除</Button>
        </Space>
      )
    },
  ] as any

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
        </Flex>

        <Table
          size="small"
          rowKey={(r: WatchItem) => r.股票代码}
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
    </div>
  )
}