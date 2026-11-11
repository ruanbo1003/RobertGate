import { Link } from 'react-router-dom'
import { motion } from 'framer-motion'
import { ArrowRight, Cpu, Bookmark, Clapperboard, FileText } from 'lucide-react'
import Navbar from '../components/layout/Navbar'
import Footer from '../components/layout/Footer'
import { useAuth } from '../store/AuthContext'

// Hide the hero CTAs (Sign In / Create Account) for already-authenticated users

const features = [
  {
    to: '/ai-videos',
    icon: Clapperboard,
    title: 'AI Videos',
    description: 'From a one-line idea to a publishable short video — script, storyboard, voice and cut',
  },
  {
    to: '/invest-reports',
    icon: FileText,
    title: 'Invest Reports',
    description: 'Agent-drafted investment memos with traceable sources, exported to Word',
  },
  {
    to: '/ai-tools',
    icon: Cpu,
    title: 'Tools',
    description: 'A small collection of AI developer tools, each doing one job',
  },
  {
    to: '/bookmarks',
    icon: Bookmark,
    title: 'Bookmarks',
    description: 'Curated websites, libraries and resources, kept current',
  },
]

// ai-videos 工作台预览的分镜数据（仅展示用的真实感样例）
const previewShots = [
  { no: 1, line: 'Repeat after me: apple', status: '成功', statusColor: 'bg-success' },
  { no: 2, line: 'A is for apple, 苹果', status: '成功', statusColor: 'bg-success' },
  { no: 3, line: 'One apple, two apples', status: '生成中', statusColor: 'bg-primary' },
]

const stagger = {
  hidden: {},
  show: { transition: { staggerChildren: 0.1 } },
}

const fadeUp = {
  hidden: { opacity: 0, y: 20 },
  show: { opacity: 1, y: 0, transition: { duration: 0.4, ease: 'easeOut' as const } },
}

/** 分镜缩略图：纯 CSS 平面场景（苹果树下的太阳与山丘），9:16 */
function ShotThumb({ className = '' }: { className?: string }) {
  return (
    <div className={`relative overflow-hidden rounded-[var(--radius-sm)] bg-primary-light ${className}`}>
      {/* 太阳 */}
      <div className="absolute top-[12%] right-[14%] w-[28%] aspect-square rounded-full bg-warning" />
      {/* 远山 */}
      <div className="absolute bottom-[-12%] left-[-20%] w-[90%] aspect-square rounded-full bg-success/60" />
      {/* 近丘 */}
      <div className="absolute bottom-[-25%] right-[-25%] w-[110%] aspect-square rounded-full bg-success" />
      {/* 苹果 */}
      <div className="absolute bottom-[26%] left-[22%] w-[14%] aspect-square rounded-full bg-accent" />
      <div className="absolute bottom-[34%] left-[42%] w-[11%] aspect-square rounded-full bg-accent" />
    </div>
  )
}

