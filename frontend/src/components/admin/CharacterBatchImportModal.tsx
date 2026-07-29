import { useState } from 'react'
import { CheckCircle2, AlertCircle } from 'lucide-react'
import Modal from '../ui/Modal'
import type { BatchImportItem, BatchImportResult } from '../../types/hanzi'

interface Props {
  open: boolean
  onClose: () => void
  onSubmit: (items: BatchImportItem[]) => Promise<BatchImportResult>
}

const EXAMPLE = `人 rén 人类
口 kǒu 嘴巴
日 rì 太阳；天
月 yuè 月亮`

function parseLines(text: string): BatchImportItem[] {
  const items: BatchImportItem[] = []
  for (const raw of text.split('\n')) {
    const line = raw.trim()
    if (!line) continue
    const parts = line.split(/\s+/)
    if (parts.length < 2) continue
    const [char, pinyin, ...meaningParts] = parts
    items.push({ char, pinyin, meaning: meaningParts.join(' ') })
  }
  return items
}

export default function CharacterBatchImportModal({ open, onClose, onSubmit }: Props) {
  const [text, setText] = useState('')
  const [submitting, setSubmitting] = useState(false)
  const [result, setResult] = useState<BatchImportResult | null>(null)

  const items = parseLines(text)

  const handleSubmit = async () => {
    if (items.length === 0) return
    setSubmitting(true)
    const r = await onSubmit(items)
    setSubmitting(false)
    setResult(r)
  }

  const handleClose = () => {
    setText('')
    setResult(null)
    onClose()
  }

  return (
    <Modal
      open={open}
      onClose={handleClose}
      title="批量导入字条"
      subtitle="每行一条 · 用空格分隔「字 拼音 释义（可选）」"
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
              className="h-9 px-4 rounded-[var(--radius-sm)] text-sm font-semibold text-text-secondary hover:bg-page cursor-pointer transition-colors"
            >
              取消
            </button>
            <button
              onClick={handleSubmit}
              disabled={items.length === 0 || submitting}
              className="h-9 px-4 rounded-[var(--radius-sm)] text-sm font-semibold bg-primary text-text-on-primary hover:bg-primary-hover cursor-pointer transition-colors disabled:opacity-50 disabled:cursor-not-allowed flex items-center gap-2"
            >
              {submitting && (
                <div className="w-3.5 h-3.5 border-2 border-white/30 border-t-white rounded-full animate-spin" />
              )}
              导入 {items.length > 0 ? `${items.length} 条` : ''}
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
              成功导入 <span className="font-semibold text-success">{result.ok}</span> 条
              {result.failed.length > 0 && (
                <>
                  ，失败 <span className="font-semibold text-error">{result.failed.length}</span> 条
                </>
              )}
            </span>
          </div>
          {result.failed.length > 0 && (
            <div className="border border-border rounded-[var(--radius-sm)] overflow-hidden">
              <div className="px-4 py-2.5 bg-page-alt text-[13px] font-semibold text-text-primary border-b border-border">
                失败明细
              </div>
              <div className="max-h-64 overflow-y-auto">
                {result.failed.map((f, i) => (
                  <div
                    key={i}
                    className="flex items-center gap-3 px-4 py-2.5 text-sm border-b border-border last:border-b-0"
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
          <div>
            <textarea
              value={text}
              onChange={(e) => setText(e.target.value)}
              placeholder={`格式示例：\n${EXAMPLE}`}
              rows={10}
              className="w-full px-3 py-2.5 text-sm font-mono bg-card border border-border rounded-[var(--radius-sm)] focus:outline-none focus:ring-2 focus:ring-primary/30 focus:border-primary transition-shadow resize-none"
            />
          </div>
          <div className="flex items-center justify-between text-xs text-text-muted">
            <span>已解析 {items.length} 条</span>
            <button
              onClick={() => setText(EXAMPLE)}
              className="text-primary hover:text-primary-hover cursor-pointer font-medium"
            >
              填充示例
            </button>
          </div>
        </div>
      )}
    </Modal>
  )
}
