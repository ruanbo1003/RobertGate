import { useState, useEffect, useRef, useMemo } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { ImageOff, RefreshCw } from 'lucide-react'
import Navbar from '../components/layout/Navbar'
import Footer from '../components/layout/Footer'
import Lightbox from '../components/ui/Lightbox'
import { getPhotos } from '../services/gallery'
import type { Photo } from '../types/gallery'

function useColumns() {
  const [cols, setCols] = useState(3)
  useEffect(() => {
    const update = () => {
      const w = window.innerWidth
      setCols(w < 640 ? 1 : w < 1024 ? 2 : 3)
    }
    update()
    window.addEventListener('resize', update)
    return () => window.removeEventListener('resize', update)
  }, [])
  return cols
}

function distributePhotos(photos: Photo[], cols: number): Photo[][] {
  const columns: Photo[][] = Array.from({ length: cols }, () => [])
  const heights = new Array(cols).fill(0)

  for (const photo of photos) {
    const shortest = heights.indexOf(Math.min(...heights))
    columns[shortest].push(photo)
    heights[shortest] += photo.height / photo.width
  }

  return columns
}

const fadeUp = {
  hidden: { opacity: 0, y: 16 },
  show: { opacity: 1, y: 0, transition: { duration: 0.3, ease: 'easeOut' as const } },
}

export default function GalleryPage() {
  const [photos, setPhotos] = useState<Photo[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [lightboxIndex, setLightboxIndex] = useState<number | null>(null)
  const cols = useColumns()

  const fetchPhotos = async () => {
    setLoading(true)
    setError('')
    const res = await getPhotos()
    setLoading(false)
    if (res.code === 0) {
      setPhotos(res.data.photos)
    } else {
      setError(res.message)
    }
  }

  useEffect(() => { fetchPhotos() }, [])

  const columns = useMemo(() => distributePhotos(photos, cols), [photos, cols])

  // Map column position back to flat index for lightbox
  const getGlobalIndex = (colIdx: number, rowIdx: number): number => {
    const photo = columns[colIdx][rowIdx]
    return photos.indexOf(photo)
  }

  return (
    <div className="min-h-screen flex flex-col bg-page relative">
      <div
        className="fixed inset-0 opacity-[0.4] pointer-events-none"
        style={{
          backgroundImage:
            'linear-gradient(to right, var(--rg-color-border) 1px, transparent 1px), linear-gradient(to bottom, var(--rg-color-border) 1px, transparent 1px)',
          backgroundSize: '48px 48px',
        }}
      />

      <Navbar />

      <main className="flex-1 relative z-[1]">
        <div className="max-w-6xl mx-auto px-5 pt-12 pb-20 md:pt-20 md:pb-28">
          <motion.h1
            initial={{ opacity: 0, y: 12 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.3 }}
            className="font-sans text-3xl md:text-4xl font-extrabold text-text-primary tracking-tight mb-8 md:mb-12"
          >
            Gallery
          </motion.h1>

          {/* Loading */}
          {loading && (
            <div className="flex gap-3">
              {Array.from({ length: cols }).map((_, c) => (
                <div key={c} className="flex-1 flex flex-col gap-3">
                  {[180, 240, 160].map((h, i) => (
                    <div
                      key={i}
                      className="w-full rounded-[var(--radius-sm)] bg-border/50 animate-pulse"
                      style={{ height: h }}
                    />
                  ))}
                </div>
              ))}
            </div>
          )}

          {/* Error */}
          {!loading && error && (
            <div className="flex flex-col items-center gap-4 py-20">
              <p className="font-sans text-muted-foreground">{error}</p>
              <button
                onClick={fetchPhotos}
                className="flex items-center gap-2 px-4 py-2 text-sm font-semibold text-primary border border-primary rounded-[var(--radius-sm)] hover:bg-primary hover:text-white transition-colors cursor-pointer"
              >
                <RefreshCw size={14} />
                Retry
              </button>
            </div>
          )}

          {/* Empty */}
          {!loading && !error && photos.length === 0 && (
            <div className="flex flex-col items-center gap-3 py-20">
              <ImageOff size={40} className="text-muted-foreground" />
              <p className="font-sans text-muted-foreground">No photos yet</p>
            </div>
          )}

          {/* Masonry Grid */}
          {!loading && !error && photos.length > 0 && (
            <motion.div
              initial="hidden"
              animate="show"
              variants={{ show: { transition: { staggerChildren: 0.03 } } }}
              className="flex gap-3"
            >
              {columns.map((column, colIdx) => (
                <div key={colIdx} className="flex-1 flex flex-col gap-3">
                  {column.map((photo, rowIdx) => (
                    <PhotoCard
                      key={photo.filename}
                      photo={photo}
                      onClick={() => setLightboxIndex(getGlobalIndex(colIdx, rowIdx))}
                    />
                  ))}
                </div>
              ))}
            </motion.div>
          )}
        </div>
      </main>

      <Footer />

      {/* Lightbox */}
      <AnimatePresence>
        {lightboxIndex !== null && (
          <Lightbox
            photos={photos}
            currentIndex={lightboxIndex}
            onClose={() => setLightboxIndex(null)}
            onNavigate={setLightboxIndex}
          />
        )}
      </AnimatePresence>
    </div>
  )
}

function PhotoCard({ photo, onClick }: { photo: Photo; onClick: () => void }) {
  const [loaded, setLoaded] = useState(false)
  const [inView, setInView] = useState(false)
  const ref = useRef<HTMLDivElement>(null)

  useEffect(() => {
    const el = ref.current
    if (!el) return
    const observer = new IntersectionObserver(
      ([entry]) => { if (entry.isIntersecting) { setInView(true); observer.disconnect() } },
      { rootMargin: '200px' }
    )
    observer.observe(el)
    return () => observer.disconnect()
  }, [])

  const aspectRatio = photo.width / photo.height

  return (
    <motion.div
      ref={ref}
      variants={fadeUp}
      onClick={onClick}
      className="group relative overflow-hidden rounded-[var(--radius-sm)] bg-border/30 shadow-sm hover:shadow-md transition-all duration-150 cursor-pointer"
      style={{ aspectRatio }}
    >
      {inView && (
        <img
          src={photo.thumbnail_url}
          alt={photo.filename}
          onLoad={() => setLoaded(true)}
          className={`w-full h-full object-cover transition-all duration-300 group-hover:scale-[1.02] ${
            loaded ? 'opacity-100' : 'opacity-0'
          }`}
        />
      )}
      {inView && !loaded && (
        <div className="absolute inset-0 bg-border/50 animate-pulse" />
      )}
    </motion.div>
  )
}
