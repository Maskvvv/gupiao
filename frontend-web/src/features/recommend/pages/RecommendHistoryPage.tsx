import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { App, Button, Card, DatePicker, Flex, Pagination, Space, Table, Tag, Popconfirm, Segmented, Typography } from 'antd'
import dayjs from 'dayjs'
import { deleteRecommend, getRecommendDetails, getRecommendHistory } from '@/api/recommend'
import { useState } from 'react'

export default function RecommendHistoryPage() {
  const qc = useQueryClient()
  const { message, modal } = App.useApp()
  const [page, setPage] = useState(1)
  const [pageSize, setPageSize] = useState(10)
  const [range, setRange] = useState<[dayjs.Dayjs, dayjs.Dayjs] | null>(null)
  const [rtype, setRtype] = useState<string | undefined>(undefined)

  const { data, isLoading } = useQuery({
    queryKey: ['rec-history', page, pageSize, range?.[0]?.format('YYYY-MM-DD'), range?.[1]?.format('YYYY-MM-DD'), rtype],
    queryFn: () => getRecommendHistory(page, pageSize, range?.[0]?.format('YYYY-MM-DD'), range?.[1]?.format('YYYY-MM-DD'), rtype),
  })

  const mDelete = useMutation({
    mutationFn: (id: number) => deleteRecommend(id),
    onSuccess: () => { message.success('已删除'); qc.invalidateQueries({ queryKey: ['rec-history'] }) },
    onError: (e: any) => message.error(e.message || '删除失败'),
  })

  const presets = [
    { label: '今日', value: [dayjs().startOf('day'), dayjs().endOf('day')] as [dayjs.Dayjs, dayjs.Dayjs] },
    { label: '最近7天', value: [dayjs().add(-6, 'day').startOf('day'), dayjs().endOf('day')] as [dayjs.Dayjs, dayjs.Dayjs] },
    { label: '最近30天', value: [dayjs().add(-29, 'day').startOf('day'), dayjs().endOf('day')] as [dayjs.Dayjs, dayjs.Dayjs] },
  ]

  const typeTag = (t?: string) => t === 'keyword' ? <Tag color="green">关键词</Tag>
    : t === 'market_wide' ? <Tag color="purple">全市场</Tag>
    : <Tag color="blue">手动/其他</Tag>

  return (
    <div className="container">
      <Card title="推荐历史">
        <Flex gap={8} wrap style={{ marginBottom: 12 }} align="center">
          <DatePicker.RangePicker value={range as any} onChange={(v)=>{ setRange(v as any); setPage(1) }} presets={presets as any} />
          <Segmented
            options={[
              { label: '全部', value: 'all' },
              { label: '关键词', value: 'keyword' },
              { label: '全市场', value: 'market_wide' },
              { label: '手动', value: 'manual' },
            ]}
            value={rtype || 'all'}
            onChange={(v)=>{ const nv = String(v); setRtype(nv === 'all' ? undefined : nv); setPage(1) }}
          />
        </Flex>

        <Table
          loading={isLoading}
          rowKey={(r)=>String(r.id)}
          dataSource={data?.records || []}
          columns={[
            { title: 'ID', dataIndex: 'id', width: 80 },
            { title: '时间', dataIndex: 'created_at', width: 180 },
            { title: '周期', dataIndex: 'period', width: 120 },
            { title: '类型', dataIndex: 'recommend_type', width: 120, render: (v: string)=> typeTag(v) },
            { title: '状态', dataIndex: 'status', width: 100, render: (_: any)=> <Tag color="success">已完成</Tag> },
            { title: '候选/入选', key: 'cnt', width: 140, render: (_:any, r:any)=> `${r.total_candidates}/${r.top_n}` },
            { title: '摘要', dataIndex: 'summary' },
            {
              title: '操作', key: 'ops', width: 220, render: (_:any, r:any)=> (
                <Space>
                  <Button size="small" onClick={async ()=>{
                    try {
                      const d = await getRecommendDetails(r.id)
                      modal.info({ title: `记录 ${d.id} 详情`, width: 720, content: (
                        <div style={{ maxHeight: 480, overflow: 'auto' }}>
                          {d.items?.map((it:any)=> (
                            <div key={it.股票代码} style={{ padding: '6px 0', borderBottom: '1px solid #f0f0f0' }}>
                              <div style={{ fontWeight: 600 }}>{it.股票名称}（{it.股票代码}）</div>
                              <div>评分：{it.评分} 建议：<Tag color={it.建议动作==='buy'?'green':it.建议动作==='sell'?'red':'gold'}>{it.建议动作}</Tag></div>
                              <div>理由：{it.理由简述}</div>
                              {it.AI详细分析 ? (
                                <Typography.Paragraph type="secondary" ellipsis={{ rows: 8, expandable: true, symbol: '展开AI分析' }} style={{ marginBottom: 0 }}>
                                  <b>AI详细分析：</b>{it.AI详细分析}
                                </Typography.Paragraph>
                              ) : null}
                            </div>
                          ))}
                        </div>
                      ) })
                    } catch (e: any) {
                      message.error(e?.message || '获取详情失败')
                    }
                  }}>查看</Button>
                  <Popconfirm title="确认删除该记录？" okText="删除" cancelText="取消" onConfirm={()=> mDelete.mutate(r.id)}>
                    <Button size="small" danger loading={mDelete.isPending}>删除</Button>
                  </Popconfirm>
                </Space>
              )
            },
          ] as any}
          pagination={false}
        />

        <Flex justify="end" style={{ marginTop: 12 }}>
          <Pagination current={page} pageSize={pageSize} total={data?.total || 0} onChange={(p, ps)=>{ setPage(p); setPageSize(ps) }} />
        </Flex>
      </Card>
    </div>
  )
}