import { useEffect, useMemo, useState } from 'react'
import { useNavigate, useSearchParams } from 'react-router-dom'
import { motion, AnimatePresence } from 'framer-motion'
import { Check, X, Volume2, RefreshCw } from 'lucide-react'
import { getEnglishQuiz } from '../../services/aiTools'
import type { QuizQuestion } from '../../types/aiTools'
import { useSpeech } from '../../hooks/useSpeech'

export default function EnglishQuizPage() {
  const navigate = useNavigate()
  const [params] = useSearchParams()
  const themeId = params.get('theme')
  const [questions, setQuestions] = useState<QuizQuestion[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [index, setIndex] = useState(0)
  const [score, setScore] = useState(0)
  const [pickedWrong, setPickedWrong] = useState<Set<number>>(new Set())
  const [pickedRight, setPickedRight] = useState<number | null>(null)
  const [finished, setFinished] = useState(false)
  const { speak, supported: ttsSupported } = useSpeech()

  const loadQuiz = () => {
    if (!themeId) return
    setLoading(true)
    setIndex(0)
    setScore(0)
    setFinished(false)
    setPickedWrong(new Set())
    setPickedRight(null)
    void getEnglishQuiz(themeId, 10).then((res) => {
      setLoading(false)
      if (res.code === 0) setQuestions(res.data.questions)
      else setError(res.message)
    })
  }

  useEffect(() => {
    loadQuiz()
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [themeId])

  const current = questions[index]

  useEffect(() => {
    if (current && ttsSupported) speak(current.word, 'en-US')
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [current])

  const isPerfect = useMemo(() => score === questions.length && questions.length > 0, [score, questions.length])

  if (!themeId) {
    return (
      <div className="max-w-2xl mx-auto text-center py-16">
        <p className="text-sm text-text-muted mb-4">先选一个主题</p>
        <button
          onClick={() => navigate('/ai-tools/english/themes')}
          className="h-10 px-5 bg-primary text-text-on-primary text-sm font-semibold rounded-[var(--radius-sm)] hover:bg-primary-hover transition-colors cursor-pointer"
        >
          去选主题
        </button>
      </div>
    )
  }

  if (loading) {
    return (
      <div className="flex justify-center py-16">
        <div className="w-6 h-6 border-2 border-primary/30 border-t-primary rounded-full animate-spin" />
      </div>
    )
  }

  if (error) {
    return (
      <div className="max-w-2xl mx-auto text-center py-16">
        <p className="text-sm text-error mb-4">{error}</p>
        <button
          onClick={loadQuiz}
          className="h-10 px-5 bg-primary text-text-on-primary text-sm font-semibold rounded-[var(--radius-sm)] hover:bg-primary-hover transition-colors cursor-pointer"
        >
          重试
        </button>
      </div>
    )
  }

  if (finished) {
    return (
      <div className="max-w-2xl mx-auto text-center py-16">
        <div className="text-6xl mb-4">{isPerfect ? '🏆' : '🎉'}</div>
        <h2 className="font-sans text-2xl font-bold text-text-primary mb-2">
          得分 {score} / {questions.length}
        </h2>
        <p className="text-sm text-text-muted mb-6">
          {isPerfect ? '全对，太厉害了！' : '继续加油！'}
        </p>
        <div className="flex items-center justify-center gap-3">
          <motion.button
            onClick={loadQuiz}
            whileHover={{ scale: 1.01 }}
            whileTap={{ scale: 0.98 }}
            className="flex items-center gap-1.5 h-11 px-5 bg-primary text-text-on-primary text-sm font-semibold rounded-[var(--radius-sm)] hover:bg-primary-hover transition-colors cursor-pointer"
          >
            <RefreshCw size={14} />
            再来一轮
          </motion.button>
          <button
            onClick={() => navigate('/ai-tools/english/themes')}
            className="h-11 px-5 border border-border text-sm font-semibold text-text-secondary rounded-[var(--radius-sm)] hover:border-primary hover:text-primary transition-colors cursor-pointer"
          >
            换主题
          </button>
        </div>
      </div>
    )
  }

  if (!current) return null

  const handlePick = (idx: number) => {
    if (pickedRight !== null) return
    if (idx === current.correct_index) {
      setPickedRight(idx)
      // 只有本题没答错过才计分
      if (pickedWrong.size === 0) setScore((s) => s + 1)
      setTimeout(() => {
        if (index >= questions.length - 1) {
          setFinished(true)
        } else {
          setIndex((i) => i + 1)
          setPickedWrong(new Set())
          setPickedRight(null)
        }
      }, 800)
    } else {
      setPickedWrong((prev) => new Set(prev).add(idx))
    }
  }

  return (
    <div className="max-w-3xl mx-auto flex flex-col gap-6">
      {/* 计分 + 进度 */}
      <div className="flex items-center justify-between">
        <div className="text-sm text-text-muted">
          <span className="text-xs uppercase tracking-wider font-semibold text-text-muted mr-2">
            {themeId}
          </span>
        </div>
        <div className="flex items-center gap-3">
          <span className="text-sm font-semibold text-primary">
            {index + 1}/{questions.length}
          </span>
          <div className="w-32 h-1.5 bg-border rounded-full overflow-hidden">
            <motion.div
              className="h-full bg-primary"
              animate={{ width: `${((index + 1) / questions.length) * 100}%` }}
              transition={{ duration: 0.3 }}
            />
          </div>
        </div>
      </div>

      {/* 单词 */}
      <div className="text-center py-6">
        <div className="flex items-center justify-center gap-3">
          <span className="font-sans text-5xl font-extrabold text-text-primary tracking-tight">
            {current.word}
          </span>
          {ttsSupported && (
            <button
              onClick={() => speak(current.word, 'en-US')}
              className="w-12 h-12 flex items-center justify-center rounded-full bg-primary-light text-primary hover:bg-primary hover:text-white transition-colors cursor-pointer"
              aria-label="播放发音"
            >
              <Volume2 size={22} />
            </button>
          )}
        </div>
        <div className="text-sm text-text-muted mt-2">{current.translation}</div>
      </div>

      {/* 2×2 图片网格 */}
      <div className="grid grid-cols-2 gap-4 max-w-lg mx-auto w-full">
        {current.options.map((url, idx) => {
          const isWrong = pickedWrong.has(idx)
          const isRight = pickedRight === idx
          return (
            <motion.button
              key={idx}
              onClick={() => handlePick(idx)}
              whileHover={pickedRight === null && !isWrong ? { scale: 1.02 } : undefined}
              whileTap={pickedRight === null && !isWrong ? { scale: 0.98 } : undefined}
              disabled={isWrong || pickedRight !== null}
              className={`relative aspect-square rounded-[var(--radius-lg)] overflow-hidden border-2 transition-all cursor-pointer disabled:cursor-not-allowed ${
                isRight
                  ? 'border-success ring-4 ring-success/30'
                  : isWrong
                    ? 'border-error opacity-50'
                    : 'border-border hover:border-primary'
              }`}
            >
              <img src={url} alt="" className="w-full h-full object-cover" />
              <AnimatePresence>
                {isRight && (
                  <motion.div
                    initial={{ scale: 0 }}
                    animate={{ scale: 1 }}
                    className="absolute inset-0 flex items-center justify-center bg-success/40"
                  >
                    <div className="w-16 h-16 rounded-full bg-success flex items-center justify-center">
                      <Check size={36} className="text-white" strokeWidth={3} />
                    </div>
                  </motion.div>
                )}
                {isWrong && (
                  <motion.div
                    initial={{ scale: 0 }}
                    animate={{ scale: 1 }}
                    className="absolute inset-0 flex items-center justify-center bg-error/30"
                  >
                    <div className="w-16 h-16 rounded-full bg-error flex items-center justify-center">
                      <X size={36} className="text-white" strokeWidth={3} />
                    </div>
                  </motion.div>
                )}
              </AnimatePresence>
            </motion.button>
          )
        })}
      </div>
    </div>
  )
}
