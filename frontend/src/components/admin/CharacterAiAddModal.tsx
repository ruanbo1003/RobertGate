import { useState } from 'react'
import { CheckCircle2, AlertCircle, Sparkles } from 'lucide-react'
import Modal from '../ui/Modal'
import type { AiAddResponse } from '../../types/hanzi'

interface Props {
  open: boolean
  onClose: () => void
  onSubmit: (text: string) => Promise<AiAddResponse | null>
}

const HANZI_RE = /[\u4e00-\u9fa5]/g
const MAX_TEXT_LEN = 2000

function extractHanziPreview(text: string): string[] {
  const seen = new Set<string>()
  const out: string[] = []
  for (const ch of text.match(HANZI_RE) ?? []) {
    if (!seen.has(ch)) {
      seen.add(ch)
      out.push(ch)
    }
  }
  return out
}

export default function CharacterAiAddModal({ open, onClose, onSubmit }: Props) {
  const [text, setText] = useState('')
  const [submitting, setSubmitting] = useState(false)
  const [result, setResult] = useState<AiAddResponse | null>(null)

  const preview = extractHanziPreview(text)
  const tooLong = text.length > MAX_TEXT_LEN

  const handleSubmit = async () => {
    if (preview.length === 0 || tooLong || submitting) return
    setSubmitting(true)
    const r = await onSubmit(text)
    setSubmitting(false)
    if (r) setResult(r)
  }

  const handleClose = () => {
    if (submitting) return
    setText('')
    setResult(null)
    onClose()
  }

  return (
    <Modal
      open={open}
      onClose={handleClose}
      title="汉字添加"
      subtitle="粘贴任意文本，自动提取汉字并用 AI 生成拼音与例词"
      width={640}
      footer={
        result ? (
          <button
            onClick={handleClose}
            className="h-9 px-4 rounded-[var(--radius-sm)] text-sm font-semibold bg-primary text-text-on-primary hover:bg-primary-hover cursor-pointer transition-colors"
          >
            完成
          </button>
        ) : (
          <>
            <button
              onClick={handleClose}
              disabled={submitting}
              className="h-9 px-4 rounded-[var(--radius-sm)] text-sm font-semibold text-text-secondary hover:bg-page cursor-pointer transition-colors disabled:opacity-50"
            >
              取消
            </button>
            <button
              onClick={handleSubmit}
              disabled={preview.length === 0 || tooLong || submitting}
              className="h-9 px-4 rounded-[var(--radius-sm)] text-sm font-semibold bg-primary text-text-on-primary hover:bg-primary-hover cursor-pointer transition-colors disabled:opacity-50 disabled:cursor-not-allowed flex items-center gap-2"
            >
              {submitting ? (
                <>
                  <div className="w-3.5 h-3.5 border-2 border-white/30 border-t-white rounded-full animate-spin" />
                  正在生成…
                </>
              ) : (
                <>
                  <Sparkles size={14} />
                  添加 {preview.length > 0 ? `${preview.length} 字` : ''}
                </>
              )}
            </button>
          </>
        )
      }
    >
      {result ? (
        <div className="flex flex-col gap-4">
          <div className="flex items-center gap-3 p-4 bg-success-light rounded-[var(--radius-sm)]">
            <CheckCircle2 size={20} className="text-success" />
            <span className="text-sm text-text-primary">
              新增 <span className="font-semibold text-success">{result.ok}</span> 字
              {result.skipped.length > 0 && (
                <>
                  ，已存在 <span className="font-semibold text-text-primary">{result.skipped.length}</span> 字
                </>
              )}
              {result.failed.length > 0 && (
                <>
                  ，失败 <span className="font-semibold text-error">{result.failed.length}</span> 字
                </>
              )}
            </span>
          </div>

          {result.added.length > 0 && (
            <div className="border border-border rounded-[var(--radius-sm)] overflow-hidden">
              <div className="px-4 py-2.5 bg-page-alt text-[13px] font-semibold text-text-primary border-b border-border">
                新增明细
              </div>
              <div className="max-h-56 overflow-y-auto">
                {result.added.map((a) => (
                  <div
                    key={a.id}
                    className="flex items-start gap-3 px-4 py-2.5 text-sm border-b border-border last:border-b-0"
                  >
                    <span className="text-2xl font-semibold w-10 shrink-0 text-text-primary">{a.char}</span>
                    <div className="flex-1 min-w-0">
                      <div className="text-text-primary">{a.pinyin}</div>
                      <div className="text-text-muted text-xs truncate">
                        {a.example_words.join('、')}
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}

          {(result.skipped.length > 0 || result.failed.length > 0) && (
            <div className="border border-border rounded-[var(--radius-sm)] overflow-hidden">
              <div className="px-4 py-2.5 bg-page-alt text-[13px] font-semibold text-text-primary border-b border-border">
                跳过 / 失败
              </div>
              <div className="max-h-40 overflow-y-auto">
                {result.skipped.map((s, i) => (
                  <div
                    key={`s-${i}`}
                    className="flex items-center gap-3 px-4 py-2 text-sm border-b border-border last:border-b-0"
                  >
                    <span className="text-xl font-semibold w-8 text-text-muted">{s.char}</span>
                    <span className="text-text-muted flex-1">{s.reason}</span>
                  </div>
                ))}
                {result.failed.map((f, i) => (
                  <div
                    key={`f-${i}`}
                    className="flex items-center gap-3 px-4 py-2 text-sm border-b border-border last:border-b-0"
                  >
                    <AlertCircle size={16} className="text-error shrink-0" />
                    <span className="text-xl font-semibold w-8 text-text-primary">{f.char}</span>
                    <span className="text-text-muted flex-1">{f.reason}</span>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      ) : (
        <div className="flex flex-col gap-3">
          <textarea
            value={text}
            onChange={(e) => setText(e.target.value)}
            placeholder="粘贴任意文本，例如：你好世界！Hello 好。&#10;系统会自动提取其中的汉字（去重、忽略英文/数字/标点），并对新字用 AI 生成拼音与 4 个例词。"
            rows={8}
            className={`w-full px-3 py-2.5 text-sm bg-card border rounded-[var(--radius-sm)] focus:outline-none transition-shadow resize-none ${
              tooLong
                ? 'border-error focus:ring-2 focus:ring-error/30'
                : 'border-border focus:ring-2 focus:ring-primary/30 focus:border-primary'
            }`}
          />
          <div className="flex items-center justify-between text-xs">
            <span className={tooLong ? 'text-error' : 'text-text-muted'}>
              {tooLong ? `超出 ${MAX_TEXT_LEN} 字符上限` : `已识别 ${preview.length} 个汉字（去重）`}
            </span>
            <span className={`${text.length > MAX_TEXT_LEN ? 'text-error' : 'text-text-muted'}`}>
              {text.length}/{MAX_TEXT_LEN}
            </span>
          </div>
          {preview.length > 0 && (
            <div className="flex flex-wrap gap-1.5 max-h-24 overflow-y-auto p-2 bg-page-alt rounded-[var(--radius-sm)]">
              {preview.map((c) => (
                <span
                  key={c}
                  className="inline-flex items-center justify-center w-8 h-8 rounded-[var(--radius-sm)] bg-card border border-border text-lg font-semibold text-text-primary"
                >
                  {c}
                </span>
              ))}
            </div>
          )}
        </div>
      )}
    </Modal>
  )
}
