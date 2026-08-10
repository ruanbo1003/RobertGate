import { useEffect, useMemo, useState } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { RefreshCw, Volume2, Check, PartyPopper } from 'lucide-react'
import { Link } from 'react-router-dom'
import type { HanziCharacter } from '../../types/hanzi'
import { speak } from '../../utils/tts'

interface Props {
  characters: HanziCharacter[]
  onToggle: (c: HanziCharacter) => Promise<void> | void
}

function pickRandom<T>(list: T[], exclude?: T): T | null {
  const pool = exclude ? list.filter((x) => x !== exclude) : list
  const source = pool.length > 0 ? pool : list
  if (source.length === 0) return null
  return source[Math.floor(Math.random() * source.length)]
}

export default function HanziRandomTab({ characters, onToggle }: Props) {
  const unlearned = useMemo(() => characters.filter((c) => !c.learned), [characters])
  const learnedCount = characters.length - unlearned.length

  const [current, setCurrent] = useState<HanziCharacter | null>(null)
  const [justLearned, setJustLearned] = useState(false)

  useEffect(() => {
    if (!current && unlearned.length > 0) {
      setCurrent(pickRandom(unlearned))
    } else if (current && current.learned) {
      setCurrent(pickRandom(unlearned))
    }
  }, [unlearned, current])

  const shuffle = () => {
    setCurrent(pickRandom(unlearned, current ?? undefined))
  }

  const handleLearned = async () => {
    if (!current || justLearned) return
    setJustLearned(true)
    await onToggle(current)
    setTimeout(() => {
      setJustLearned(false)
      setCurrent(pickRandom(unlearned.filter((c) => c.id !== current.id)))
    }, 400)
  }

  if (unlearned.length === 0) {
    return (
      <div className="bg-card border border-border rounded-[var(--radius-lg)] p-12 text-center flex flex-col items-center gap-3">
        <PartyPopper size={40} className="text-success" />
        <p className="text-lg font-semibold text-text-primary">这一级都学完啦！</p>
        <p className="text-sm text-text-muted">去挑战下一级吧</p>
        <Link
          to="/ai-tools/hanzi"
          className="mt-2 inline-flex items-center h-9 px-4 rounded-[var(--radius-sm)] text-sm font-semibold bg-primary text-text-on-primary hover:bg-primary-hover cursor-pointer transition-colors"
        >
          返回级别列表
        </Link>
      </div>
    )
  }

  if (!current) return null

  return (
    <div className="flex flex-col gap-6">
      <div className="flex items-center justify-between">
        <button
          onClick={shuffle}
          className="inline-flex items-center gap-1.5 h-9 px-3 rounded-[var(--radius-sm)] text-sm font-semibold text-text-secondary hover:bg-page cursor-pointer transition-colors"
        >
          <RefreshCw size={14} />
          换一个
        </button>
        <div className="text-sm text-text-muted">
          已学 <span className="font-semibold text-primary">{learnedCount}</span>
          <span className="text-text-muted"> / {characters.length}</span>
        </div>
      </div>

      <AnimatePresence mode="wait">
        <motion.div
          key={current.id}
          initial={{ opacity: 0, y: 8 }}
          animate={{ opacity: 1, y: 0 }}
          exit={{ opacity: 0, y: -8 }}
          transition={{ duration: 0.2 }}
          className="bg-card border border-border rounded-[var(--radius-lg)] shadow-sm p-8 flex flex-col items-center gap-4"
        >
          <div
            className="text-text-primary font-semibold leading-none select-none"
            style={{ fontSize: 200 }}
          >
            {current.char}
          </div>
          <div className="text-2xl text-text-muted">{current.pinyin}</div>
          <button
            onClick={() => speak(current.char)}
            className="inline-flex items-center gap-2 h-10 px-4 rounded-[var(--radius-sm)] text-sm font-semibold bg-primary/10 text-primary hover:bg-primary/20 cursor-pointer transition-colors"
          >
            <Volume2 size={16} />
            读这个字
          </button>
        </motion.div>
      </AnimatePresence>

      {current.example_words && current.example_words.length > 0 && (
        <div className="flex flex-col gap-2">
          <div className="text-sm font-semibold text-text-primary">例词</div>
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-2">
            {current.example_words.map((w) => (
              <button
                key={w}
                onClick={() => speak(w)}
                className="flex items-center justify-center gap-2 h-12 rounded-[var(--radius-sm)] bg-card border border-border text-text-primary text-base font-semibold hover:border-primary hover:text-primary cursor-pointer transition-colors"
              >
                <Volume2 size={14} />
                {w}
              </button>
            ))}
          </div>
        </div>
      )}

      <div className="flex justify-center">
        <button
          onClick={handleLearned}
          disabled={justLearned}
          className="inline-flex items-center gap-2 h-11 px-6 rounded-[var(--radius-sm)] text-sm font-semibold bg-success text-white hover:bg-success/90 cursor-pointer transition-colors disabled:opacity-70"
        >
          <Check size={16} />
          {justLearned ? '已标记，下一个…' : '标记为已学'}
        </button>
      </div>
    </div>
  )
}
