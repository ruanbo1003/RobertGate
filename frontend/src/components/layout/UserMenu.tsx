import { useEffect, useRef, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { motion, AnimatePresence } from 'framer-motion'
import { useAuth } from '../../store/AuthContext'

export default function UserMenu() {
  const { user, logout } = useAuth()
  const navigate = useNavigate()
  const [open, setOpen] = useState(false)
  const containerRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    if (!open) return
    const onClick = (e: MouseEvent) => {
      if (!containerRef.current?.contains(e.target as Node)) setOpen(false)
    }
    const onKey = (e: KeyboardEvent) => {
      if (e.key === 'Escape') setOpen(false)
    }
    document.addEventListener('mousedown', onClick)
    document.addEventListener('keydown', onKey)
    return () => {
      document.removeEventListener('mousedown', onClick)
      document.removeEventListener('keydown', onKey)
    }
  }, [open])

  if (!user) return null

  const initial = (user.username || user.email || '?').charAt(0).toUpperCase()

  const handleLogout = () => {
    setOpen(false)
    logout()
    navigate('/login')
  }

  return (
    <div ref={containerRef} className="relative">
      <button
        type="button"
        onClick={() => setOpen((v) => !v)}
        aria-label="User menu"
        aria-haspopup="menu"
        aria-expanded={open}
        className="flex items-center justify-center w-9 h-9 rounded-full bg-primary text-white text-sm font-bold hover:bg-primary-hover transition-colors cursor-pointer"
      >
        {initial}
      </button>

      <AnimatePresence>
        {open && (
          <motion.div
            initial={{ opacity: 0, y: -4 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -4 }}
            transition={{ duration: 0.15, ease: 'easeOut' }}
            role="menu"
            className="absolute right-0 mt-2 w-72 bg-card border border-border rounded-[var(--radius-md)] shadow-[0_8px_32px_rgba(0,0,0,0.08)] overflow-hidden z-[var(--rg-z-dropdown)]"
          >
            {/* Header: avatar + name / email */}
            <div className="px-4 py-4 flex items-center gap-3">
              <div className="flex items-center justify-center w-10 h-10 rounded-full bg-primary text-white text-base font-bold shrink-0">
                {initial}
              </div>
              <div className="min-w-0 flex-1">
                <div className="font-sans text-sm text-text-primary truncate">
                  <span className="font-bold">{user.username}</span>
                  <span className="text-text-muted font-normal"> · {user.role}</span>
                </div>
                <div className="font-sans text-xs text-text-muted truncate">
                  {user.email}
                </div>
              </div>
            </div>

            <div className="border-t border-border" />

            {/* Sign out */}
            <button
              type="button"
              onClick={handleLogout}
              role="menuitem"
              className="w-full text-left px-4 py-3 text-sm text-text-primary hover:bg-page transition-colors cursor-pointer"
            >
              Sign out
            </button>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  )
}
