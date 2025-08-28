import { useEffect, useRef, useState } from 'react'
import { App, Button, Card, Divider, Flex, Input, Space, Typography, Progress, Skeleton, InputNumber, Segmented, Tooltip, Tabs, Alert } from 'antd'
import { useMutation, useQueryClient } from '@tanstack/react-query'
import { addWatch } from '@/api/watchlist'
import ActionBadge from '@/components/ActionBadge'
import { startKeywordRecommend, getKeywordStatus, getKeywordResult, type KeywordStartPayload, type KeywordTaskStatus } from '@/api/recommend'
import StreamingKeywordForm from '../StreamingKeywordForm'
import { ThunderboltOutlined } from '@ant-design/icons'

export default function KeywordRecommendPage() {
  return (
    <div className="container">
      <Card 
        title={
          <span>
            <ThunderboltOutlined style={{ marginRight: 8 }} />
            关键词流式推荐
          </span>
        }
      >
        <Alert
          message="全新的流式关键词推荐"
          description="使用最新的流式AI技术，实时显示筛选和分析过程，支持任务管理和进度追踪。"
          type="info"
          showIcon
          style={{ marginBottom: 16 }}
        />
        <StreamingKeywordForm />
      </Card>
    </div>
  )
}