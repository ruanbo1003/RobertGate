import { useEffect, useState } from 'react'
import { motion } from 'framer-motion'
import { RefreshCw, Volume2 } from 'lucide-react'
import { getHanziLibrary, getSentence } from '../../services/aiTools'
import type { SentenceResponse } from '../../types/aiTools'
import { useSpeech } from '../../hooks/useSpeech'

export default function HanziSentencePage() {
  const [knownChars, setKnownChars] = useState<string[]>([])
  const [sentence, setSentence] = useState<SentenceResponse | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [libraryReady, setLibraryReady] = useState(false)
  const { speak, supported: ttsSupported } = useSpeech()

  const fetchSentence = async (chars: string[]) => {
    setLoading(true)
    setError('')
    const res = await getSentence(chars)
    setLoading(false)
    if (res.code === 0) {
      setSentence(res.data)
    } else {
      setError(res.message)
    }
  }

  useEffect(() => {
    void (async () => {
      const res = await getHanziLibrary()
      if (res.code === 0) {
        const learned = res.data.items.filter((i) => i.learned).map((i) => i.char)
        setKnownChars(learned)
        setLibraryReady(true)
        if (learned.length >= 5) await fetchSentence(learned)
        else setLoading(false)
      }
    })()
  }, [])

  if (!libraryReady || loading) {
    return (
      <div className="flex justify-center py-16">
        <div className="w-6 h-6 border-2 border-primary/30 border-t-primary rounded-full animate-spin" />
      </div>
    )
  }

  if (knownChars.length < 5) {
    return (
      <div className="max-w-2xl mx-auto text-center py-16">
        <div className="text-6xl mb-4">📖</div>
        <h2 className="font-sans text-xl font-bold text-text-primary mb-2">先学几个字再来组句</h2>
        <p className="text-sm text-text-muted mb-4">
          目前已学 {knownChars.length} 字，至少需要 5 字
        </p>
        <a
          href="/ai-tools/hanzi/learn"
          className="inline-flex items-center gap-1.5 h-10 px-5 bg-primary text-text-on-primary text-sm font-semibold rounded-[var(--radius-sm)] hover:bg-primary-hover transition-colors"
        >
          去学字
        </a>
      </div>
    )
  }

  if (error) {
    return (
      <div className="max-w-2xl mx-auto text-center py-16">
        <p className="text-sm text-error mb-4">{error}</p>
        <button
          onClick={() => fetchSentence(knownChars)}
          className="h-10 px-5 bg-primary text-text-on-primary text-sm font-semibold rounded-[var(--radius-sm)] hover:bg-primary-hover transition-colors cursor-pointer"
        >
          重试
        </button>
      </div>
    )
  }

  if (!sentence) return null

  const known = new Set(knownChars)
  const chars = Array.from(sentence.sentence.replace(/[。！？，、]/g, ''))
  const pinyins = sentence.pinyin.split(/\s+/)

  return (
    <div className="max-w-2xl mx-auto flex flex-col gap-6">
      <motion.div
        key={sentence.sentence}
        initial={{ opacity: 0, y: 8 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.3 }}
        className="bg-card border border-border rounded-[var(--radius-lg)] shadow-sm p-6 flex flex-col gap-5"
      >
        {/* 句子（含拼音注音） */}
        <div className="flex flex-wrap gap-x-2 gap-y-3 justify-center py-4">
          {chars.map((c, i) => {
            const isOutOfVocab = /[\u4e00-\u9fa5]/.test(c) && !known.has(c)
            return (
              <div key={i} className="flex flex-col items-center gap-1 min-w-[2rem]">
                <span className="text-xs text-text-muted font-mono">{pinyins[i] ?? ''}</span>
                <span
                  className={`text-3xl font-semibold ${
                    isOutOfVocab ? 'text-error' : 'text-text-primary'
                  }`}
                >
                  {c}
                </span>
              </div>
            )
          })}
        </div>

        <div className="border-t border-border pt-4">
          <div className="text-xs font-semibold uppercase tracking-wider text-text-muted mb-1">
            中文含义
          </div>
          <div className="text-sm text-text-secondary leading-relaxed">
            {sentence.translation}
          </div>
        </div>

        {sentence.out_of_vocab.length > 0 && (
          <div className="text-xs text-error">
            库外字（红色标注）：{sentence.out_of_vocab.join('、')}
          </div>
        )}

        <div className="flex items-center gap-3 pt-2">
          {ttsSupported && (
            <button
              onClick={() => speak(sentence.sentence, 'zh-CN')}
              className="flex items-center gap-1.5 h-10 px-4 border border-border text-sm font-semibold text-text-secondary rounded-[var(--radius-sm)] hover:border-primary hover:text-primary transition-colors cursor-pointer"
            >
              <Volume2 size={14} />
              朗读
            </button>
          )}
          <motion.button
            onClick={() => fetchSentence(knownChars)}
            whileHover={{ scale: 1.01 }}
            whileTap={{ scale: 0.98 }}
            className="flex items-center gap-1.5 h-10 px-4 bg-primary text-text-on-primary text-sm font-semibold rounded-[var(--radius-sm)] hover:bg-primary-hover transition-colors cursor-pointer"
          >
            <RefreshCw size={14} />
            换一句
          </motion.button>
        </div>
      </motion.div>
    </div>
  )
}
