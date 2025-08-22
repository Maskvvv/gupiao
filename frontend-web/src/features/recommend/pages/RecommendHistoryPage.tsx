import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { Button, Card, DatePicker, Flex, Modal, Pagination, Space, Table, Tag, message, Popconfirm } from 'antd'
import dayjs from 'dayjs'
import { deleteRecommend, getRecommendDetails, getRecommendHistory } from '@/api/recommend'
import { useState } from 'react'

export default function RecommendHistoryPage() {
  const qc = useQueryClient()
  const [page, setPage] = useState(1)
  const [pageSize, setPageSize] = useState(10)
  const [range, setRange] = useState<[dayjs.Dayjs, dayjs.Dayjs] | null>(null)

  const { data, isLoading } = useQuery({
    queryKey: ['rec-history', page, pageSize, range?.[0]?.format('YYYY-MM-DD'), range?.[1]?.format('YYYY-MM-DD')],
    queryFn: () => getRecommendHistory(page, pageSize, range?.[0]?.format('YYYY-MM-DD'), range?.[1]?.format('YYYY-MM-DD')),
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

  return (
    <div className="container">
      <Card title="推荐历史">
        <Flex gap={8} wrap style={{ marginBottom: 12 }}>
          <DatePicker.RangePicker value={range as any} onChange={(v)=>{ setRange(v as any); setPage(1) }} presets={presets as any} />
        </Flex>

        <Table
          loading={isLoading}
          rowKey={(r)=>String(r.id)}
          dataSource={data?.records || []}
          columns={[
            { title: 'ID', dataIndex: 'id', width: 80 },
            { title: '时间', dataIndex: 'created_at', width: 180 },
            { title: '周期', dataIndex: 'period', width: 120 },
            { title: '候选/入选', key: 'cnt', width: 140, render: (_:any, r:any)=> `${r.total_candidates}/${r.top_n}` },
            { title: '摘要', dataIndex: 'summary' },
            {
              title: '操作', key: 'ops', width: 220, render: (_:any, r:any)=> (
                <Space>
                  <Button size="small" onClick={async ()=>{
                    try {
                      const d = await getRecommendDetails(r.id)
                      Modal.info({ title: `记录 ${d.id} 详情`, width: 720, content: (
                        <div style={{ maxHeight: 480, overflow: 'auto' }}>
                          {d.items?.map((it:any)=> (
                            <div key={it.股票代码} style={{ padding: '6px 0', borderBottom: '1px solid #f0f0f0' }}>
                              <div style={{ fontWeight: 600 }}>{it.股票名称}（{it.股票代码}）</div>
                              <div>评分：{it.评分} 建议：<Tag color={it.建议动作==='buy'?'green':it.建议动作==='sell'?'red':'gold'}>{it.建议动作}</Tag></div>
                              <div>理由：{it.理由简述}</div>
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