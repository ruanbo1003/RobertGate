import { useState } from 'react'
import { motion } from 'framer-motion'
import { Sparkles, Download, RefreshCw, AlertCircle } from 'lucide-react'
import { textToImage } from '../../services/aiTools'
import type { Text2ImageResponse } from '../../types/aiTools'

export default function Text2ImagePage() {
  const [prompt, setPrompt] = useState('')
  const [loading, setLoading] = useState(false)
  const [result, setResult] = useState<Text2ImageResponse | null>(null)
  const [error, setError] = useState('')

  const handleGenerate = async () => {
    if (!prompt.trim()) return
    setLoading(true)
    setError('')
    const res = await textToImage(prompt)
    setLoading(false)
    if (res.code === 0) {
      setResult(res.data)
    } else {
      setError(res.message)
    }
  }

  const handleDownload = () => {
    if (!result) return
    const a = document.createElement('a')
    a.href = result.image_url
    a.download = `t2i-${Date.now()}.png`
    a.target = '_blank'
    a.rel = 'noopener'
    a.click()
  }

  return (
    <div className="max-w-3xl mx-auto flex flex-col gap-6">
      {/* Prompt 输入 */}
      <div className="bg-card border border-border rounded-[var(--radius-lg)] p-4 shadow-sm">
        <textarea
          value={prompt}
          onChange={(e) => setPrompt(e.target.value)}
          placeholder="描述你想要的图片，例如：a watercolor cat sitting by a window..."
          rows={4}
          className="w-full resize-y font-sans text-base text-text-primary placeholder:text-text-muted bg-transparent focus:outline-none"
        />
        <div className="flex items-center justify-end mt-3 pt-3 border-t border-border">
          <motion.button
            onClick={handleGenerate}
            disabled={!prompt.trim() || loading}
            whileHover={!prompt.trim() || loading ? undefined : { scale: 1.01 }}
            whileTap={!prompt.trim() || loading ? undefined : { scale: 0.98 }}
            className="flex items-center gap-1.5 h-11 px-6 bg-primary text-text-on-primary text-sm font-semibold rounded-[var(--radius-sm)] hover:bg-primary-hover transition-colors disabled:opacity-50 disabled:cursor-not-allowed cursor-pointer"
          >
            {loading ? (
              <>
                <div className="w-4 h-4 border-2 border-white/30 border-t-white rounded-full animate-spin" />
                生成中...
              </>
            ) : (
              <>
                <Sparkles size={16} />
                生成
              </>
            )}
          </motion.button>
        </div>
      </div>

      {/* 错误 */}
      {error && (
        <div className="flex items-start gap-2 p-4 bg-error-light border border-error/20 rounded-[var(--radius-sm)] text-error">
          <AlertCircle size={16} className="shrink-0 mt-0.5" />
          <div className="flex-1 text-sm">{error}</div>
          <button
            onClick={handleGenerate}
            className="text-sm font-semibold underline cursor-pointer"
          >
            重试
          </button>
        </div>
      )}

      {/* 结果 */}
      {loading && !result && (
        <div className="mx-auto w-full max-w-[768px] aspect-square rounded-[var(--radius-lg)] border border-border bg-card flex items-center justify-center">
          <div className="flex flex-col items-center gap-3 text-text-muted">
            <div className="w-8 h-8 border-2 border-primary/30 border-t-primary rounded-full animate-spin" />
            <span className="text-sm">生成中，通常需要几秒……</span>
          </div>
        </div>
      )}

      {result && !loading && (
        <motion.div
          key={result.image_url}
          initial={{ opacity: 0, y: 8 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.3 }}
          className="flex flex-col items-center gap-4"
        >
          <div className="w-full max-w-[768px] rounded-[var(--radius-lg)] overflow-hidden border border-border bg-card shadow-sm">
            <img src={result.image_url} alt={result.prompt} className="w-full h-auto block" />
          </div>
          <div className="flex items-center gap-3">
            <button
              onClick={handleDownload}
              className="flex items-center gap-1.5 h-10 px-4 border border-border text-sm font-semibold text-text-secondary rounded-[var(--radius-sm)] hover:border-primary hover:text-primary transition-colors cursor-pointer"
            >
              <Download size={14} />
              下载
            </button>
            <motion.button
              onClick={handleGenerate}
              whileHover={{ scale: 1.01 }}
              whileTap={{ scale: 0.98 }}
              className="flex items-center gap-1.5 h-10 px-4 bg-primary text-text-on-primary text-sm font-semibold rounded-[var(--radius-sm)] hover:bg-primary-hover transition-colors cursor-pointer"
            >
              <RefreshCw size={14} />
              再生成
            </motion.button>
          </div>
        </motion.div>
      )}
    </div>
  )
}
