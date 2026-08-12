import { useEffect, useState } from 'react'
import { Info, Loader2 } from 'lucide-react'
import Modal from '../ui/Modal'
import type { T2ITemplate } from '../../types/t2i'

interface Props {
  open: boolean
  template: T2ITemplate | null
  onClose: () => void
  onSubmit: (keywords: Record<string, string>) => Promise<void>
}

export default function T2ITaskCreateModal({ open, template, onClose, onSubmit }: Props) {
  const [item, setItem] = useState('')
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(false)

  useEffect(() => {
    if (open) {
      setItem('')
      setError('')
      setLoading(false)
    }
  }, [open, template?.code])

  if (!template) return null

  const canSubmit = item.trim().length > 0
  const preview = template.prompt.replace(/\{\{item\}\}/g, item.trim() || '…')

  const handleSubmit = async () => {
    if (!canSubmit || loading) return
    setError('')
    setLoading(true)
    try {
      await onSubmit({ item: item.trim() })
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : '提交失败')
    } finally {
      setLoading(false)
    }
  }

  return (
    <Modal
      open={open}
      onClose={onClose}
      title={`新建任务 · ${template.name}`}
      subtitle={template.description ?? undefined}
      footer={
        <>
          <button
            onClick={onClose}
            className="h-10 px-4 border border-border text-sm font-semibold text-text-secondary rounded-[var(--radius-sm)] hover:border-primary hover:text-primary transition-colors cursor-pointer"
            disabled={loading}
          >
            取消
          </button>
          <button
            onClick={handleSubmit}
            disabled={!canSubmit || loading}
            className="h-10 px-4 bg-primary text-text-on-primary text-sm font-semibold rounded-[var(--radius-sm)] hover:bg-primary-hover transition-colors disabled:opacity-50 disabled:cursor-not-allowed cursor-pointer inline-flex items-center gap-1.5"
          >
            {loading && <Loader2 size={14} className="animate-spin" />}
            创建并生成
          </button>
        </>
      }
    >
      <div className="flex flex-col gap-4">
        <label className="flex flex-col gap-1.5">
          <span className="text-[13px] font-semibold text-text-primary">
            关键词<span className="text-error ml-0.5">*</span>
          </span>
          <input
            type="text"
            value={item}
            onChange={(e) => setItem(e.target.value)}
            placeholder="例如 apple / 苹果"
            maxLength={100}
            autoFocus
            className="h-11 px-3 text-base bg-input-bg border border-border rounded-[var(--radius-sm)] focus:outline-none focus:ring-2 focus:ring-primary/30 focus:border-primary transition-colors"
          />
        </label>

        <div className="flex flex-col gap-1">
          <span className="text-[12px] font-semibold text-text-muted uppercase tracking-wider">
            Prompt 预览
          </span>
          <div className="p-3 bg-page border border-border rounded-[var(--radius-sm)] text-sm text-text-secondary whitespace-pre-wrap break-words">
            {preview}
          </div>
        </div>

        <div className="flex items-start gap-2 p-3 bg-page rounded-[var(--radius-sm)] text-xs text-text-muted">
          <Info size={14} className="shrink-0 mt-0.5" />
          <span>创建后会立刻发起一次生成。同一模板下重复的关键字会打开已有任务。</span>
        </div>

        {error && <div className="text-sm text-error">{error}</div>}
      </div>
    </Modal>
  )
}
