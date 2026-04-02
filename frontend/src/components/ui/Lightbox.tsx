import { useEffect, useCallback, useState } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { X, ChevronLeft, ChevronRight, Maximize, Minimize } from 'lucide-react'
import type { Photo } from '../../types/gallery'

interface LightboxProps {
  photos: Photo[]
  currentIndex: number
  onClose: () => void
  onNavigate: (index: number) => void
}

export default function Lightbox({
  photos,
  currentIndex,
  onClose,
  onNavigate,
}: LightboxProps) {
  const [isFullscreen, setIsFullscreen] = useState(false)
  const photo = photos[currentIndex]
  const isFirst = currentIndex === 0
  const isLast = currentIndex === photos.length - 1

  const toggleFullscreen = useCallback(async () => {
    if (!document.fullscreenElement) {
      await document.documentElement.requestFullscreen()
    } else {
      await document.exitFullscreen()
    }
  }, [])

  useEffect(() => {
    const onFsChange = () => setIsFullscreen(!!document.fullscreenElement)
    document.addEventListener('fullscreenchange', onFsChange)
    return () => document.removeEventListener('fullscreenchange', onFsChange)
  }, [])

  useEffect(() => {
    const handleKey = (e: KeyboardEvent) => {
      if (e.key === 'Escape') {
        if (isFullscreen) return // browser handles fullscreen exit
        onClose()
      } else if (e.key === 'ArrowLeft' && !isFirst) {
        onNavigate(currentIndex - 1)
      } else if (e.key === 'ArrowRight' && !isLast) {
        onNavigate(currentIndex + 1)
      } else if (e.key === 'f' || e.key === 'F') {
        toggleFullscreen()
      }
    }
    window.addEventListener('keydown', handleKey)
    return () => window.removeEventListener('keydown', handleKey)
  }, [currentIndex, isFirst, isLast, isFullscreen, onClose, onNavigate, toggleFullscreen])

  // Lock body scroll
  useEffect(() => {
    document.body.style.overflow = 'hidden'
    return () => { document.body.style.overflow = '' }
  }, [])

  return (
    <motion.div
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      exit={{ opacity: 0 }}
      transition={{ duration: 0.2 }}
      className="fixed inset-0 z-[var(--rg-z-modal)] bg-black/85 flex items-center justify-center"
      onClick={onClose}
    >
      {/* Top bar */}
      <div className="absolute top-0 left-0 right-0 flex items-center justify-between p-4 z-10">
        <span className="text-white/70 text-sm font-sans font-medium">
          {currentIndex + 1} / {photos.length}
        </span>
        <div className="flex items-center gap-2">
          <button
            onClick={(e) => { e.stopPropagation(); toggleFullscreen() }}
            className="p-2 text-white/70 hover:text-white transition-colors cursor-pointer"
            aria-label={isFullscreen ? 'Exit fullscreen' : 'Fullscreen'}
          >
            {isFullscreen ? <Minimize size={20} /> : <Maximize size={20} />}
          </button>
          <button
            onClick={(e) => { e.stopPropagation(); onClose() }}
            className="p-2 text-white/70 hover:text-white transition-colors cursor-pointer"
            aria-label="Close"
          >
            <X size={20} />
          </button>
        </div>
      </div>

      {/* Left arrow */}
      <button
        onClick={(e) => { e.stopPropagation(); if (!isFirst) onNavigate(currentIndex - 1) }}
        disabled={isFirst}
        className="absolute left-3 md:left-6 p-2 text-white/60 hover:text-white disabled:text-white/20 disabled:cursor-default transition-colors cursor-pointer z-10"
        aria-label="Previous"
      >
        <ChevronLeft size={32} />
      </button>

      {/* Right arrow */}
      <button
        onClick={(e) => { e.stopPropagation(); if (!isLast) onNavigate(currentIndex + 1) }}
        disabled={isLast}
        className="absolute right-3 md:right-6 p-2 text-white/60 hover:text-white disabled:text-white/20 disabled:cursor-default transition-colors cursor-pointer z-10"
        aria-label="Next"
      >
        <ChevronRight size={32} />
      </button>

      {/* Photo */}
      <AnimatePresence mode="wait">
        <motion.img
          key={photo.filename}
          src={photo.url}
          alt={photo.filename}
          initial={{ opacity: 0, scale: 0.95 }}
          animate={{ opacity: 1, scale: 1 }}
          exit={{ opacity: 0, scale: 0.95 }}
          transition={{ duration: 0.2 }}
          onClick={(e) => e.stopPropagation()}
          className="max-h-[85vh] max-w-[90vw] object-contain select-none"
        />
      </AnimatePresence>
    </motion.div>
  )
}
