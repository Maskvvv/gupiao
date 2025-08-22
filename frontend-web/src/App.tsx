import { Layout, theme, Menu } from 'antd'
import { Link, Outlet, Route, Routes, useLocation } from 'react-router-dom'
import WatchlistPage from '@/features/watchlist/pages/WatchlistPage'
import './styles.css'

const { Header, Content, Footer } = Layout

export default function App() {
  const { token } = theme.useToken()
  const { pathname } = useLocation()
  const items = [
    { key: '/', label: <Link to="/">自选股</Link> },
    { key: '/ai', label: <Link to="/ai">AI 推荐</Link> },
    { key: '/history', label: <Link to="/history">推荐历史</Link> },
  ]
  return (
    <Layout style={{ minHeight: '100vh' }}>
      <Header style={{ display: 'flex', alignItems: 'center' }}>
        <div style={{ color: 'white', fontWeight: 600, marginRight: 24 }}>股票助手</div>
        <Menu theme="dark" mode="horizontal" selectedKeys={[pathname]} items={items} style={{ flex: 1 }} />
      </Header>
      <Content style={{ padding: 16, background: token.colorBgContainer }}>
        <Routes>
          <Route path="/" element={<WatchlistPage />} />
          <Route path="/ai" element={<div style={{ padding: 24 }}>即将到来～</div>} />
          <Route path="/history" element={<div style={{ padding: 24 }}>即将到来～</div>} />
        </Routes>
        <Outlet />
      </Content>
      <Footer style={{ textAlign: 'center' }}>Made with ❤️ by Dear Master & 小跟班</Footer>
    </Layout>
  )
}