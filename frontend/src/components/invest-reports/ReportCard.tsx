import type { ProjectSummary } from '../../types/investReports'
import { ProjectStateChip, TypeBadge } from './badges'

function footNote(p: ProjectSummary): { text: string; cls: string } {
  if (p.status === 'partial_failed') return { text: '可单章重试', cls: 'text-error' }
  if (p.status === 'completed') return { text: p.tbd_count > 0 ? `待补充 ${p.tbd_count} 处` : '可导出', cls: p.tbd_count > 0 ? 'text-warning' : 'text-success' }
  if (p.status === 'researching') return { text: p.tbd_count > 0 ? `待补充 ${p.tbd_count} 处` : '生成中', cls: 'text-warning' }
  return { text: '待上传资料', cls: 'text-text-muted' }
}

export default function ReportCard({ project, onOpen }: { project: ProjectSummary; onOpen: () => void }) {
  const note = footNote(project)
  const pct = project.chapters_total ? (project.chapters_done / project.chapters_total) * 100 : 0
  return (
    <button
      onClick={onOpen}
      className="w-full text-left bg-card border border-border rounded-2xl p-4.5 shadow-sm hover:shadow-[0_8px_32px_rgba(0,0,0,0.08)] hover:border-primary/40 transition-all duration-200 cursor-pointer focus:outline-none focus:ring-2 focus:ring-primary/30"
    >
      <div className="flex items-center justify-between gap-2">
        <h3 className="text-sm font-bold text-text-primary truncate">{project.title}</h3>
        <ProjectStateChip status={project.status} />
      </div>
      <div className="mt-2">
        <TypeBadge type={project.type} />
      </div>
      <div className="mt-3">
        <div className="flex justify-between text-[11px]">
          <span className="text-text-muted">章节进度</span>
          <span className="font-bold text-text-primary">
            {project.chapters_done}/{project.chapters_total}
          </span>
        </div>
        <div className="mt-1 h-1.5 rounded-full bg-page-alt overflow-hidden">
          <div
            className={`h-full rounded-full ${project.chapters_done === project.chapters_total ? 'bg-success' : 'bg-primary'}`}
            style={{ width: `${pct}%` }}
          />
        </div>
      </div>
      <div className="mt-3 flex items-center justify-between text-[11px]">
        <span className="text-text-muted">{new Date(project.updated_at).toLocaleString('zh-CN', { month: 'numeric', day: 'numeric', hour: '2-digit', minute: '2-digit' })} 更新</span>
        <span className={`font-semibold ${note.cls}`}>{note.text}</span>
      </div>
    </button>
  )
}
