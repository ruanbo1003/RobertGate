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
      className="flex items-center justify-center gap-2 w-full h-[52px] bg-accent text-text-on-dark font-heading text-xs font-semibold tracking-[1px] uppercase rounded-[var(--radius-sm)] transition-all duration-200 cursor-pointer hover:bg-accent-hover hover:shadow-[0_4px_12px_rgba(192,90,60,0.3)] disabled:opacity-50 disabled:cursor-not-allowed disabled:hover:bg-accent disabled:hover:shadow-none"
    >
      {loading ? (
        <div className="w-5 h-5 border-2 border-text-on-dark/30 border-t-text-on-dark rounded-full animate-spin" />
      ) : (
        <>
          {Icon && <Icon size={16} />}
          {children}
        </>
      )}
    </motion.button>
  )
}
