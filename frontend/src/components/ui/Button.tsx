import { motion } from 'framer-motion'
import type { LucideIcon } from 'lucide-react'

interface ButtonProps {
  children: string
  icon?: LucideIcon
  onClick?: () => void
  loading?: boolean
  disabled?: boolean
  type?: 'button' | 'submit'
}

export default function Button({
  children,
  icon: Icon,
  onClick,
  loading = false,
  disabled = false,
  type = 'button',
}: ButtonProps) {
  return (
    <motion.button
      type={type}
      onClick={onClick}
      disabled={disabled || loading}
      whileHover={{ scale: 1.01 }}
      whileTap={{ scale: 0.98 }}
      className="flex items-center justify-center gap-2 w-full h-[52px] bg-accent hover:bg-accent-hover text-text-on-dark font-heading text-xs font-semibold tracking-[1px] uppercase transition-colors disabled:opacity-60 disabled:cursor-not-allowed cursor-pointer"
    >
      {loading ? (
        <div className="w-4 h-4 border-2 border-text-on-dark/30 border-t-text-on-dark rounded-full animate-spin" />
      ) : (
        <>
          {Icon && <Icon size={16} />}
          {children}
        </>
      )}
    </motion.button>
  )
}
