import { Link } from 'react-router-dom'
import { motion } from 'framer-motion'
import { AlertCircle, Loader2 } from 'lucide-react'
import type { T2ITaskSummary, T2ITemplateCode } from '../../types/t2i'
import { resolveImageUrl } from '../../services/t2i'
import StatusBadge from './StatusBadge'

interface Props {
  task: T2ITaskSummary
  templateCode: T2ITemplateCode
}

export default function T2ITaskCard({ task, templateCode }: Props) {
  const detailPath = `/ai-tools/text-to-image/${templateCode}/${task.id}`
  const thumbs = task.thumbnails ?? []
  const hasGenerating = task.status === 'generating'

  return (
    <motion.div
      whileHover={{ y: -2 }}
      transition={{ duration: 0.15 }}
      className="relative bg-card border border-border rounded-[var(--radius-lg)] overflow-hidden shadow-sm hover:shadow-[0_8px_32px_rgba(0,0,0,0.08)] transition-shadow"
    >
      <Link to={detailPath} className="block">
        {/* 缩略图区 */}
        <div
          className={`relative aspect-[4/3] bg-page grid gap-0.5 ${
            thumbs.length <= 1 ? 'grid-cols-1' : 'grid-cols-2'
          }`}
        >
          {hasGenerating && thumbs.length === 0 ? (
            <div className="flex flex-col items-center justify-center gap-2 text-text-muted">
              <Loader2 size={20} className="animate-spin" />
              <span className="text-xs">生成中…</span>
            </div>
          ) : thumbs.length === 0 ? (
            <div className="flex items-center justify-center text-text-muted text-xs">
              暂无图片
            </div>
          ) : (
            thumbs.slice(0, 4).map((url, idx) => (
              <div key={idx} className="relative overflow-hidden bg-page">
                <img
                  src={resolveImageUrl(url)}
                  alt=""
                  loading="lazy"
                  className="w-full h-full object-cover"
                />
                {idx === 3 && task.images_total > 4 && (
                  <div className="absolute inset-0 bg-black/50 flex items-center justify-center text-white text-xs font-semibold">
                    +{task.images_total - 4}
                  </div>
                )}
              </div>
            ))
          )}

          {/* 右上角：生成中 spinner */}
          {hasGenerating && thumbs.length > 0 && (
            <div className="absolute top-2 right-2 w-8 h-8 rounded-full bg-card/95 border border-border flex items-center justify-center">
              <Loader2 size={14} className="animate-spin text-primary" />
            </div>
          )}
        </div>

        {/* 元信息区 */}
        <div className="p-4 flex flex-col gap-2">
          <div className="flex items-start justify-between gap-2">
            <div
              className="text-sm font-semibold text-text-primary truncate flex-1"
              title={task.summary}
            >
              {task.summary}
            </div>
            <StatusBadge status={task.business_status} />
          </div>

          <div className="flex items-center justify-between text-xs text-text-muted">
            <span>
              可用{' '}
              <span className="text-text-primary font-semibold">{task.images_available}</span>
              <span className="mx-0.5">/</span>
              {task.images_total}
            </span>
            {task.last_failed && !hasGenerating && (
              <span className="inline-flex items-center gap-1 text-error">
                <AlertCircle size={12} />
                上次生成失败
              </span>
            )}
          </div>
        </div>
      </Link>
    </motion.div>
  )
}
