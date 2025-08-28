import { Layout, theme, Menu, Tooltip, Button, Drawer } from 'antd'
import { Link, Outlet, Route, Routes, useLocation, useNavigate } from 'react-router-dom'
import WatchlistPage from '@/features/watchlist/pages/WatchlistPage'
import RecommendPage from '@/features/recommend/pages/RecommendPage'
import KeywordRecommendPage from '@/features/recommend/pages/KeywordRecommendPage'
import TasksPage from '@/features/tasks/pages/TasksPage'
import AdvancedSettingsPage from '@/features/settings/pages/AdvancedSettingsPage'
import { SettingOutlined, MenuOutlined } from '@ant-design/icons'
import { useEffect, useMemo, useState } from 'react'
import './styles.css'

const { Header, Content, Footer } = Layout

export default function App() {
  const { token } = theme.useToken()
  const { pathname } = useLocation()
  const navigate = useNavigate()
  const [vw, setVw] = useState<number>(typeof window !== 'undefined' ? window.innerWidth : 1200)
  const isMobile = vw < 768
  useEffect(() => {
    const onResize = () => setVw(typeof window !== 'undefined' ? window.innerWidth : 1200)
    window.addEventListener('resize', onResize)
    return () => window.removeEventListener('resize', onResize)
  }, [])

  const items = useMemo(() => ([
    { key: '/', label: <Link to="/">自选股</Link> },
    { key: '/ai', label: <Link to="/ai">AI 推荐</Link> },
    { key: '/keyword', label: <Link to="/keyword">关键词推荐</Link> },
    { key: '/tasks', label: <Link to="/tasks">任务管理</Link> },
  ]), [])
  const itemsMobile = useMemo(() => ([
    { key: '/', label: '自选股' },
    { key: '/ai', label: 'AI 推荐' },
    { key: '/keyword', label: '关键词推荐' },
    { key: '/tasks', label: '任务管理' },
  ]), [])
  const [mobileOpen, setMobileOpen] = useState(false)

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
      <Header style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
        {/* 左侧菜单按钮（移动端显示） */}
        {isMobile && (
          <Button type="text" aria-label="打开菜单" icon={<MenuOutlined style={{ color: '#fff' }} />} onClick={() => setMobileOpen(true)} />
        )}
        <span style={{ color: 'white', fontWeight: 600, marginRight: 12 }}>股票助手</span>
        {/* 桌面端水平菜单 */}
        <div style={{ flex: 1, minWidth: 0 }}>
          <Menu
            theme="dark"
            mode="horizontal"
            selectedKeys={[pathname]}
            items={items}
            style={{ display: isMobile ? 'none' : 'block', minWidth: 0, overflowX: 'auto' }}
          />
        </div>
        <Tooltip title="高级参数（Ctrl+,）" placement="bottom">
          <Link to="/settings" style={{ color: 'white', fontSize: 18 }} aria-label="高级参数">
            <SettingOutlined />
          </Link>
        </Tooltip>
        {/* 移动端抽屉菜单 */}
        <Drawer
          title="菜单"
          placement="left"
          open={mobileOpen}
          onClose={() => setMobileOpen(false)}
          width={Math.min(280, Math.max(220, Math.round(vw * 0.8)))}
        >
          <Menu
            mode="inline"
            selectedKeys={[pathname]}
            items={itemsMobile}
            onClick={({ key }) => { setMobileOpen(false); if (key && typeof key === 'string') navigate(key) }}
          />
        </Drawer>
      </Header>

      <Content style={{ padding: 16, background: token.colorBgContainer }}>
        <Routes>
          <Route path="/" element={<WatchlistPage />} />
          <Route path="/ai" element={<RecommendPage />} />
          <Route path="/keyword" element={<KeywordRecommendPage />} />
          <Route path="/tasks" element={<TasksPage />} />
          <Route path="/settings" element={<AdvancedSettingsPage />} />
        </Routes>
        <Outlet />
      </Content>
      <Footer style={{ textAlign: 'center' }}>Made with ❤️ by Dear Master & 小跟班</Footer>
    </Layout>
  )
}