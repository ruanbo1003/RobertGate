import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { motion } from 'framer-motion'
import { getEnglishThemes } from '../../services/aiTools'
import type { EnglishTheme } from '../../types/aiTools'

export default function EnglishThemesPage() {
  const navigate = useNavigate()
  const [themes, setThemes] = useState<EnglishTheme[]>([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    void getEnglishThemes().then((res) => {
      if (res.code === 0) setThemes(res.data.themes)
      setLoading(false)
    })
  }, [])

  return (
    <div className="max-w-4xl mx-auto flex flex-col gap-6">
      {loading ? (
        <div className="flex justify-center py-16">
          <div className="w-6 h-6 border-2 border-primary/30 border-t-primary rounded-full animate-spin" />
        </div>
      ) : (
        <div className="grid grid-cols-2 gap-4">
          {themes.map((theme) => (
            <motion.button
              key={theme.id}
              onClick={() => theme.ready && navigate(`/ai-tools/english/quiz?theme=${theme.id}`)}
              disabled={!theme.ready}
              whileHover={theme.ready ? { scale: 1.02, y: -2 } : undefined}
              whileTap={theme.ready ? { scale: 0.99 } : undefined}
              className={`bg-card border border-border rounded-[var(--radius-lg)] p-8 shadow-sm text-left transition-shadow cursor-pointer disabled:cursor-not-allowed disabled:opacity-60 ${
                theme.ready ? 'hover:shadow-md' : ''
              }`}
            >
              <div className="text-5xl mb-4">{theme.emoji}</div>
              <div className="font-sans text-xl font-bold text-text-primary mb-1">
                {theme.name_en}
              </div>
              <div className="font-sans text-sm text-text-muted">
                {theme.name_zh}
              </div>
              {!theme.ready && (
                <div className="mt-3 inline-block px-2 py-0.5 bg-warning-light text-warning text-xs font-semibold rounded-[var(--radius-sm)]">
                  准备中
                </div>
              )}
              {theme.ready && (
                <div className="mt-3 text-xs text-text-muted">
                  {theme.words.length} 个单词
                </div>
              )}
            </motion.button>
          ))}
        </div>
      )}
    </div>
  )
}
