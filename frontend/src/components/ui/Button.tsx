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
  const isDisabled = disabled || loading

  return (
    <motion.button
      type={type}
      onClick={onClick}
      disabled={isDisabled}
      whileHover={isDisabled ? undefined : { scale: 1.01 }}
      whileTap={isDisabled ? undefined : { scale: 0.98 }}
      className="flex items-center justify-center gap-2 w-full h-11 bg-primary text-text-on-primary font-sans text-sm font-semibold rounded-[var(--radius-sm)] transition-all duration-150 cursor-pointer hover:bg-primary-hover disabled:opacity-50 disabled:cursor-not-allowed disabled:hover:bg-primary"
    >
      {loading ? (
        <div className="w-4 h-4 border-2 border-white/30 border-t-white rounded-full animate-spin" />
      ) : (
        <>
          {Icon && <Icon size={16} />}
          {children}
        </>
      )}
    </motion.button>
  )
}
