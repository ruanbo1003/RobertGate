import { useEffect } from 'react'
import { AnimatePresence, motion } from 'framer-motion'
import { ChevronLeft, ChevronRight, X } from 'lucide-react'
import type { T2IImage } from '../../types/t2i'
import { resolveImageUrl } from '../../services/t2i'

interface Props {
  images: T2IImage[]
  currentIndex: number
  onClose: () => void
  onNavigate: (index: number) => void
}

/** 极简全屏查看器，只显示 succeeded 图。gallery 的 Lightbox 绑定 Photo 类型，这里独立实现更省事。 */
export default function T2IImageLightbox({ images, currentIndex, onClose, onNavigate }: Props) {
  const img = images[currentIndex]
  const isFirst = currentIndex === 0
  const isLast = currentIndex === images.length - 1

  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if (e.key === 'Escape') onClose()
      else if (e.key === 'ArrowLeft' && !isFirst) onNavigate(currentIndex - 1)
      else if (e.key === 'ArrowRight' && !isLast) onNavigate(currentIndex + 1)
    }
    window.addEventListener('keydown', onKey)
    return () => window.removeEventListener('keydown', onKey)
  }, [currentIndex, isFirst, isLast, onClose, onNavigate])

  useEffect(() => {
    document.body.style.overflow = 'hidden'
    return () => {
      document.body.style.overflow = ''
    }
  }, [])

  if (!img || !img.url) return null

  return (
    <motion.div
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      exit={{ opacity: 0 }}
      transition={{ duration: 0.15 }}
      className="fixed inset-0 z-50 bg-black/85 flex items-center justify-center"
      onClick={onClose}
    >
      <div className="absolute top-0 left-0 right-0 flex items-center justify-between p-4 z-10">
        <span className="text-white/70 text-sm font-medium">
          {currentIndex + 1} / {images.length}
        </span>
        <button
          onClick={(e) => {
            e.stopPropagation()
            onClose()
          }}
          className="p-2 text-white/70 hover:text-white transition-colors cursor-pointer"
          aria-label="关闭"
        >
          <X size={20} />
        </button>
      </div>

      <button
        onClick={(e) => {
          e.stopPropagation()
          if (!isFirst) onNavigate(currentIndex - 1)
        }}
        disabled={isFirst}
        className="absolute left-4 md:left-8 p-2 text-white/60 hover:text-white disabled:text-white/20 disabled:cursor-default transition-colors cursor-pointer z-10"
        aria-label="上一张"
      >
        <ChevronLeft size={32} />
      </button>

      <button
        onClick={(e) => {
          e.stopPropagation()
          if (!isLast) onNavigate(currentIndex + 1)
        }}
        disabled={isLast}
        className="absolute right-4 md:right-8 p-2 text-white/60 hover:text-white disabled:text-white/20 disabled:cursor-default transition-colors cursor-pointer z-10"
        aria-label="下一张"
      >
        <ChevronRight size={32} />
      </button>

      <AnimatePresence mode="wait">
        <motion.img
          key={img.id}
          src={resolveImageUrl(img.url)}
          alt=""
          initial={{ opacity: 0, scale: 0.95 }}
          animate={{ opacity: 1, scale: 1 }}
          exit={{ opacity: 0, scale: 0.95 }}
          transition={{ duration: 0.15 }}
          onClick={(e) => e.stopPropagation()}
          className="max-h-[85vh] max-w-[90vw] object-contain select-none"
        />
      </AnimatePresence>
    </motion.div>
  )
}
