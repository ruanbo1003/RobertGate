import { useEffect, useState } from 'react'
import { Loader2, Trash2 } from 'lucide-react'
import Modal from '../ui/Modal'
import type { T2ITemplate } from '../../types/t2i'

interface Props {
  open: boolean
  template: T2ITemplate | null // null 表示新建
  nextOrderIndex: number
  onClose: () => void
  onSubmit: (payload: {
    code: string
    name: string
    description: string
    prompt: string
    order_index: number
  }) => Promise<void>
  onDelete?: (template: T2ITemplate) => Promise<void>
}

const CODE_RE = /^[a-z][a-z0-9-]{1,63}$/

export default function T2ITemplateEditModal({
  open,
  template,
  nextOrderIndex,
  onClose,
  onSubmit,
  onDelete,
}: Props) {
  const isEdit = !!template
  const isBuiltin = !!template?.is_builtin

  const [code, setCode] = useState('')
  const [name, setName] = useState('')
  const [description, setDescription] = useState('')
  const [prompt, setPrompt] = useState('')
  const [orderIndex, setOrderIndex] = useState(0)
  const [error, setError] = useState<string | null>(null)
  const [submitting, setSubmitting] = useState(false)
  const [deleting, setDeleting] = useState(false)

  useEffect(() => {
    if (!open) return
    setCode(template?.code ?? '')
    setName(template?.name ?? '')
    setDescription(template?.description ?? '')
    setPrompt(template?.prompt ?? '')
    setOrderIndex(template?.order_index ?? nextOrderIndex)
    setError(null)
    setSubmitting(false)
    setDeleting(false)
  }, [open, template, nextOrderIndex])

  const validate = (): string | null => {
    if (!isEdit) {
      const c = code.trim()
      if (!c) return 'code 不能为空'
      if (!CODE_RE.test(c)) return 'code 只能小写字母/数字/连字符，2-64 位'
    }
    if (!name.trim()) return '名称不能为空'
    if (!prompt.includes('{{item}}')) return 'Prompt 必须包含占位符 {{item}}'
    return null
  }

  const handleSubmit = async () => {
    const err = validate()
    if (err) {
      setError(err)
      return
    }
    setError(null)
    setSubmitting(true)
    try {
      await onSubmit({
        code: code.trim(),
        name: name.trim(),
        description: description.trim(),
        prompt: prompt.trim(),
        order_index: orderIndex,
      })
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : '提交失败')
    } finally {
      setSubmitting(false)
    }
  }

  const handleDelete = async () => {
    if (!template || !onDelete || isBuiltin) return
    if (!confirm(`确认删除模板「${template.name}」？该操作不可撤销。`)) return
    setError(null)
    setDeleting(true)
    try {
      await onDelete(template)
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : '删除失败')
    } finally {
      setDeleting(false)
    }
  }

  const showDelete = isEdit && !!onDelete && !isBuiltin

  return (
    <Modal
      open={open}
      onClose={onClose}
      title={isEdit ? '编辑模板' : '新建模板'}
      subtitle={isEdit ? '修改模板信息（code 不可修改）' : '定义一个新的文生图模板'}
      width={620}
      footer={
        <>
          {showDelete && (
            <button
              onClick={handleDelete}
              disabled={submitting || deleting}
              className="mr-auto h-9 px-4 rounded-[var(--radius-sm)] text-sm font-semibold text-error hover:bg-error-light cursor-pointer transition-colors disabled:opacity-50 disabled:cursor-not-allowed flex items-center gap-2"
            >
              {deleting ? (
                <Loader2 size={14} className="animate-spin" />
              ) : (
                <Trash2 size={14} />
              )}
              删除模板
            </button>
          )}
          <button
            onClick={onClose}
            disabled={submitting || deleting}
            className="h-9 px-4 rounded-[var(--radius-sm)] text-sm font-semibold text-text-secondary hover:bg-page cursor-pointer transition-colors"
          >
            取消
          </button>
          <button
            onClick={handleSubmit}
            disabled={submitting || deleting || isBuiltin}
            className="h-9 px-4 rounded-[var(--radius-sm)] text-sm font-semibold bg-primary text-text-on-primary hover:bg-primary-hover cursor-pointer transition-colors disabled:opacity-50 disabled:cursor-not-allowed flex items-center gap-2"
          >
            {submitting && <Loader2 size={14} className="animate-spin" />}
            保存
          </button>
        </>
      }
    >
      <div className="flex flex-col gap-4">
        {isBuiltin && (
          <div className="p-3 bg-warning-light text-warning text-xs rounded-[var(--radius-sm)]">
            这是内置模板，不可修改或删除。
          </div>
        )}

        <div>
          <label className="block text-[13px] font-semibold text-text-primary mb-1.5">
            code <span className="text-error">*</span>
          </label>
          <input
            type="text"
            value={code}
            onChange={(e) => setCode(e.target.value)}
            placeholder="例如 english-primer"
            disabled={isEdit}
            className="w-full h-11 px-3 text-base bg-card border border-border rounded-[var(--radius-sm)] focus:outline-none focus:ring-2 focus:ring-primary/30 focus:border-primary transition-shadow disabled:bg-page disabled:text-text-muted disabled:cursor-not-allowed"
          />
          <p className="text-xs text-text-muted mt-1.5">
            用作 URL 与内部标识，只允许小写字母/数字/连字符，2-64 位。创建后不可修改。
          </p>
        </div>

        <div>
          <label className="block text-[13px] font-semibold text-text-primary mb-1.5">
            名称 <span className="text-error">*</span>
          </label>
          <input
            type="text"
            value={name}
            onChange={(e) => setName(e.target.value)}
            placeholder="例如 英文启蒙"
            className="w-full h-11 px-3 text-base bg-card border border-border rounded-[var(--radius-sm)] focus:outline-none focus:ring-2 focus:ring-primary/30 focus:border-primary transition-shadow"
          />
        </div>

        <div>
          <label className="block text-[13px] font-semibold text-text-primary mb-1.5">描述</label>
          <input
            type="text"
            value={description}
            onChange={(e) => setDescription(e.target.value)}
            placeholder="选填 · 侧边栏与列表页会展示"
            className="w-full h-11 px-3 text-base bg-card border border-border rounded-[var(--radius-sm)] focus:outline-none focus:ring-2 focus:ring-primary/30 focus:border-primary transition-shadow"
          />
        </div>

        <div>
          <label className="block text-[13px] font-semibold text-text-primary mb-1.5">
            Prompt 模板 <span className="text-error">*</span>
          </label>
          <textarea
            value={prompt}
            onChange={(e) => setPrompt(e.target.value)}
            placeholder="A cute flat cartoon illustration of a {{item}}, plain white background."
            rows={5}
            className="w-full px-3 py-2 text-sm font-mono bg-card border border-border rounded-[var(--radius-sm)] focus:outline-none focus:ring-2 focus:ring-primary/30 focus:border-primary transition-shadow resize-y"
          />
          <p className="text-xs text-text-muted mt-1.5">
            必须包含占位符 <code className="px-1 bg-page rounded">{'{{item}}'}</code>
            ，用户输入的关键词会替换该占位符。
          </p>
        </div>

        <div>
          <label className="block text-[13px] font-semibold text-text-primary mb-1.5">排序位</label>
          <input
            type="number"
            value={orderIndex}
            onChange={(e) => setOrderIndex(Number(e.target.value))}
            className="w-32 h-11 px-3 text-base bg-card border border-border rounded-[var(--radius-sm)] focus:outline-none focus:ring-2 focus:ring-primary/30 focus:border-primary transition-shadow"
          />
          <p className="text-xs text-text-muted mt-1.5">数字越小越靠前</p>
        </div>

        {error && <p className="text-xs text-error">{error}</p>}
      </div>
    </Modal>
  )
}
