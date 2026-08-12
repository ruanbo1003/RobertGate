import { useState } from 'react'
import { motion } from 'framer-motion'
import { AlertCircle, Eye, Loader2, Star, Trash2 } from 'lucide-react'
import type { T2IImage } from '../../types/t2i'
import { resolveImageUrl } from '../../services/t2i'

interface Props {
  image: T2IImage
  isAdmin: boolean
  onView: () => void
  onToggleAvailable: () => Promise<void> | void
  onDelete: () => Promise<void> | void
}

export default function T2IImageTile({ image, isAdmin, onView, onToggleAvailable, onDelete }: Props) {
  const [busy, setBusy] = useState(false)

  if (image.status === 'generating') {
    return (
      <div className="aspect-square rounded-[var(--radius-md)] border border-dashed border-border bg-page flex flex-col items-center justify-center gap-2 text-text-muted">
        <Loader2 size={20} className="animate-spin" />
        <span className="text-xs">生成中…</span>
      </div>
    )
  }

  if (image.status === 'failed') {
    return (
      <div className="aspect-square rounded-[var(--radius-md)] border border-dashed border-error/40 bg-error-light/40 flex flex-col items-center justify-center gap-2 text-error">
        <AlertCircle size={20} />
        <span className="text-xs">生成失败</span>
      </div>
    )
  }

  const cannotDelete = image.available
  const wrap = async (fn: () => Promise<void> | void) => {
    if (busy) return
    setBusy(true)
    try {
      await fn()
    } finally {
      setBusy(false)
    }
  }

  return (
    <div className="group relative aspect-square rounded-[var(--radius-md)] overflow-hidden bg-page border border-border">
      <img
        src={resolveImageUrl(image.url)}
        alt=""
        loading="lazy"
        className="w-full h-full object-cover"
      />

      {/* 可用角标 */}
      {image.available && (
        <div className="absolute top-2 right-2 inline-flex items-center gap-1 h-6 px-2 rounded-full bg-success text-white text-xs font-semibold shadow-sm">
          <Star size={10} fill="currentColor" />
          可用
        </div>
      )}

      {/* 悬停操作栏 */}
      <motion.div
        initial={false}
        className="absolute inset-x-0 bottom-0 p-2 opacity-0 group-hover:opacity-100 transition-opacity"
      >
        <div className="mx-auto inline-flex items-center gap-0.5 bg-black/70 backdrop-blur rounded-full px-1.5 py-1">
          <button
            onClick={(e) => { e.preventDefault(); e.stopPropagation(); onView() }}
            className="w-8 h-8 flex items-center justify-center text-white/80 hover:text-white rounded-full hover:bg-white/10 transition-colors cursor-pointer"
            title="放大查看"
            aria-label="放大"
          >
            <Eye size={16} />
          </button>

          {isAdmin && (
            <button
              onClick={(e) => { e.preventDefault(); e.stopPropagation(); wrap(onToggleAvailable) }}
              disabled={busy}
              className={`w-8 h-8 flex items-center justify-center rounded-full transition-colors cursor-pointer disabled:opacity-50 ${
                image.available
                  ? 'text-yellow-300 hover:bg-white/10'
                  : 'text-white/80 hover:text-white hover:bg-white/10'
              }`}
              title={image.available ? '取消可用' : '标记可用'}
              aria-label="标记可用"
            >
              <Star size={16} fill={image.available ? 'currentColor' : 'none'} />
            </button>
          )}

          {isAdmin && (
            <button
              onClick={(e) => { e.preventDefault(); e.stopPropagation(); if (!cannotDelete) wrap(onDelete) }}
              disabled={busy || cannotDelete}
              className={`w-8 h-8 flex items-center justify-center rounded-full transition-colors ${
                cannotDelete
                  ? 'text-white/30 cursor-not-allowed'
                  : 'text-white/80 hover:text-white hover:bg-white/10 cursor-pointer'
              }`}
              title={cannotDelete ? '取消可用后才能删除' : '删除'}
              aria-label="删除"
            >
              <Trash2 size={16} />
            </button>
          )}
        </div>
      </motion.div>
    </div>
  )
}
