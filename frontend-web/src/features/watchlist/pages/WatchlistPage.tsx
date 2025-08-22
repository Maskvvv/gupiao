import { useMemo, useState } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { listWatchlist, addWatch, removeWatch, analyzeOne, type WatchItem } from '@/api/watchlist'
import { Button, Card, Flex, Input, message, Space, Table, Typography, Drawer, Pagination } from 'antd'
import ActionBadge from '@/components/ActionBadge'
import { listHistory } from '@/api/watchlist'

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
    onSuccess: () => message.success('分析完成并已保存'),
    onError: (e: any) => message.error(e.message || '分析失败'),
  })

  const columns = useMemo(() => [
    { title: '股票代码', dataIndex: '股票代码', key: 'symbol' },
    { title: '股票名称', dataIndex: '股票名称', key: 'name', responsive: ['md'] as any },
    { title: '综合评分', dataIndex: '综合评分', key: 'score', width: 100 },
    { title: '操作建议', dataIndex: '操作建议', key: 'action', width: 120, render: (v: string) => <ActionBadge action={v} /> },
    { title: '理由摘要', dataIndex: '分析理由摘要', key: 'brief', className: 'hide-sm' },
    { title: '最近分析时间', dataIndex: '最近分析时间', key: 'time', width: 180, responsive: ['lg'] as any },
    {
      title: '操作', key: 'ops', width: 260,
      render: (_: any, r: WatchItem) => (
        <Space wrap>
          <Button size="small" onClick={() => mAnalyze.mutate(r.股票代码)} loading={mAnalyze.isPending}>分析</Button>
          <Button size="small" onClick={() => { setHistSymbol(r.股票代码); setOpenHist(true); refetchHist() }}>历史</Button>
          <Button size="small" danger onClick={() => mRemove.mutate(r.股票代码)} loading={mRemove.isPending}>移除</Button>
        </Space>
      )
    },
  ], [mAnalyze.isPending, mRemove.isPending])

  return (
    <div className="container">
      <Card title="自选股票" extra={
        <Flex gap={8}>
          <Input placeholder="输入股票代码，如 000001.SZ" value={symbol} onChange={e => setSymbol(e.target.value)} allowClear style={{ width: 220 }} />
          <Button type="primary" onClick={() => symbol && mAdd.mutate(symbol)} loading={mAdd.isPending}>加入自选</Button>
        </Flex>
      }>
        <Table
          rowKey={(r) => r.股票代码}
          dataSource={items}
          columns={columns as any}
          loading={isLoading}
          scroll={{ x: 800 }}
          pagination={false}
        />
        {items.length === 0 && !isLoading && (
          <Typography.Paragraph type="secondary" style={{ marginTop: 12 }}>暂无数据，先添加一只股票试试吧～</Typography.Paragraph>
        )}
      </Card>

      <Drawer title={`${histSymbol || ''} 历史分析`} width={720} open={openHist} onClose={() => setOpenHist(false)} destroyOnClose>
        {fetchingHist ? '加载中...' : (
          <>
            <Table
              size="small"
              rowKey={(_, idx) => String(idx)}
              dataSource={hist?.items || []}
              columns={[
                { title: '时间', dataIndex: '时间', key: 't', width: 180 },
                { title: '评分', dataIndex: '综合评分', key: 's', width: 80 },
                { title: '建议', dataIndex: '操作建议', key: 'a', width: 120, render: (v) => <ActionBadge action={v} /> },
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