import { Loader2 } from 'lucide-react'
import type { ChapterState, ParseState, ProjectStatus, ReportType } from '../../types/investReports'

export function TypeBadge({ type }: { type: ReportType }) {
  const advice = type === 'advice'
  return (
    <span
      className={`px-2 py-0.5 rounded text-[10px] font-semibold ${
        advice ? 'bg-primary-light text-primary' : 'bg-accent-light text-accent'
      }`}
    >
      {advice ? '投资建议书' : '尽调报告'}
    </span>
  )
}

const CHAPTER_STATE: Record<ChapterState, { label: string; cls: string; spin?: boolean }> = {
  pending: { label: '待研究', cls: 'bg-page-alt text-text-muted' },
  researching: { label: '研究中', cls: 'bg-warning-light text-warning', spin: true },
  done: { label: '已完成', cls: 'bg-success-light text-success' },
  failed: { label: '失败', cls: 'bg-error-light text-error' },
  stale: { label: '已过期', cls: 'bg-warning-light text-warning' },
  updating: { label: '更新中', cls: 'bg-warning-light text-warning', spin: true },
}

export function ChapterStateChip({ state }: { state: ChapterState }) {
  const s = CHAPTER_STATE[state]
  return (
    <span className={`inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-[10px] font-semibold ${s.cls}`}>
      {s.spin && <Loader2 size={10} className="animate-spin" />}
      {s.label}
    </span>
  )
}

const PROJECT_STATE: Record<ProjectStatus, { label: string; cls: string }> = {
  draft: { label: '草稿', cls: 'bg-page-alt text-text-muted' },
  researching: { label: '研究中', cls: 'bg-warning-light text-warning' },
  partial_failed: { label: '有失败章节', cls: 'bg-error-light text-error' },
  completed: { label: '已完成', cls: 'bg-success-light text-success' },
}

export function ProjectStateChip({ status }: { status: ProjectStatus }) {
  const s = PROJECT_STATE[status]
  return <span className={`px-2 py-0.5 rounded-full text-[10px] font-semibold ${s.cls}`}>{s.label}</span>
}

export function ParseChip({ state, quality }: { state: ParseState; quality?: 'ok' | 'low' }) {
  if (state === 'ready' && quality === 'low') {
    return <span className="px-2 py-0.5 rounded-full text-[10px] font-semibold bg-warning-light text-warning">解析质量低</span>
  }
  const map: Record<ParseState, { label: string; cls: string }> = {
    pending: { label: '待解析', cls: 'bg-page-alt text-text-muted' },
    parsing: { label: '解析中…', cls: 'bg-warning-light text-warning' },
    ready: { label: '已解析', cls: 'bg-success-light text-success' },
    failed: { label: '解析失败', cls: 'bg-error-light text-error' },
  }
  const s = map[state]
  return <span className={`px-2 py-0.5 rounded-full text-[10px] font-semibold ${s.cls}`}>{s.label}</span>
}
