import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { motion } from 'framer-motion'
import { ArrowRight, Settings } from 'lucide-react'
import { getLevels } from '../../services/hanzi'
import { useAuth } from '../../store/AuthContext'
import type { HanziLevel } from '../../types/hanzi'

export default function HanziLevelListPage() {
  const [levels, setLevels] = useState<HanziLevel[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const { user } = useAuth()
  const isAdmin = user?.role === 'admin'

  useEffect(() => {
    let mounted = true
    setLoading(true)
    getLevels().then((res) => {
      if (!mounted) return
      if (res.code === 0) {
        setLevels(res.data.levels)
        setError(null)
      } else {
        setError(res.message)
      }
      setLoading(false)
    })
    return () => {
      mounted = false
    }
  }, [])

  return (
    <div className="max-w-5xl mx-auto flex flex-col gap-6">
      <div className="flex items-start justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-text-primary tracking-tight">汉字学习</h1>
          <p className="text-sm text-text-muted mt-1">选一个级别，按顺序学习</p>
        </div>
        {isAdmin && (
          <Link
            to="/ai-tools/admin/hanzi"
            className="shrink-0 inline-flex items-center gap-1.5 h-11 px-4 bg-card border border-border text-text-primary text-sm font-semibold rounded-[var(--radius-sm)] hover:border-primary hover:text-primary transition-colors cursor-pointer"
          >
            <Settings size={16} />
            管理字库
          </Link>
        )}
      </div>

      {loading ? (
        <div className="grid gap-4 md:grid-cols-2">
          {[0, 1].map((i) => (
            <div
              key={i}
              className="h-40 bg-card border border-border rounded-[var(--radius-lg)] animate-pulse"
            />
          ))}
        </div>
      ) : error ? (
        <div className="bg-card border border-border rounded-[var(--radius-lg)] p-12 text-center">
          <p className="text-sm text-error">{error}</p>
        </div>
      ) : levels.length === 0 ? (
        <div className="bg-card border border-border rounded-[var(--radius-lg)] p-12 text-center">
          <div className="text-4xl mb-3">📘</div>
          <p className="text-sm text-text-muted">暂无学习内容，请联系管理员</p>
        </div>
      ) : (
        <div className="grid gap-4 md:grid-cols-2">
          {[...levels]
            .sort((a, b) => a.order_index - b.order_index)
            .map((lvl) => {
              const pct = lvl.total > 0 ? Math.round((lvl.learned / lvl.total) * 100) : 0
              const started = lvl.learned > 0
              return (
                <motion.div
                  key={lvl.id}
                  whileHover={{ y: -2 }}
                  transition={{ duration: 0.15 }}
                  className="bg-card border border-border rounded-[var(--radius-lg)] p-6 shadow-sm hover:shadow-[0_8px_32px_rgba(0,0,0,0.08)] transition-shadow flex flex-col gap-4"
                >
                  <div>
                    <h3 className="text-xl font-bold text-text-primary tracking-tight">
                      {lvl.name}
                    </h3>
                    {lvl.description && (
                      <p className="text-sm text-text-muted mt-1">{lvl.description}</p>
                    )}
                  </div>

                  <div className="flex flex-col gap-1.5">
                    <div className="flex items-baseline justify-between">
                      <span className="text-xs text-text-muted">进度</span>
                      <div className="text-sm text-text-secondary">
                        <span className="font-semibold text-primary">{lvl.learned}</span>
                        <span className="text-text-muted"> / {lvl.total}</span>
                      </div>
                    </div>
                    <div className="h-1.5 bg-border rounded-full overflow-hidden">
                      <motion.div
                        initial={{ width: 0 }}
                        animate={{ width: `${pct}%` }}
                        transition={{ duration: 0.4, ease: 'easeOut' }}
                        className="h-full bg-success"
                      />
                    </div>
                  </div>

                  <Link
                    to={`/ai-tools/hanzi/levels/${lvl.id}`}
                    className="mt-auto inline-flex items-center justify-center gap-1.5 h-11 rounded-[var(--radius-sm)] bg-primary text-text-on-primary text-sm font-semibold hover:bg-primary-hover transition-colors group cursor-pointer"
                  >
                    {started ? '继续学习' : '开始学习'}
                    <ArrowRight
                      size={14}
                      className="group-hover:translate-x-0.5 transition-transform"
                    />
                  </Link>
                </motion.div>
              )
            })}
        </div>
      )}
    </div>
  )
}
