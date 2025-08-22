import { Layout, theme, Menu, Tooltip } from 'antd'
import { Link, Outlet, Route, Routes, useLocation, useNavigate } from 'react-router-dom'
import WatchlistPage from '@/features/watchlist/pages/WatchlistPage'
import RecommendPage from '@/features/recommend/pages/RecommendPage'
import RecommendHistoryPage from '@/features/recommend/pages/RecommendHistoryPage'
import KeywordRecommendPage from '@/features/recommend/pages/KeywordRecommendPage'
import AdvancedSettingsPage from '@/features/settings/pages/AdvancedSettingsPage'
import { SettingOutlined } from '@ant-design/icons'
import { useEffect } from 'react'
import './styles.css'

const { Header, Content, Footer } = Layout

export default function App() {
  const { token } = theme.useToken()
  const { pathname } = useLocation()
  const navigate = useNavigate()
  const items = [
    { key: '/', label: <Link to="/">自选股</Link> },
    { key: '/ai', label: <Link to="/ai">AI 推荐</Link> },
    { key: '/keyword', label: <Link to="/keyword">关键词推荐</Link> },
    { key: '/history', label: <Link to="/history">推荐历史</Link> },
  ]

  // 快捷键：Ctrl+, 打开设置页
  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      const isMac = navigator.platform.toLowerCase().includes('mac')
      const ctrlOrCmd = isMac ? e.metaKey : e.ctrlKey
      if (ctrlOrCmd && e.key === ',') {
        e.preventDefault()
        navigate('/settings')
      }
    }
    window.addEventListener('keydown', onKey)
    return () => window.removeEventListener('keydown', onKey)
  }, [navigate])

  return (
    <Layout style={{ minHeight: '100vh' }}>
      <Header style={{ display: 'flex', alignItems: 'center' }}>
        {/* 标题处不需要额外的块级容器，改为 span 简化结构 */}
        <span style={{ color: 'white', fontWeight: 600, marginRight: 24 }}>股票助手</span>
        <Menu theme="dark" mode="horizontal" selectedKeys={[pathname]} items={items} style={{ flex: 1 }} />
        <Tooltip title="高级参数（Ctrl+,）" placement="bottom">
          <Link to="/settings" style={{ color: 'white', fontSize: 18 }} aria-label="高级参数">
            <SettingOutlined />
          </Link>
        </Tooltip>
      </Header>
      <Content style={{ padding: 16, background: token.colorBgContainer }}>
        <Routes>
          <Route path="/" element={<WatchlistPage />} />
          <Route path="/ai" element={<RecommendPage />} />
          <Route path="/keyword" element={<KeywordRecommendPage />} />
          <Route path="/history" element={<RecommendHistoryPage />} />
          <Route path="/settings" element={<AdvancedSettingsPage />} />
        </Routes>
        <Outlet />
      </Content>
      <Footer style={{ textAlign: 'center' }}>Made with ❤️ by Dear Master & 小跟班</Footer>
    </Layout>
  )
}