import React, { useState } from 'react';
import { Card, Alert } from 'antd';
import { ThunderboltOutlined } from '@ant-design/icons';
import StreamingRecommendForm from '../StreamingRecommendForm';

const RecommendPage: React.FC = () => {
  return (
    <div className="container">
      <Card 
        title={
          <span>
            <ThunderboltOutlined style={{ marginRight: 8 }} />
            AI 流式推荐
          </span>
        }
      >
        <Alert
          message="全新的流式推荐体验"
          description="使用最新的流式AI技术，实时显示分析过程，支持任务管理和进度追踪。"
          type="info"
          showIcon
          style={{ marginBottom: 16 }}
        />
        <StreamingRecommendForm />
      </Card>
    </div>
  );
};

export default RecommendPage;
