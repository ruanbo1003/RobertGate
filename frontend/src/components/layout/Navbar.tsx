import { useState } from 'react'
import { Link } from 'react-router-dom'
import { Menu, X, Cpu, Bookmark, User } from 'lucide-react'
import { motion, AnimatePresence } from 'framer-motion'
import { useAuth } from '../../store/AuthContext'

const navLinks = [
  { to: '/ai-tools', label: 'AI Tools', icon: Cpu },
  { to: '/bookmarks', label: 'Bookmarks', icon: Bookmark },
  { to: '/about', label: 'About', icon: User },
]

export default function Navbar() {
  const { isAuthenticated } = useAuth()
  const [menuOpen, setMenuOpen] = useState(false)

  return (
    <nav className="sticky top-0 z-[var(--rg-z-sticky)] w-full bg-card/80 backdrop-blur-lg border-b border-border">
      <div className="max-w-6xl mx-auto px-5 h-14 flex items-center justify-between">
        {/* Logo */}
        <Link to="/" className="font-sans text-base font-bold text-text-primary tracking-wider">
          ROBERT<span className="text-primary">GATE</span>
        </Link>

        {/* Desktop nav links */}
        <div className="hidden md:flex items-center gap-1">
          {navLinks.map(({ to, label, icon: Icon }) => (
            <Link
              key={to}
              to={to}
              className="flex items-center gap-1.5 px-3 py-2 text-sm font-medium text-text-secondary hover:text-primary rounded-[var(--radius-sm)] hover:bg-primary-light/50 transition-colors"
            >
              <Icon size={15} />
              {label}
            </Link>
          ))}
        </div>

        {/* Desktop CTA */}
        <div className="hidden md:flex items-center">
          {isAuthenticated ? (
            <Link
              to="/dashboard"
              className="flex items-center gap-1.5 h-9 px-4 bg-primary hover:bg-primary-hover text-white text-sm font-semibold rounded-[var(--radius-sm)] transition-colors"
            >
              Dashboard
            </Link>
          ) : (
            <Link
              to="/login"
              className="flex items-center gap-1.5 h-9 px-4 bg-primary hover:bg-primary-hover text-white text-sm font-semibold rounded-[var(--radius-sm)] transition-colors"
            >
              Sign In
            </Link>
          )}
        </div>

        {/* Mobile hamburger */}
        <button
          onClick={() => setMenuOpen(!menuOpen)}
          aria-label={menuOpen ? 'Close menu' : 'Open menu'}
          className="md:hidden p-2 text-text-secondary hover:text-text-primary transition-colors cursor-pointer"
        >
          {menuOpen ? <X size={20} /> : <Menu size={20} />}
        </button>
      </div>

      {/* Mobile menu */}
      <AnimatePresence>
        {menuOpen && (
          <motion.div
            initial={{ height: 0, opacity: 0 }}
            animate={{ height: 'auto', opacity: 1 }}
            exit={{ height: 0, opacity: 0 }}
            transition={{ duration: 0.2 }}
            className="md:hidden overflow-hidden border-t border-border bg-card"
          >
            <div className="px-5 py-3 flex flex-col gap-1">
              {navLinks.map(({ to, label, icon: Icon }) => (
                <Link
                  key={to}
                  to={to}
                  onClick={() => setMenuOpen(false)}
                  className="flex items-center gap-2 px-3 py-2.5 text-sm font-medium text-text-secondary hover:text-primary hover:bg-primary-light/50 rounded-[var(--radius-sm)] transition-colors"
                >
                  <Icon size={16} />
                  {label}
                </Link>
              ))}
              <div className="border-t border-border my-1" />
              <Link
                to={isAuthenticated ? '/dashboard' : '/login'}
                onClick={() => setMenuOpen(false)}
                className="flex items-center justify-center h-10 bg-primary hover:bg-primary-hover text-white text-sm font-semibold rounded-[var(--radius-sm)] transition-colors"
              >
                {isAuthenticated ? 'Dashboard' : 'Sign In'}
              </Link>
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </nav>
  )
}
