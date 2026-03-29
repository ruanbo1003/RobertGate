import { Link, Navigate } from 'react-router-dom'
import { motion } from 'framer-motion'
import { ArrowRight, Cpu, Bookmark, User } from 'lucide-react'
import Navbar from '../components/layout/Navbar'
import Footer from '../components/layout/Footer'
import { useAuth } from '../store/AuthContext'

const features = [
  {
    to: '/ai-tools',
    icon: Cpu,
    title: 'AI Tools',
    description: 'A collection of AI-powered developer tools to boost your productivity.',
    color: 'bg-primary/10 text-primary',
  },
  {
    to: '/bookmarks',
    icon: Bookmark,
    title: 'Bookmarks',
    description: 'Curated collection of useful websites, libraries, and resources.',
    color: 'bg-accent-light text-accent',
  },
  {
    to: '/about',
    icon: User,
    title: 'About',
    description: 'Learn more about the developer behind RobertGate.',
    color: 'bg-success-light text-success',
  },
]

const stagger = {
  hidden: {},
  show: { transition: { staggerChildren: 0.1 } },
}

const fadeUp = {
  hidden: { opacity: 0, y: 20 },
  show: { opacity: 1, y: 0, transition: { duration: 0.4, ease: 'easeOut' } },
}

export default function HomePage() {
  const { isAuthenticated } = useAuth()

  if (isAuthenticated) {
    return <Navigate to="/not-implemented" replace />
  }

  return (
    <div className="min-h-screen flex flex-col bg-page relative">
      {/* Background grid */}
      <div
        className="fixed inset-0 opacity-[0.4] pointer-events-none"
        style={{
          backgroundImage:
            'linear-gradient(to right, #E2E8F0 1px, transparent 1px), linear-gradient(to bottom, #E2E8F0 1px, transparent 1px)',
          backgroundSize: '48px 48px',
        }}
      />

      <Navbar />

      <main className="flex-1 relative z-[1]">
        {/* Hero Section */}
        <motion.section
          variants={stagger}
          initial="hidden"
          animate="show"
          className="max-w-6xl mx-auto px-5 pt-20 pb-16 md:pt-28 md:pb-20 text-center"
        >
          <motion.div variants={fadeUp} className="inline-flex items-center gap-2 px-3 py-1 bg-primary-light/60 rounded-[var(--radius-full)] mb-6">
            <div className="w-1.5 h-1.5 rounded-full bg-primary animate-pulse" />
            <span className="text-xs font-semibold text-primary">Developer Toolkit</span>
          </motion.div>

          <motion.h1
            variants={fadeUp}
            className="font-sans text-4xl md:text-5xl lg:text-6xl font-extrabold text-text-primary tracking-tight leading-[1.1] mb-5"
          >
            Tools & Resources
            <br />
            <span className="text-primary">for Developers</span>
          </motion.h1>

          <motion.p
            variants={fadeUp}
            className="font-sans text-lg md:text-xl text-muted-foreground max-w-xl mx-auto leading-relaxed mb-10"
          >
            AI-powered tools, curated bookmarks, and developer resources — all in one place.
          </motion.p>

          <motion.div
            variants={fadeUp}
            className="flex flex-col sm:flex-row items-center justify-center gap-3"
          >
            <Link
              to="/login"
              className="flex items-center gap-2 h-11 px-6 bg-primary hover:bg-primary-hover text-white font-sans text-sm font-semibold rounded-[var(--radius-sm)] transition-all duration-150 hover:shadow-[var(--rg-shadow-button-hover)]"
            >
              Sign In
              <ArrowRight size={16} />
            </Link>
            <Link
              to="/register"
              className="flex items-center gap-2 h-11 px-6 border border-border hover:border-primary text-text-secondary hover:text-primary font-sans text-sm font-semibold rounded-[var(--radius-sm)] transition-all duration-150 bg-card"
            >
              Create Account
            </Link>
          </motion.div>
        </motion.section>

        {/* Features Section */}
        <motion.section
          variants={stagger}
          initial="hidden"
          animate="show"
          className="max-w-6xl mx-auto px-5 pb-20 md:pb-28"
        >
          <div className="grid grid-cols-1 md:grid-cols-3 gap-5">
            {features.map(({ to, icon: Icon, title, description, color }) => (
              <motion.div key={to} variants={fadeUp}>
                <Link
                  to={to}
                  className="group flex flex-col gap-4 p-6 bg-card rounded-[var(--radius-lg)] border border-border hover:border-primary/30 shadow-sm hover:shadow-md transition-all duration-150 hover:-translate-y-0.5"
                >
                  <div className={`w-10 h-10 rounded-[var(--radius-md)] flex items-center justify-center ${color}`}>
                    <Icon size={20} />
                  </div>
                  <div className="flex flex-col gap-1.5">
                    <h3 className="font-sans text-base font-bold text-text-primary group-hover:text-primary transition-colors">
                      {title}
                    </h3>
                    <p className="font-sans text-sm text-muted-foreground leading-relaxed">
                      {description}
                    </p>
                  </div>
                  <span className="font-sans text-xs font-semibold text-primary opacity-0 group-hover:opacity-100 transition-opacity">
                    Explore →
                  </span>
                </Link>
              </motion.div>
            ))}
          </div>
        </motion.section>
      </main>

      <Footer />
    </div>
  )
}
