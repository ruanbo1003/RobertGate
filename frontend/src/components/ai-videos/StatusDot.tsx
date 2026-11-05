import type { AssetState } from '../../types/aiVideos'

/** 产物五态（pending/running/success/failed + stale 覆盖）的视觉映射，全站统一。 */
function assetStateMeta(state: AssetState, stale: boolean) {
  if (stale) return { label: '过期', dot: 'bg-warning', text: 'text-warning', bg: 'bg-warning-light' }
  switch (state) {
    case 'success':
      return { label: '成功', dot: 'bg-success', text: 'text-success', bg: 'bg-success-light' }
    case 'failed':
      return { label: '失败', dot: 'bg-error', text: 'text-error', bg: 'bg-error-light' }
    case 'running':
      return { label: '生成中', dot: 'bg-primary animate-pulse', text: 'text-primary', bg: 'bg-primary-light' }
    default:
      return { label: '待生成', dot: 'bg-border', text: 'text-text-muted', bg: 'bg-page-alt' }
  }
}

interface StatusDotProps {
  state: AssetState
  stale?: boolean
}

export default function StatusDot({ state, stale = false }: StatusDotProps) {
  const meta = assetStateMeta(state, stale)
  return (
    <span
      className={`inline-block w-1.5 h-1.5 rounded-full shrink-0 ${meta.dot}`}
      role="img"
      aria-label={meta.label}
    />
  )
}

interface StatusChipProps {
  state: AssetState
  stale?: boolean
}

/** 带文字的状态 chip（颜色 + 文字双重指示，不只靠颜色传达状态）。 */
export function StatusChip({ state, stale = false }: StatusChipProps) {
  const meta = assetStateMeta(state, stale)
  return (
    <span className={`inline-flex items-center gap-1.5 px-2 py-0.5 rounded-full ${meta.bg}`}>
      <span className={`w-1.5 h-1.5 rounded-full ${meta.dot}`} />
      <span className={`text-[10px] font-semibold ${meta.text}`}>{meta.label}</span>
    </span>
  )
}
