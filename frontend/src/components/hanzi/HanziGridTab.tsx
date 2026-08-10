import { motion } from 'framer-motion'
import { Check } from 'lucide-react'
import type { HanziCharacter } from '../../types/hanzi'

interface Props {
  characters: HanziCharacter[]
  onToggle: (c: HanziCharacter) => void
  savingId: string | null
}

export default function HanziGridTab({ characters, onToggle, savingId }: Props) {
  if (characters.length === 0) {
    return (
      <div className="bg-card border border-border rounded-[var(--radius-lg)] p-12 text-center">
        <div className="text-4xl mb-3">📝</div>
        <p className="text-sm text-text-muted">该级别暂无字条</p>
      </div>
    )
  }

  return (
    <>
      <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-5 xl:grid-cols-6 gap-3">
        {[...characters]
          .sort((a, b) => a.order_index - b.order_index)
          .map((c) => (
            <motion.button
              key={c.id}
              onClick={() => onToggle(c)}
              disabled={savingId === c.id}
              whileHover={{ y: -2 }}
              whileTap={{ scale: 0.98 }}
              transition={{ duration: 0.15 }}
              className={`relative flex flex-col items-center gap-1 p-4 rounded-[var(--radius-lg)] border transition-all cursor-pointer text-left disabled:opacity-70 ${
                c.learned
                  ? 'bg-success-light border-success/30'
                  : 'bg-card border-border hover:border-primary'
              }`}
            >
              {c.learned && (
                <div className="absolute top-1.5 right-1.5 w-5 h-5 rounded-full bg-success flex items-center justify-center">
                  <Check size={12} className="text-white" strokeWidth={3} />
                </div>
              )}
              <div
                className={`text-4xl font-semibold leading-none ${
                  c.learned ? 'text-success' : 'text-text-primary'
                }`}
              >
                {c.char}
              </div>
              <div className="text-sm text-text-muted">{c.pinyin}</div>
              {c.example_words && c.example_words.length > 0 && (
                <div
                  className="text-xs text-text-muted text-center leading-snug line-clamp-2 w-full"
                  title={c.example_words.join('、')}
                >
                  {c.example_words.join('、')}
                </div>
              )}
            </motion.button>
          ))}
      </div>
      <p className="text-xs text-text-muted text-center">
        点击字条切换「已学 / 未学」· 已学字条会加上对勾并高亮
      </p>
    </>
  )
}
