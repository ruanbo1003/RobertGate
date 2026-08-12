import { useCallback, useEffect, useMemo, useRef, useState } from 'react'
import { Link, useNavigate, useParams } from 'react-router-dom'
import { AnimatePresence, motion } from 'framer-motion'
import { ArrowLeft, Loader2, RefreshCw } from 'lucide-react'
import { deleteImage, getTask, patchImage, retryTask } from '../../services/t2i'
import { useAuth } from '../../store/AuthContext'
import type { T2IImage, T2ITaskDetail, T2ITemplateCode } from '../../types/t2i'
import StatusBadge from '../../components/t2i/StatusBadge'
import T2IImageTile from '../../components/t2i/T2IImageTile'
import T2IImageLightbox from '../../components/t2i/T2IImageLightbox'

export default function T2ITaskDetailPage() {
  const { templateCode, taskId } = useParams<{ templateCode: T2ITemplateCode; taskId: string }>()
  const navigate = useNavigate()
  const { user } = useAuth()
  const isAdmin = user?.role === 'admin'

  const [detail, setDetail] = useState<T2ITaskDetail | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [retrying, setRetrying] = useState(false)
  const [lightboxIndex, setLightboxIndex] = useState<number | null>(null)

  const load = useCallback(async () => {
    if (!taskId) return
    const res = await getTask(taskId)
    if (res.code === 0 && res.data) {
      setDetail(res.data)
      setError(null)
    } else {
      setError(res.message)
    }
    setLoading(false)
  }, [taskId])

  useEffect(() => {
    setLoading(true)
    load()
  }, [load])

  // 轮询：有 generating 图片时每 2s 刷新
  const pollRef = useRef<number | null>(null)
  useEffect(() => {
    if (!detail) return
    const hasGenerating = detail.images.some((i) => i.status === 'generating')
    if (!hasGenerating) return
    pollRef.current = window.setInterval(load, 2000)
    return () => {
      if (pollRef.current) window.clearInterval(pollRef.current)
    }
  }, [detail, load])

  const succeededImages = useMemo<T2IImage[]>(
    () => (detail?.images ?? []).filter((i) => i.status === 'succeeded' && i.url),
    [detail],
  )

  const openLightbox = (imgId: string) => {
    const idx = succeededImages.findIndex((i) => i.id === imgId)
    if (idx >= 0) setLightboxIndex(idx)
  }

  const handleRetry = async () => {
    if (!taskId || retrying) return
    setRetrying(true)
    const res = await retryTask(taskId)
    setRetrying(false)
    if (res.code === 0) {
      load()
    } else {
      alert(res.message)
    }
  }

  const handleToggleAvailable = async (img: T2IImage) => {
    const res = await patchImage(img.id, !img.available)
    if (res.code === 0) {
      load()
    } else {
      alert(res.message)
    }
  }

  const handleDelete = async (img: T2IImage) => {
    if (!confirm('确认删除这张图？此操作不可撤销。')) return
    const res = await deleteImage(img.id)
    if (res.code === 0) {
      load()
    } else {
      alert(res.message)
    }
  }

  if (loading && !detail) {
    return (
      <div className="max-w-6xl mx-auto">
        <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
          {Array.from({ length: 8 }).map((_, i) => (
            <div key={i} className="aspect-square bg-card border border-border rounded-[var(--radius-md)] animate-pulse" />
          ))}
        </div>
      </div>
    )
  }

  if (error || !detail) {
    return (
      <div className="max-w-6xl mx-auto">
        <div className="bg-card border border-border rounded-[var(--radius-lg)] p-12 text-center">
          <p className="text-sm text-error">{error ?? '任务不存在'}</p>
          <button
            onClick={() => navigate(`/ai-tools/text-to-image/${templateCode ?? 'english-primer'}`)}
            className="mt-4 h-10 px-4 bg-primary text-text-on-primary text-sm font-semibold rounded-[var(--radius-sm)] hover:bg-primary-hover cursor-pointer"
          >
            返回列表
          </button>
        </div>
      </div>
    )
  }

  const { task, images } = detail
  const hasGenerating = images.some((i) => i.status === 'generating')

  return (
    <div className="max-w-6xl mx-auto flex flex-col gap-6">
      {/* 页头 */}
      <div className="flex items-start justify-between gap-4">
        <div className="flex items-start gap-3">
          <Link
            to={`/ai-tools/text-to-image/${templateCode}`}
            className="mt-1 w-8 h-8 inline-flex items-center justify-center rounded-[var(--radius-sm)] text-text-muted hover:text-text-primary hover:bg-page transition-colors cursor-pointer"
            aria-label="返回"
          >
            <ArrowLeft size={16} />
          </Link>
          <div>
            <div className="flex items-center gap-3">
              <h1 className="text-2xl font-bold text-text-primary tracking-tight">
                {task.summary}
              </h1>
              <StatusBadge status={task.business_status} />
            </div>
            <p className="text-sm text-text-muted mt-1">
              {Object.entries(task.keywords)
                .map(([k, v]) => `${k}: ${v}`)
                .join(' · ')}
            </p>
          </div>
        </div>

        {isAdmin && (
          <motion.button
            whileHover={{ scale: hasGenerating ? 1 : 1.01 }}
            whileTap={{ scale: hasGenerating ? 1 : 0.98 }}
            onClick={handleRetry}
            disabled={retrying || hasGenerating}
            className="shrink-0 inline-flex items-center gap-1.5 h-11 px-4 bg-primary text-text-on-primary text-sm font-semibold rounded-[var(--radius-sm)] hover:bg-primary-hover transition-colors disabled:opacity-50 disabled:cursor-not-allowed cursor-pointer"
          >
            {retrying || hasGenerating ? (
              <Loader2 size={14} className="animate-spin" />
            ) : (
              <RefreshCw size={14} />
            )}
            {hasGenerating ? '生成中…' : '再生成一张'}
          </motion.button>
        )}
      </div>

      {/* 图片网格 */}
      {images.length === 0 ? (
        <div className="bg-card border border-border rounded-[var(--radius-lg)] p-16 text-center">
          <p className="text-sm text-text-muted">还没有图片</p>
        </div>
      ) : (
        <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-3">
          {images.map((img) => (
            <T2IImageTile
              key={img.id}
              image={img}
              isAdmin={isAdmin}
              onView={() => openLightbox(img.id)}
              onToggleAvailable={() => handleToggleAvailable(img)}
              onDelete={() => handleDelete(img)}
            />
          ))}
        </div>
      )}

      {/* 底部元信息 */}
      <div className="text-xs text-text-muted flex flex-wrap items-center gap-x-4 gap-y-1 border-t border-border pt-4">
        <span>创建于 {new Date(task.created_at).toLocaleString()}</span>
        <span>共 {task.images_total} 张</span>
        <span>可用 {task.images_available}</span>
        {task.images_failed > 0 && <span>失败 {task.images_failed}</span>}
      </div>

      <AnimatePresence>
        {lightboxIndex !== null && (
          <T2IImageLightbox
            images={succeededImages}
            currentIndex={lightboxIndex}
            onClose={() => setLightboxIndex(null)}
            onNavigate={(idx) => setLightboxIndex(idx)}
          />
        )}
      </AnimatePresence>
    </div>
  )
}
