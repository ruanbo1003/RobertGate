import { useEffect, useState } from 'react'
import { Link, useParams, useSearchParams } from 'react-router-dom'
import { motion } from 'framer-motion'
import { ChevronLeft } from 'lucide-react'
import HanziGridTab from '../../components/hanzi/HanziGridTab'
import HanziRandomTab from '../../components/hanzi/HanziRandomTab'
import HanziPracticeTab from '../../components/hanzi/HanziPracticeTab'
import { getLevelCharacters, updateProgress } from '../../services/hanzi'
import type { HanziCharacter, HanziLevelSummary } from '../../types/hanzi'

type TabKey = 'grid' | 'random' | 'practice'
const TABS: { key: TabKey; label: string }[] = [
  { key: 'grid', label: '字表' },
  { key: 'random', label: '随机学习' },
  { key: 'practice', label: '组合练习' },
]

export default function HanziCharacterGridPage() {
  const { levelId = '' } = useParams()
  const [searchParams, setSearchParams] = useSearchParams()
  const rawTab = searchParams.get('tab')
  const activeTab: TabKey =
    rawTab === 'random' || rawTab === 'practice' ? rawTab : 'grid'

  const [level, setLevel] = useState<HanziLevelSummary | null>(null)
  const [chars, setChars] = useState<HanziCharacter[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [savingId, setSavingId] = useState<string | null>(null)

  useEffect(() => {
    let mounted = true
    setLoading(true)
    getLevelCharacters(levelId).then((res) => {
      if (!mounted) return
      if (res.code === 0 && res.data) {
        setLevel(res.data.level)
        setChars(res.data.characters)
        setError(null)
      } else {
        setError(res.message)
      }
      setLoading(false)
    })
    return () => {
      mounted = false
    }
  }, [levelId])

  const setActiveTab = (t: TabKey) => {
    const next = new URLSearchParams(searchParams)
    if (t === 'grid') next.delete('tab')
    else next.set('tab', t)
    setSearchParams(next, { replace: true })
  }

  const toggle = async (c: HanziCharacter) => {
    if (savingId) return
    const next = !c.learned
    const now = new Date().toISOString()
    setChars((cs) =>
      cs.map((x) =>
        x.id === c.id ? { ...x, learned: next, learned_at: next ? now : null } : x,
      ),
    )
    setSavingId(c.id)
    const res = await updateProgress(c.id, next)
    setSavingId(null)
    if (res.code !== 0) {
      setChars((cs) =>
        cs.map((x) =>
          x.id === c.id ? { ...x, learned: c.learned, learned_at: c.learned_at } : x,
        ),
      )
      alert(res.message)
    } else if (res.data) {
      setChars((cs) =>
        cs.map((x) =>
          x.id === c.id
            ? { ...x, learned: res.data!.learned, learned_at: res.data!.learned_at }
            : x,
        ),
      )
    }
  }

  const learnedCount = chars.filter((c) => c.learned).length
  const total = chars.length
  const pct = total > 0 ? Math.round((learnedCount / total) * 100) : 0

  if (loading) {
    return (
      <div className="max-w-6xl mx-auto flex flex-col gap-6">
        <div className="h-24 bg-card border border-border rounded-[var(--radius-lg)] animate-pulse" />
        <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-5 xl:grid-cols-6 gap-3">
          {Array.from({ length: 12 }).map((_, i) => (
            <div
              key={i}
              className="h-28 bg-card border border-border rounded-[var(--radius-lg)] animate-pulse"
            />
          ))}
        </div>
      </div>
    )
  }

  if (error || !level) {
    return (
      <div className="max-w-5xl mx-auto text-center py-12">
        <p className="text-sm text-text-muted">{error ?? '级别不存在'}</p>
        <Link
          to="/ai-tools/hanzi"
          className="text-sm text-primary hover:text-primary-hover cursor-pointer font-medium mt-2 inline-block"
        >
          返回级别列表
        </Link>
      </div>
    )
  }

  return (
    <div className="max-w-6xl mx-auto flex flex-col gap-6">
      <div>
        <Link
          to="/ai-tools/hanzi"
          className="inline-flex items-center gap-1 text-xs text-text-muted hover:text-primary transition-colors mb-1.5 cursor-pointer"
        >
          <ChevronLeft size={12} />
          返回级别列表
        </Link>
        <h1 className="text-2xl font-bold text-text-primary tracking-tight">{level.name}</h1>
        {level.description && (
          <p className="text-sm text-text-muted mt-1">{level.description}</p>
        )}
      </div>

      <div className="bg-card border border-border rounded-[var(--radius-lg)] p-5 shadow-sm">
        <div className="flex items-baseline justify-between mb-2">
          <span className="text-sm font-semibold text-text-primary">学习进度</span>
          <div className="text-sm text-text-secondary">
            <span className="font-bold text-primary text-lg">{learnedCount}</span>
            <span className="text-text-muted"> / {total} 字 · {pct}%</span>
          </div>
        </div>
        <div className="h-2 bg-border rounded-full overflow-hidden">
          <motion.div
            initial={{ width: 0 }}
            animate={{ width: `${pct}%` }}
            transition={{ duration: 0.4, ease: 'easeOut' }}
            className="h-full bg-success"
          />
        </div>
      </div>

      <div className="flex items-center gap-1 border-b border-border">
        {TABS.map((t) => (
          <button
            key={t.key}
            onClick={() => setActiveTab(t.key)}
            className={`relative px-4 h-10 text-sm font-semibold cursor-pointer transition-colors ${
              activeTab === t.key
                ? 'text-primary'
                : 'text-text-muted hover:text-text-primary'
            }`}
          >
            {t.label}
            {activeTab === t.key && (
              <span className="absolute -bottom-px left-0 right-0 h-0.5 bg-primary" />
            )}
          </button>
        ))}
      </div>

      {activeTab === 'grid' && (
        <HanziGridTab characters={chars} onToggle={toggle} savingId={savingId} />
      )}
      {activeTab === 'random' && (
        <HanziRandomTab characters={chars} onToggle={toggle} />
      )}
      {activeTab === 'practice' && (
        <HanziPracticeTab levelId={levelId} learnedCount={learnedCount} />
      )}
    </div>
  )
}
