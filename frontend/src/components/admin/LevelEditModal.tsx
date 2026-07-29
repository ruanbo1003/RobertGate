import { useEffect, useState } from 'react'
import Modal from '../ui/Modal'
import type { HanziLevel } from '../../types/hanzi'

interface Props {
  open: boolean
  onClose: () => void
  onSubmit: (payload: { name: string; description: string; order_index: number }) => void
  level: HanziLevel | null // null 表示新建
  nextOrderIndex: number
  submitting?: boolean
}

export default function LevelEditModal({ open, onClose, onSubmit, level, nextOrderIndex, submitting }: Props) {
  const [name, setName] = useState('')
  const [description, setDescription] = useState('')
  const [orderIndex, setOrderIndex] = useState(0)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    if (!open) return
    setName(level?.name ?? '')
    setDescription(level?.description ?? '')
    setOrderIndex(level?.order_index ?? nextOrderIndex)
    setError(null)
  }, [open, level, nextOrderIndex])

  const handleSubmit = () => {
    if (!name.trim()) {
      setError('名称不能为空')
      return
    }
    onSubmit({ name: name.trim(), description: description.trim(), order_index: orderIndex })
  }

  return (
    <Modal
      open={open}
      onClose={onClose}
      title={level ? '编辑级别' : '新建级别'}
      subtitle={level ? '修改级别信息' : '创建一个新的分级字库'}
      width={520}
      footer={
        <>
          <button
            onClick={onClose}
            className="h-9 px-4 rounded-[var(--radius-sm)] text-sm font-semibold text-text-secondary hover:bg-page cursor-pointer transition-colors"
          >
            取消
          </button>
          <button
            onClick={handleSubmit}
            disabled={submitting}
            className="h-9 px-4 rounded-[var(--radius-sm)] text-sm font-semibold bg-primary text-text-on-primary hover:bg-primary-hover cursor-pointer transition-colors disabled:opacity-50 disabled:cursor-not-allowed flex items-center gap-2"
          >
            {submitting && (
              <div className="w-3.5 h-3.5 border-2 border-white/30 border-t-white rounded-full animate-spin" />
            )}
            保存
          </button>
        </>
      }
    >
      <div className="flex flex-col gap-4">
        <div>
          <label className="block text-[13px] font-semibold text-text-primary mb-1.5">
            名称 <span className="text-error">*</span>
          </label>
          <input
            type="text"
            value={name}
            onChange={(e) => {
              setName(e.target.value)
              if (error) setError(null)
            }}
            placeholder="例如：启蒙 · Level 1"
            className={`w-full h-11 px-3 text-base bg-card border rounded-[var(--radius-sm)] focus:outline-none transition-shadow ${
              error
                ? 'border-error focus:ring-2 focus:ring-error/30'
                : 'border-border focus:ring-2 focus:ring-primary/30 focus:border-primary'
            }`}
          />
          {error && <p className="text-xs text-error mt-1.5">{error}</p>}
        </div>

        <div>
          <label className="block text-[13px] font-semibold text-text-primary mb-1.5">描述</label>
          <textarea
            value={description}
            onChange={(e) => setDescription(e.target.value)}
            placeholder="选填 · 用一句话介绍这个级别的内容"
            rows={3}
            className="w-full px-3 py-2 text-base bg-card border border-border rounded-[var(--radius-sm)] focus:outline-none focus:ring-2 focus:ring-primary/30 focus:border-primary transition-shadow resize-none"
          />
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
      </div>
    </Modal>
  )
}
