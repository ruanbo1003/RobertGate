import { Check, Circle } from 'lucide-react'
import type { T2IBusinessStatus } from '../../types/t2i'

interface Props {
  status: T2IBusinessStatus
}

export default function StatusBadge({ status }: Props) {
  if (status === 'done') {
    return (
      <span className="inline-flex items-center gap-1 h-6 px-2 rounded-full bg-success-light text-success text-xs font-semibold">
        <Check size={12} />
        完成
      </span>
    )
  }
  return (
    <span className="inline-flex items-center gap-1 h-6 px-2 rounded-full border border-border bg-page text-text-muted text-xs font-semibold">
      <Circle size={10} />
      未完成
    </span>
  )
}
