import { Clapperboard, Trash2 } from 'lucide-react'
import type { ProjectStatus, ProjectSummary } from '../../types/aiVideos'
import { resolveAssetUrl } from '../../services/aiVideos'

const STATUS_META: Record<ProjectStatus, { label: string; dot: string; text: string }> = {
  draft: { label: '草稿', dot: 'bg-text-muted', text: 'text-text-muted' },
  generating: { label: '生成中', dot: 'bg-primary animate-pulse', text: 'text-primary' },
  partial_failed: { label: '部分失败', dot: 'bg-error', text: 'text-error' },
  completed: { label: '已完成', dot: 'bg-success', text: 'text-success' },
}

interface ProjectCardProps {
  project: ProjectSummary
  onOpen: () => void
  onDelete: () => void
}

export default function ProjectCard({ project, onOpen, onDelete }: ProjectCardProps) {
  const meta = STATUS_META[project.status]
  const statusText =
    project.status === 'generating'
      ? `${meta.label} ${project.progress.video}/${project.shot_count}`
      : meta.label

  return (
    <div
      onClick={onOpen}
      role="button"
      tabIndex={0}
      onKeyDown={(e) => e.key === 'Enter' && onOpen()}
      className="group flex flex-col bg-card rounded-[var(--radius-lg)] border border-border hover:border-primary/30 shadow-sm hover:shadow-md transition-all duration-150 hover:-translate-y-0.5 cursor-pointer overflow-hidden focus:outline-none focus:ring-2 focus:ring-primary/30"
    >
      <div className="relative w-full aspect-[9/16] bg-page-alt overflow-hidden">
        {project.cover_url ? (
          <img
            src={resolveAssetUrl(project.cover_url)}
            alt={`${project.title} 封面`}
            className="w-full h-full object-cover"
            loading="lazy"
          />
        ) : (
          <div className="w-full h-full flex items-center justify-center">
            <Clapperboard size={32} className="text-text-muted/40" />
          </div>
        )}
        <span className="absolute top-3 left-3 inline-flex items-center gap-1.5 px-2.5 py-1 bg-card rounded-full shadow-sm">
          <span className={`w-1.5 h-1.5 rounded-full ${meta.dot}`} />
          <span className={`text-[11px] font-semibold ${meta.text}`}>{statusText}</span>
        </span>
        <button
          onClick={(e) => {
            e.stopPropagation()
            onDelete()
          }}
          aria-label={`删除 ${project.title}`}
          className="absolute top-3 right-3 w-8 h-8 flex items-center justify-center bg-card rounded-full shadow-sm text-text-muted hover:text-error opacity-0 group-hover:opacity-100 focus:opacity-100 transition-all cursor-pointer"
        >
          <Trash2 size={14} />
        </button>
      </div>
      <div className="flex flex-col gap-1 p-4">
        <h3 className="text-sm font-bold text-text-primary group-hover:text-primary transition-colors truncate">
          {project.title}
        </h3>
        <p className="text-xs text-text-muted">
          {project.duration_estimate}s · {project.shot_count} 镜 ·{' '}
          {new Date(project.updated_at).toLocaleDateString('zh-CN', {
            month: '2-digit',
            day: '2-digit',
          })}
        </p>
      </div>
    </div>
  )
}
