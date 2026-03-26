import { motion } from 'framer-motion'

interface AuthLayoutProps {
  children: React.ReactNode
}

export default function AuthLayout({ children }: AuthLayoutProps) {
  return (
    <div className="min-h-screen w-full flex items-center justify-center p-4 md:p-6 bg-gradient-to-br from-page via-page-alt to-page relative overflow-hidden">
      {/* Subtle background pattern */}
      <div
        className="absolute inset-0 opacity-[0.03]"
        style={{
          backgroundImage:
            'radial-gradient(circle at 1px 1px, #2E3A4D 1px, transparent 0)',
          backgroundSize: '32px 32px',
        }}
      />

      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.5, ease: 'easeOut' }}
        className="relative flex w-full max-w-[1040px] h-auto md:h-[680px] bg-card rounded-[var(--radius-lg)] shadow-[0_8px_40px_rgba(26,26,26,0.10)] overflow-hidden"
      >
        {/* Left Branding Panel - 40% */}
        <div className="hidden md:flex w-[40%] bg-dark flex-col justify-between p-10 lg:p-14">
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            transition={{ delay: 0.2 }}
          >
            <span className="font-heading text-lg font-bold text-accent tracking-[2px]">
              ROBERTGATE
            </span>
          </motion.div>

          <motion.div
            initial={{ opacity: 0, x: -20 }}
            animate={{ opacity: 1, x: 0 }}
            transition={{ delay: 0.3, duration: 0.5 }}
            className="flex flex-col gap-6"
          >
            <h1 className="font-heading text-4xl lg:text-[42px] font-bold text-text-on-dark leading-[1.05]">
              Start Your
              <br />
              Journey.
            </h1>
            <p className="font-body text-base text-text-muted leading-relaxed">
              Create an account and join thousands of teams already building
              with us.
            </p>
          </motion.div>

          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            transition={{ delay: 0.5 }}
            className="flex flex-col gap-2"
          >
            <div className="w-full h-[2px] bg-border-dark" />
            <p className="font-body text-sm italic text-text-muted">
              "Every expert was once a beginner."
            </p>
            <p className="font-heading text-[11px] font-semibold text-text-muted tracking-[1px]">
              — Helen Hayes
            </p>
          </motion.div>
        </div>

        {/* Mobile Branding - shown only on mobile */}
        <div className="flex md:hidden bg-dark px-6 py-5 items-center absolute top-0 left-0 right-0 z-10">
          <span className="font-heading text-sm font-bold text-accent tracking-[2px]">
            ROBERTGATE
          </span>
        </div>

        {/* Right Form Panel - 60% */}
        <div className="flex-1 flex items-center justify-center p-6 pt-16 md:pt-6 md:p-14">
          <motion.div
            initial={{ opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.3, duration: 0.4 }}
            className="w-full max-w-[360px]"
          >
            {children}
          </motion.div>
        </div>
      </motion.div>
    </div>
  )
}
