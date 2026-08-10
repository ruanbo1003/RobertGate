import { useState } from 'react'
import { motion } from 'framer-motion'
import { Languages, Wand2, Sparkles, Copy, Check, AlertCircle } from 'lucide-react'
import { grammar, native, translate } from '../../services/aiTools'
import type { TranslateAction, TranslateResponse } from '../../types/aiTools'

const actionFns: Record<TranslateAction, (text: string) => ReturnType<typeof translate>> = {
  translate,
  grammar,
  native,
}

const actions: { key: TranslateAction; label: string; icon: typeof Languages }[] = [
  { key: 'translate', label: '翻译', icon: Languages },
  { key: 'grammar', label: '语法修正', icon: Wand2 },
  { key: 'native', label: '改地道', icon: Sparkles },
]

const actionLabel: Record<TranslateAction, string> = {
  translate: '翻译',
  grammar: '语法修正',
  native: '改地道',
}

export default function TranslatePage() {
  const [text, setText] = useState('')
  const [loading, setLoading] = useState<TranslateAction | null>(null)
  const [result, setResult] = useState<TranslateResponse | null>(null)
  const [lastAction, setLastAction] = useState<TranslateAction | null>(null)
  const [error, setError] = useState('')
  const [copied, setCopied] = useState(false)

  const disabled = !text.trim() || loading !== null

  const handleAction = async (action: TranslateAction) => {
    setLoading(action)
    setError('')
    const res = await actionFns[action](text)
    setLoading(null)
    if (res.code === 0) {
      setResult(res.data)
      setLastAction(action)
      setCopied(false)
    } else {
      setError(res.message || '请求失败')
    }
  }

  const handleCopy = async () => {
    if (!result) return
    await navigator.clipboard.writeText(result.result)
    setCopied(true)
    setTimeout(() => setCopied(false), 2000)
  }

  return (
    <div className="max-w-3xl mx-auto flex flex-col gap-6">
      {/* 输入 */}
      <div className="bg-card border border-border rounded-[var(--radius-lg)] p-4 shadow-sm">
        <textarea
          value={text}
          onChange={(e) => setText(e.target.value)}
          placeholder="在此输入中文或英文……"
          rows={6}
          className="w-full resize-y font-sans text-base text-text-primary placeholder:text-text-muted bg-transparent focus:outline-none min-h-[144px]"
        />
      </div>

      {/* 动作按钮组 */}
      <div className="flex flex-wrap gap-3">
        {actions.map(({ key, label, icon: Icon }) => {
          const isLoading = loading === key
          return (
            <motion.button
              key={key}
              onClick={() => handleAction(key)}
              disabled={disabled}
              whileHover={disabled ? undefined : { scale: 1.01 }}
              whileTap={disabled ? undefined : { scale: 0.98 }}
              className="flex items-center gap-2 h-11 px-5 bg-primary text-text-on-primary text-sm font-semibold rounded-[var(--radius-sm)] transition-colors hover:bg-primary-hover disabled:opacity-50 disabled:cursor-not-allowed cursor-pointer"
            >
              {isLoading ? (
                <div className="w-4 h-4 border-2 border-white/30 border-t-white rounded-full animate-spin" />
              ) : (
                <Icon size={16} />
              )}
              {label}
            </motion.button>
          )
        })}
      </div>

      {/* 错误态 */}
      {error && (
        <div className="flex items-start gap-2 p-4 bg-error-light border border-error/20 rounded-[var(--radius-sm)] text-error">
          <AlertCircle size={16} className="shrink-0 mt-0.5" />
          <div className="flex-1 text-sm">{error}</div>
          <button
            onClick={() => text && loading === null && result === null && handleAction('translate')}
            className="text-sm font-semibold underline cursor-pointer"
          >
            重试
          </button>
        </div>
      )}

      {/* 结果卡 */}
      {result && (
        <motion.div
          key={result.result}
          initial={{ opacity: 0, y: 8 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.2 }}
          className="bg-card border border-border rounded-[var(--radius-lg)] shadow-sm overflow-hidden"
        >
          <div className="flex items-center justify-between px-5 py-3 border-b border-border">
            <div className="flex items-center gap-2">
              <span className="text-xs font-semibold uppercase tracking-wider text-primary bg-primary-light px-2 py-0.5 rounded-[var(--radius-sm)]">
                {lastAction ? actionLabel[lastAction] : ''}
              </span>
              <span className="text-xs text-text-muted">
                {result.source_lang} → {result.target_lang}
              </span>
            </div>
            <button
              onClick={handleCopy}
              className="flex items-center gap-1.5 text-sm text-text-secondary hover:text-primary transition-colors cursor-pointer"
            >
              {copied ? (
                <>
                  <Check size={14} className="text-success" />
                  <span className="text-success">已复制</span>
                </>
              ) : (
                <>
                  <Copy size={14} />
                  <span>复制</span>
                </>
              )}
            </button>
          </div>
          <div className="p-5 font-sans text-base text-text-primary whitespace-pre-wrap leading-relaxed">
            {result.result}
          </div>
        </motion.div>
      )}

      {/* 空态 */}
      {!result && !error && !text && (
        <div className="text-center py-8 text-text-muted text-sm">
          输入文本后，点击上方按钮开始
        </div>
      )}
    </div>
  )
}
