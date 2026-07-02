import { useEffect, useMemo, useState } from 'react'
import { useSearchParams } from 'react-router-dom'
import { motion } from 'framer-motion'
import { Check, ChevronLeft, SkipForward, Volume2 } from 'lucide-react'
import { getCharacterInfo, getHanziLibrary, updateHanzi } from '../../services/aiTools'
import type { CharacterInfoResponse, HanziItem } from '../../types/aiTools'
import { useSpeech } from '../../hooks/useSpeech'

export default function HanziLearnPage() {
  const [params] = useSearchParams()
  const initialChar = params.get('char')

  const [items, setItems] = useState<HanziItem[]>([])
  const [index, setIndex] = useState(0)
  const [info, setInfo] = useState<CharacterInfoResponse | null>(null)
  const [infoLoading, setInfoLoading] = useState(false)
  const { speak, supported: ttsSupported } = useSpeech()

  useEffect(() => {
    void (async () => {
      const res = await getHanziLibrary()
      if (res.code === 0) {
        setItems(res.data.items)
        if (initialChar) {
          const i = res.data.items.findIndex((it) => it.char === initialChar)
          if (i >= 0) setIndex(i)
        } else {
          const firstUnlearned = res.data.items.findIndex((it) => !it.learned)
          if (firstUnlearned >= 0) setIndex(firstUnlearned)
        }
      }
    })()
  }, [initialChar])

  const current = items[index]

  useEffect(() => {
    if (!current) return
    setInfoLoading(true)
    setInfo(null)
    void getCharacterInfo(current.char).then((res) => {
      if (res.code === 0) setInfo(res.data)
      setInfoLoading(false)
    })
  }, [current])

  const allLearned = useMemo(() => items.length > 0 && items.every((i) => i.learned), [items])

  const goPrev = () => setIndex((i) => Math.max(0, i - 1))
  const goNext = () => setIndex((i) => Math.min(items.length - 1, i + 1))

  const markLearned = async () => {
    if (!current) return
    const res = await updateHanzi(current.char, true)
    if (res.code === 0) {
      setItems((prev) => prev.map((it) => (it.char === current.char ? { ...it, learned: true } : it)))
      // 自动下一未学
      const nextIdx = items.findIndex((it, i) => i > index && !it.learned)
      if (nextIdx >= 0) setIndex(nextIdx)
    }
  }

  if (items.length === 0) {
    return (
      <div className="max-w-2xl mx-auto text-center py-16">
        <div className="text-6xl mb-4">📚</div>
        <h2 className="font-sans text-xl font-bold text-text-primary mb-2">字库还没有字</h2>
        <p className="text-sm text-text-muted mb-4">先去字库添加一些汉字吧</p>
        <a
          href="/ai-tools/hanzi/library"
          className="inline-flex items-center gap-1.5 h-10 px-5 bg-primary text-text-on-primary text-sm font-semibold rounded-[var(--radius-sm)] hover:bg-primary-hover transition-colors"
        >
          去字库
        </a>
      </div>
    )
  }

  if (allLearned) {
    return (
      <div className="max-w-2xl mx-auto text-center py-16">
        <div className="text-6xl mb-4">🎉</div>
        <h2 className="font-sans text-xl font-bold text-text-primary mb-2">全部字已学完</h2>
        <p className="text-sm text-text-muted">去句子学习复习一下吧</p>
      </div>
    )
  }

  if (!current) return null

  return (
    <div className="max-w-2xl mx-auto flex flex-col gap-6">
      {/* 字卡 */}
      <div className="bg-card border border-border rounded-[var(--radius-lg)] shadow-sm overflow-hidden">
        <div className="bg-page-alt border-b border-border h-56 flex items-center justify-center">
          <span
            className="font-sans font-bold text-text-primary select-none"
            style={{ fontSize: 160, lineHeight: 1 }}
          >
            {current.char}
          </span>
        </div>

        {/* 信息区 */}
        <div className="p-6 flex flex-col gap-4">
          <div className="text-xs text-text-muted">
            第 {index + 1} / {items.length} 字
          </div>
          {infoLoading || !info ? (
            <div className="flex justify-center py-6">
              <div className="w-5 h-5 border-2 border-primary/30 border-t-primary rounded-full animate-spin" />
            </div>
          ) : (
            <>
              <div className="flex items-center gap-3">
                <span className="text-xs font-semibold uppercase tracking-wider text-text-muted">拼音</span>
                <span className="font-sans text-lg font-semibold text-primary">{info.pinyin}</span>
                {ttsSupported && (
                  <button
                    onClick={() => speak(current.char, 'zh-CN')}
                    className="text-text-secondary hover:text-primary transition-colors cursor-pointer"
                  >
                    <Volume2 size={16} />
                  </button>
                )}
              </div>
              <div>
                <div className="text-xs font-semibold uppercase tracking-wider text-text-muted mb-1">组词</div>
                <div className="flex flex-wrap gap-2">
                  {info.words.map((w) => (
                    <span key={w} className="px-2.5 py-1 bg-page rounded-[var(--radius-sm)] text-sm text-text-primary">
                      {w}
                    </span>
                  ))}
                </div>
              </div>
              <div>
                <div className="text-xs font-semibold uppercase tracking-wider text-text-muted mb-1">例句</div>
                <div className="text-sm text-text-primary leading-relaxed">{info.sentence}</div>
              </div>
            </>
          )}
        </div>
      </div>

      {/* 操作 */}
      <div className="flex items-center justify-between gap-3">
        <button
          onClick={goPrev}
          disabled={index === 0}
          className="flex items-center gap-1.5 h-11 px-5 border border-border text-sm font-semibold text-text-secondary rounded-[var(--radius-sm)] hover:border-primary hover:text-primary transition-colors disabled:opacity-40 disabled:cursor-not-allowed cursor-pointer"
        >
          <ChevronLeft size={16} />
          上一个
        </button>
        <button
          onClick={goNext}
          disabled={index >= items.length - 1}
          className="flex items-center gap-1.5 h-11 px-5 border border-border text-sm font-semibold text-text-secondary rounded-[var(--radius-sm)] hover:border-primary hover:text-primary transition-colors disabled:opacity-40 disabled:cursor-not-allowed cursor-pointer"
        >
          <SkipForward size={16} />
          跳过
        </button>
        <motion.button
          onClick={markLearned}
          whileHover={{ scale: 1.01 }}
          whileTap={{ scale: 0.98 }}
          className="flex items-center gap-1.5 h-11 px-5 bg-success text-white text-sm font-semibold rounded-[var(--radius-sm)] transition-colors cursor-pointer"
        >
          <Check size={16} />
          已学完
        </motion.button>
      </div>
    </div>
  )
}
