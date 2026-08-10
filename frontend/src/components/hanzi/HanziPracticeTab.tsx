import { useEffect, useMemo, useState } from 'react'
import { RefreshCw, Volume2, Eye, EyeOff, Sparkles, Info } from 'lucide-react'
import type { PracticeTextResponse } from '../../types/hanzi'
import { getPracticeText } from '../../services/hanzi'
import { speak } from '../../utils/tts'

interface Props {
  levelId: string
  learnedCount: number
}

const MIN_LEARNED = 3

export default function HanziPracticeTab({ levelId, learnedCount }: Props) {
  const [data, setData] = useState<PracticeTextResponse | null>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [showPinyin, setShowPinyin] = useState(false)

  const enoughLearned = learnedCount >= MIN_LEARNED

  const load = async () => {
    setLoading(true)
    setError(null)
    const res = await getPracticeText(levelId)
    setLoading(false)
    if (res.code === 0 && res.data) {
      setData(res.data)
    } else {
      setError(res.message)
    }
  }

  useEffect(() => {
    if (enoughLearned && !data && !loading) {
      load()
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [enoughLearned, levelId])

  const pinyinMap = useMemo(() => {
    const m = new Map<string, string>()
    if (data) {
      for (const a of data.annotations) {
        if (!m.has(a.char)) m.set(a.char, a.pinyin)
      }
    }
    return m
  }, [data])

  const newCharSet = useMemo(
    () => new Set(data?.new_chars ?? []),
    [data],
  )

  if (!enoughLearned) {
    return (
      <div className="bg-card border border-border rounded-[var(--radius-lg)] p-10 text-center flex flex-col items-center gap-3">
        <Info size={32} className="text-primary" />
        <p className="text-base font-semibold text-text-primary">
          再学 {MIN_LEARNED - learnedCount} 个字就能来这里练习啦
        </p>
        <p className="text-sm text-text-muted">
          当前已学 <span className="font-semibold text-primary">{learnedCount}</span> · 需要至少 {MIN_LEARNED}
        </p>
      </div>
    )
  }

  return (
    <div className="flex flex-col gap-4">
      <div className="flex items-center justify-between gap-2 flex-wrap">
        <button
          onClick={() => setShowPinyin((v) => !v)}
          className="inline-flex items-center gap-1.5 h-9 px-3 rounded-[var(--radius-sm)] text-sm font-semibold text-text-secondary hover:bg-page cursor-pointer transition-colors"
        >
          {showPinyin ? <EyeOff size={14} /> : <Eye size={14} />}
          拼音：{showPinyin ? '显示' : '隐藏'}
        </button>
        <div className="flex items-center gap-2">
          <button
            onClick={() => data && speak(data.text)}
            disabled={!data}
            className="inline-flex items-center gap-1.5 h-9 px-3 rounded-[var(--radius-sm)] text-sm font-semibold text-primary hover:bg-primary/10 cursor-pointer transition-colors disabled:opacity-50"
          >
            <Volume2 size={14} />
            朗读全文
          </button>
          <button
            onClick={load}
            disabled={loading}
            className="inline-flex items-center gap-1.5 h-9 px-3 rounded-[var(--radius-sm)] text-sm font-semibold bg-primary text-text-on-primary hover:bg-primary-hover cursor-pointer transition-colors disabled:opacity-70"
          >
            <RefreshCw size={14} className={loading ? 'animate-spin' : ''} />
            换一段
          </button>
        </div>
      </div>

      {loading && !data && (
        <div className="bg-card border border-border rounded-[var(--radius-lg)] p-10 flex flex-col items-center gap-3">
          <Sparkles size={24} className="text-primary animate-pulse" />
          <p className="text-sm text-text-muted">AI 正在写句子…</p>
        </div>
      )}

      {error && !loading && (
        <div className="bg-card border border-error/30 rounded-[var(--radius-lg)] p-6 text-center">
          <p className="text-sm text-error">{error}</p>
          <button
            onClick={load}
            className="mt-3 text-sm text-primary hover:text-primary-hover cursor-pointer font-semibold"
          >
            重试
          </button>
        </div>
      )}

      {data && !loading && (
        <>
          <div className="bg-card border border-border rounded-[var(--radius-lg)] shadow-sm px-6 py-8">
            <p
              className="text-2xl text-text-primary"
              style={{ lineHeight: showPinyin ? 2.6 : 1.9 }}
            >
              {[...data.text].map((ch, idx) => {
                const isHanzi = /[\u4e00-\u9fa5]/.test(ch)
                const py = pinyinMap.get(ch)
                const isNew = newCharSet.has(ch)
                if (!isHanzi) return <span key={idx}>{ch}</span>
                const content = (
                  <span
                    className={
                      isNew
                        ? 'text-primary border-b border-dashed border-primary/50'
                        : ''
                    }
                    title={isNew && py ? `${ch} · ${py}` : undefined}
                  >
                    {ch}
                  </span>
                )
                if (showPinyin && py) {
                  return (
                    <ruby key={idx} className="mx-0.5">
                      {content}
                      <rt className="text-xs text-text-muted font-normal">{py}</rt>
                    </ruby>
                  )
                }
                return <span key={idx}>{content}</span>
              })}
            </p>
          </div>

          {data.new_chars.length > 0 && (
            <div className="flex items-start gap-3 text-sm">
              <span className="text-text-muted shrink-0 pt-0.5">新字：</span>
              <div className="flex flex-wrap gap-2">
                {data.new_chars.map((ch) => {
                  const py = pinyinMap.get(ch)
                  return (
                    <span
                      key={ch}
                      className="inline-flex items-baseline gap-1 px-2 py-1 rounded-[var(--radius-sm)] bg-primary/10 text-primary"
                    >
                      <span className="font-semibold">{ch}</span>
                      {py && <span className="text-xs text-text-muted">{py}</span>}
                    </span>
                  )
                })}
              </div>
            </div>
          )}
        </>
      )}
    </div>
  )
}
