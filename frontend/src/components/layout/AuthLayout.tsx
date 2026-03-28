import { motion } from 'framer-motion'

interface AuthLayoutProps {
  children: React.ReactNode
}

export default function AuthLayout({ children }: AuthLayoutProps) {
  return (
    <div className="min-h-screen w-full flex items-center justify-center p-4 md:p-6 bg-page relative overflow-hidden">
      {/* Subtle grid pattern */}
      <div
        className="absolute inset-0 opacity-[0.4]"
        style={{
          backgroundImage:
            'linear-gradient(to right, #E2E8F0 1px, transparent 1px), linear-gradient(to bottom, #E2E8F0 1px, transparent 1px)',
          backgroundSize: '48px 48px',
        }}
      />

      <motion.div
        initial={{ opacity: 0, y: 16 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.4, ease: 'easeOut' }}
        className="relative flex w-full max-w-[1000px] h-auto md:h-[660px] bg-card rounded-[var(--radius-lg)] shadow-[0_1px_3px_rgba(0,0,0,0.08),0_8px_32px_rgba(0,0,0,0.06)] overflow-hidden"
      >
        {/* Left Branding Panel - 40% */}
        <div className="hidden md:flex w-[40%] bg-dark flex-col justify-between p-10 lg:p-12">
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            transition={{ delay: 0.15 }}
          >
            <span className="font-sans text-base font-bold text-text-on-dark tracking-wider">
              ROBERT<span className="text-primary">GATE</span>
            </span>
          </motion.div>

          <motion.div
            initial={{ opacity: 0, x: -12 }}
            animate={{ opacity: 1, x: 0 }}
            transition={{ delay: 0.2, duration: 0.4 }}
            className="flex flex-col gap-5"
          >
            <h1 className="font-sans text-[36px] font-extrabold text-text-on-dark leading-[1.1] tracking-tight">
              Start Your
              <br />
              Journey.
            </h1>
            <p className="font-sans text-[15px] text-text-muted leading-relaxed">
              Create an account and join thousands of teams already building
              with us.
            </p>
          </motion.div>

          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            transition={{ delay: 0.35 }}
            className="flex flex-col gap-3"
          >
            <div className="w-full h-px bg-border-dark" />
            <p className="font-sans text-sm italic text-muted-foreground">
              "Every expert was once a beginner."
            </p>
            <p className="font-sans text-xs font-semibold text-muted-foreground tracking-wide">
              — Helen Hayes
            </p>
          </motion.div>
        </div>

        {/* Mobile Branding */}
        <div className="flex md:hidden bg-dark px-5 py-4 items-center absolute top-0 left-0 right-0 z-10">
          <span className="font-sans text-sm font-bold text-text-on-dark tracking-wider">
            ROBERT<span className="text-primary">GATE</span>
          </span>
        </div>

        {/* Right Form Panel - 60% */}
        <div className="flex-1 flex items-center justify-center p-6 pt-16 md:pt-6 md:p-12">
          <motion.div
            initial={{ opacity: 0, y: 8 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.2, duration: 0.3 }}
            className="w-full max-w-[360px]"
          >
            {children}
          </motion.div>
        </div>
      </motion.div>
    </div>
  )
}
