import { useEffect } from 'react'
import { X } from 'lucide-react'
import { AnimatePresence, motion } from 'framer-motion'

interface ModalProps {
  open: boolean
  onClose: () => void
  title: string
  subtitle?: string
  children: React.ReactNode
  footer?: React.ReactNode
  width?: number
}

export default function Modal({ open, onClose, title, subtitle, children, footer, width = 520 }: ModalProps) {
  useEffect(() => {
    if (!open) return
    const onKey = (e: KeyboardEvent) => {
      if (e.key === 'Escape') onClose()
    }
    window.addEventListener('keydown', onKey)
    return () => window.removeEventListener('keydown', onKey)
  }, [open, onClose])

  return (
    <AnimatePresence>
      {open && (
        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          exit={{ opacity: 0 }}
          transition={{ duration: 0.15 }}
          className="fixed inset-0 z-50 bg-black/40 flex items-center justify-center p-4"
          onClick={onClose}
        >
          <motion.div
            initial={{ opacity: 0, scale: 0.96, y: 8 }}
            animate={{ opacity: 1, scale: 1, y: 0 }}
            exit={{ opacity: 0, scale: 0.96, y: 8 }}
            transition={{ duration: 0.18, ease: 'easeOut' }}
            style={{ width }}
            className="bg-card rounded-[var(--radius-lg)] shadow-lg max-w-full flex flex-col max-h-[calc(100vh-2rem)] overflow-hidden"
            onClick={(e) => e.stopPropagation()}
          >
            <div className="flex items-start justify-between p-5 border-b border-border">
              <div>
                <h3 className="text-lg font-bold text-text-primary tracking-tight">{title}</h3>
                {subtitle && <p className="text-sm text-text-muted mt-0.5">{subtitle}</p>}
              </div>
              <button
                onClick={onClose}
                className="w-8 h-8 rounded-[var(--radius-sm)] flex items-center justify-center text-text-muted hover:text-text-primary hover:bg-page transition-colors cursor-pointer"
                aria-label="关闭"
              >
                <X size={16} />
              </button>
            </div>
            <div className="p-5 overflow-y-auto flex-1">{children}</div>
            {footer && (
              <div className="p-5 border-t border-border bg-page-alt/50 flex items-center justify-end gap-2">
                {footer}
              </div>
            )}
          </motion.div>
        </motion.div>
      )}
    </AnimatePresence>
  )
}
