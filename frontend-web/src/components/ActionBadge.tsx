import { Tag } from 'antd'

const COLORS: Record<string, string> = { buy: 'green', hold: 'gold', sell: 'red' }

export default function ActionBadge({ action }: { action?: string | null }) {
  const a = action || 'N/A'
  const color = COLORS[a] || 'default'
  return <Tag color={color} style={{ textTransform: 'uppercase', minWidth: 52, textAlign: 'center' }}>{a}</Tag>
}