import { Link } from 'react-router-dom'
import { motion } from 'framer-motion'
import { ArrowLeft, Wrench } from 'lucide-react'

export default function NotImplementedPage() {
  return (
    <div className="min-h-screen w-full flex items-center justify-center p-6 bg-page relative overflow-hidden">
      <div
        className="absolute inset-0 opacity-[0.4]"
        style={{
          backgroundImage:
            'linear-gradient(to right, #E2E8F0 1px, transparent 1px), linear-gradient(to bottom, #E2E8F0 1px, transparent 1px)',
          backgroundSize: '48px 48px',
        }}
      />

      <motion.div
        initial={{ opacity: 0, scale: 0.8 }}
        animate={{ opacity: 1, scale: 1 }}
        transition={{ duration: 0.6 }}
        className="absolute select-none pointer-events-none"
      >
        <span
          className="font-sans font-extrabold text-primary/[0.05] leading-none"
          style={{ fontSize: 'clamp(200px, 40vw, 500px)' }}
        >
          501
        </span>
      </motion.div>

      <motion.div
        initial={{ opacity: 0, y: 24 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.4, delay: 0.15 }}
        className="relative z-10 flex flex-col items-center text-center max-w-md"
      >
        <motion.div
          animate={{ rotate: [0, 12, -12, 8, 0] }}
          transition={{ delay: 0.4, duration: 0.8 }}
          className="w-14 h-14 rounded-[var(--radius-md)] bg-accent flex items-center justify-center mb-6"
        >
          <Wrench size={24} className="text-white" />
        </motion.div>

        <h1 className="font-sans text-4xl md:text-5xl font-extrabold text-text-primary mb-3 leading-tight tracking-tight">
          Under construction
        </h1>

        <p className="font-sans text-base text-muted-foreground leading-relaxed mb-4">
          This feature is currently being built. We're working hard to bring it to you soon.
        </p>

        <div className="w-full max-w-[220px] mb-8">
          <div className="h-1.5 bg-border rounded-full overflow-hidden">
            <motion.div
              initial={{ width: 0 }}
              animate={{ width: '65%' }}
              transition={{ delay: 0.6, duration: 1, ease: 'easeOut' }}
              className="h-full bg-accent rounded-full"
            />
          </div>
          <p className="font-sans text-xs font-semibold text-muted-foreground mt-1.5 text-right">
            65%
          </p>
        </div>

        <Link
          to="/"
          className="flex items-center justify-center gap-2 h-11 px-8 bg-primary hover:bg-primary-hover text-white font-sans text-sm font-semibold rounded-[var(--radius-sm)] transition-colors"
        >
          <ArrowLeft size={16} />
          Back to Home
        </Link>
      </motion.div>
    </div>
  )
}
