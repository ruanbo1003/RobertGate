import { Loader2 } from 'lucide-react'
import type { ChapterMeta, ChapterState } from '../../types/investReports'

const CHAPTER_DOT: Record<ChapterState, string> = {
  pending: 'bg-slate-300',
  researching: 'bg-warning',
  done: 'bg-success',
  failed: 'bg-error',
  stale: 'bg-warning',
  updating: 'bg-warning',
}

interface ChapterTreeProps {
  chapters: ChapterMeta[]
  selectedId: number | null
  onSelect: (id: number) => void
}

const STATE_SUB: Record<ChapterMeta['state'], string> = {
  pending: '待研究',
  researching: '研究中…',
  done: '已完成',
  failed: '失败',
  stale: '已过期',
  updating: '更新中…',
}

export default function ChapterTree({ chapters, selectedId, onSelect }: ChapterTreeProps) {
  const done = chapters.filter((c) => c.state === 'done').length
  return (
    <aside className="w-[252px] shrink-0 h-full flex flex-col bg-card border-r border-border px-3 py-4 overflow-y-auto">
      <p className="px-2 pb-2 text-xs font-semibold text-text-muted">章节 · {chapters.length}</p>
      <nav className="flex flex-col gap-1" aria-label="章节导航">
        {chapters.map((c) => {
          const active = c.id === selectedId
          const busy = c.state === 'researching' || c.state === 'updating'
          return (
            <button
              key={c.id}
              onClick={() => onSelect(c.id)}
              aria-current={active ? 'true' : undefined}
              className={`flex items-center gap-2 px-2.5 py-2 rounded-[var(--radius-sm)] text-left transition-colors cursor-pointer focus:outline-none focus:ring-2 focus:ring-primary/30 ${
                active ? 'bg-primary-light border border-primary' : 'hover:bg-page-alt border border-transparent'
              }`}
            >
              <span className={`w-[7px] h-[7px] rounded-full shrink-0 ${CHAPTER_DOT[c.state]}`} />
              <span className="flex-1 min-w-0">
                <span className={`block text-[13px] truncate ${active ? 'font-bold' : 'font-semibold'} text-text-primary`}>
                  {c.title}
                </span>
                <span className={`flex items-center gap-1 text-[10px] ${busy ? 'text-warning' : 'text-text-muted'}`}>
                  {busy && <Loader2 size={9} className="animate-spin" />}
                  {STATE_SUB[c.state]}
                  {c.tbd_count > 0 && c.state === 'done' && ` · 待补充 ${c.tbd_count}`}
                </span>
              </span>
            </button>
          )
        })}
      </nav>
      <div className="mt-auto pt-4">
        <div className="px-2.5 py-2.5 rounded-[var(--radius-sm)] bg-page-alt">
          <div className="flex justify-between text-[11px]">
            <span className="text-text-muted">整体进度</span>
            <span className="font-bold text-text-primary">
              {done}/{chapters.length}
            </span>
          </div>
          <div className="mt-1.5 h-1.5 rounded-full bg-border overflow-hidden">
            <div
              className="h-full rounded-full bg-primary transition-all duration-300"
              style={{ width: `${chapters.length ? (done / chapters.length) * 100 : 0}%` }}
            />
          </div>
        </div>
      </div>
    </aside>
  )
}