export default function HomePage() {
  const { isAuthenticated } = useAuth()

  return (
    <div className="min-h-screen flex flex-col bg-page relative">
      {/* Background grid */}
      <div
        className="fixed inset-0 opacity-[0.4] pointer-events-none"
        style={{
          backgroundImage:
            'linear-gradient(to right, var(--rg-color-border) 1px, transparent 1px), linear-gradient(to bottom, var(--rg-color-border) 1px, transparent 1px)',
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
          className="w-full max-w-6xl mx-auto px-5 pt-16 md:pt-20 text-center"
        >
          <motion.h1
            variants={fadeUp}
            className="font-sans text-4xl md:text-5xl font-semibold text-text-primary tracking-tight leading-[1.15] mb-5"
          >
            Turn ideas into short videos
            <br />
            <span className="text-primary">and investment reports</span>
          </motion.h1>

          <motion.p
            variants={fadeUp}
            className="font-sans text-lg md:text-xl text-muted-foreground max-w-xl mx-auto leading-relaxed mb-8"
          >
            RobertGate is Robert&apos;s personal AI workbench — video production, report
            drafting, and the tools and bookmarks behind them
          </motion.p>

          <motion.div
            variants={fadeUp}
            className="flex flex-col sm:flex-row items-center justify-center gap-3"
          >
            {isAuthenticated ? (
              <Link
                to="/ai-tools"
                className="flex items-center gap-2 h-11 px-6 bg-primary hover:bg-primary-hover text-white font-sans text-sm font-medium rounded-[var(--radius-sm)] transition-colors duration-150"
              >
                Go to Tools
                <ArrowRight size={16} strokeWidth={1.5} />
              </Link>
            ) : (
              <>
                <Link
                  to="/login"
                  className="flex items-center gap-2 h-11 px-6 bg-primary hover:bg-primary-hover text-white font-sans text-sm font-medium rounded-[var(--radius-sm)] transition-colors duration-150"
                >
                  Sign In
                  <ArrowRight size={16} strokeWidth={1.5} />
                </Link>
                <Link
                  to="/register"
                  className="flex items-center gap-2 h-11 px-6 border border-border hover:border-primary text-text-secondary hover:text-primary font-sans text-sm font-medium rounded-[var(--radius-sm)] transition-colors duration-150 bg-card"
                >
                  Create Account
                </Link>
              </>
            )}
          </motion.div>

          {/* Product preview: ai-videos 创作工作台 */}
          <motion.div variants={fadeUp} className="mt-14 md:mt-16 max-w-4xl mx-auto text-left">
            <div className="rounded-[var(--radius-lg)] border border-border bg-card shadow-sm shadow-[0_8px_32px_rgba(0,0,0,0.08)] overflow-hidden">
              {/* 窗口栏 */}
              <div className="flex items-center h-9 px-4 border-b border-border bg-page">
                <div className="flex items-center gap-1.5">
                  <span className="w-2.5 h-2.5 rounded-full bg-border" />
                  <span className="w-2.5 h-2.5 rounded-full bg-border" />
                  <span className="w-2.5 h-2.5 rounded-full bg-border" />
                </div>
                <span className="ml-4 font-mono text-xs text-text-muted">
                  AI Videos · 创作工作台 · 水果单词 第 3 集
                </span>
              </div>

              <div className="grid grid-cols-1 md:grid-cols-[240px_1fr]">
                {/* 分镜轨 */}
                <div className="hidden md:flex flex-col gap-2 p-4 border-r border-border">
                  <span className="font-sans text-xs font-medium text-text-secondary mb-1">分镜</span>
                  {previewShots.map(({ no, status, statusColor }) => (
                    <div
                      key={no}
                      className={`flex items-center gap-3 p-2 rounded-[var(--radius-md)] border ${
                        no === 1 ? 'border-primary/30 bg-primary-light/40' : 'border-border'
                      }`}
                    >
                      <ShotThumb className="w-9 h-16 shrink-0" />
                      <div className="flex flex-col gap-1 min-w-0">
                        <span className="font-mono text-xs text-text-primary">镜 {no} · 4s</span>
                        <span className="flex items-center gap-1.5 font-sans text-xs text-text-muted">
                          <span className={`w-1.5 h-1.5 rounded-full ${statusColor}`} />
                          {status}
                        </span>
                      </div>
                    </div>
                  ))}
                </div>

                {/* 当前分镜 */}
                <div className="flex gap-5 p-5">
                  <ShotThumb className="w-28 h-48 md:w-32 md:h-56 shrink-0" />
                  <div className="flex flex-col gap-3 min-w-0 flex-1">
                    <span className="font-mono text-xs text-text-muted">镜 1 · 出场角色 小云雀</span>
                    <p className="font-sans text-sm md:text-base text-text-primary leading-relaxed">
                      “Repeat after me: apple — A·P·P·L·E, apple, 苹果”
                    </p>
                    <div className="mt-auto flex flex-col gap-2">
                      {[
                        { label: '分镜图', status: '成功', color: 'bg-success' },
                        { label: '配音', status: '成功', color: 'bg-success' },
                        { label: '视频', status: '生成中', color: 'bg-primary' },
                      ].map(({ label, status, color }) => (
                        <div key={label} className="flex items-center gap-2 font-sans text-xs">
                          <span className="w-12 text-text-muted">{label}</span>
                          <span className={`w-1.5 h-1.5 rounded-full ${color}`} />
                          <span className="text-text-secondary">{status}</span>
                        </div>
                      ))}
                    </div>
                  </div>
                </div>
              </div>
            </div>
          </motion.div>
        </motion.section>

        {/* Features Section */}
        <motion.section
          variants={stagger}
          initial="hidden"
          whileInView="show"
          viewport={{ once: true, amount: 0.2 }}
          className="w-full max-w-6xl mx-auto px-5 mt-16 md:mt-20 pb-16 md:pb-20"
        >
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-5">
            {features.map(({ to, icon: Icon, title, description }) => (
              <motion.div key={to} variants={fadeUp} className="h-full">
                <Link
                  to={to}
                  className="group flex flex-col h-full gap-3 p-6 bg-card rounded-[var(--radius-lg)] border border-border hover:border-primary/30 shadow-sm hover:shadow-md transition-[border-color,box-shadow] duration-150"
                >
                  <Icon size={16} strokeWidth={1.5} className="text-text-muted" />
                  <div className="flex flex-col gap-1.5">
                    <h3 className="font-sans text-base font-medium text-text-primary">
                      {title}
                    </h3>
                    <p className="font-sans text-sm text-muted-foreground leading-relaxed">
                      {description}
                    </p>
                  </div>
                  <span className="mt-auto font-mono text-xs text-text-muted group-hover:text-primary transition-colors duration-150">
                    Open →
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
