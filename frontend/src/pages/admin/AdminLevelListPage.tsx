import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { motion } from 'framer-motion'
import { Plus, Pencil, Trash2, ChevronRight } from 'lucide-react'
import LevelEditModal from '../../components/admin/LevelEditModal'
import {
  adminCreateLevel,
  adminDeleteLevel,
  adminListLevels,
  adminUpdateLevel,
} from '../../services/hanzi'
import type { HanziLevel } from '../../types/hanzi'

export default function AdminLevelListPage() {
  const [levels, setLevels] = useState<HanziLevel[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [editing, setEditing] = useState<HanziLevel | null>(null)
  const [modalOpen, setModalOpen] = useState(false)
  const [submitting, setSubmitting] = useState(false)

  const refresh = () => {
    setLoading(true)
    return adminListLevels().then((res) => {
      if (res.code === 0) {
        setLevels(res.data.levels)
        setError(null)
      } else {
        setError(res.message)
      }
      setLoading(false)
    })
  }

  useEffect(() => {
    refresh()
  }, [])

  const openCreate = () => {
    setEditing(null)
    setModalOpen(true)
  }
  const openEdit = (lvl: HanziLevel) => {
    setEditing(lvl)
    setModalOpen(true)
  }

  const handleSubmit = async (payload: {
    name: string
    description: string
    order_index: number
  }) => {
    setSubmitting(true)
    const res = editing
      ? await adminUpdateLevel(editing.id, {
          name: payload.name,
          description: payload.description,
          order_index: payload.order_index,
        })
      : await adminCreateLevel({
          name: payload.name,
          description: payload.description,
          order_index: payload.order_index,
        })
    setSubmitting(false)
    if (res.code !== 0) {
      alert(res.message)
      return
    }
    setModalOpen(false)
    refresh()
  }

  const handleDelete = async (lvl: HanziLevel) => {
    if (lvl.total > 0) {
      alert(`「${lvl.name}」下还有 ${lvl.total} 字，请先清空字条`)
      return
    }
    if (!confirm(`确认删除「${lvl.name}」？`)) return
    const res = await adminDeleteLevel(lvl.id)
    if (res.code !== 0) {
      alert(res.message)
      return
    }
    refresh()
  }

  const nextOrder = levels.length > 0 ? Math.max(...levels.map((l) => l.order_index)) + 1 : 1

  return (
    <div className="max-w-5xl mx-auto flex flex-col gap-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-text-primary tracking-tight">汉字级别管理</h1>
          <p className="text-sm text-text-muted mt-1">定义分级字库，供学习者按级别学习</p>
        </div>
        <motion.button
          onClick={openCreate}
          whileHover={{ scale: 1.01 }}
          whileTap={{ scale: 0.98 }}
          className="flex items-center gap-1.5 h-11 px-4 bg-primary text-text-on-primary text-sm font-semibold rounded-[var(--radius-sm)] hover:bg-primary-hover transition-colors cursor-pointer"
        >
          <Plus size={16} />
          新建级别
        </motion.button>
      </div>

      {loading ? (
        <div className="h-40 bg-card border border-border rounded-[var(--radius-lg)] animate-pulse" />
      ) : error ? (
        <div className="bg-card border border-border rounded-[var(--radius-lg)] p-12 text-center">
          <p className="text-sm text-error">{error}</p>
        </div>
      ) : levels.length === 0 ? (
        <div className="bg-card border border-border rounded-[var(--radius-lg)] p-12 text-center">
          <div className="text-4xl mb-3">📘</div>
          <p className="text-sm text-text-muted mb-4">还没有任何级别，先创建第一个吧</p>
          <button
            onClick={openCreate}
            className="text-sm text-primary hover:text-primary-hover cursor-pointer font-medium"
          >
            新建级别
          </button>
        </div>
      ) : (
        <div className="bg-card border border-border rounded-[var(--radius-lg)] shadow-sm overflow-hidden">
          <div className="grid grid-cols-[1fr_auto_auto_auto] items-center gap-4 px-6 py-3 bg-page-alt border-b border-border text-[12px] font-semibold uppercase tracking-wider text-text-muted">
            <div>名称 / 描述</div>
            <div className="w-24 text-center">字数</div>
            <div className="w-32">创建时间</div>
            <div className="w-24 text-right">操作</div>
          </div>
          {[...levels]
            .sort((a, b) => a.order_index - b.order_index)
            .map((lvl) => (
              <div
                key={lvl.id}
                className="grid grid-cols-[1fr_auto_auto_auto] items-center gap-4 px-6 py-4 border-b border-border last:border-b-0 hover:bg-page/60 transition-colors group"
              >
                <div className="min-w-0">
                  <Link
                    to={`/ai-tools/admin/hanzi/levels/${lvl.id}/characters`}
                    className="flex items-center gap-1.5 text-[15px] font-semibold text-text-primary hover:text-primary transition-colors group/link"
                  >
                    <span>{lvl.name}</span>
                    <ChevronRight
                      size={14}
                      className="opacity-0 group-hover/link:opacity-100 -translate-x-1 group-hover/link:translate-x-0 transition-all"
                    />
                  </Link>
                  {lvl.description && (
                    <p className="text-sm text-text-muted mt-0.5 truncate">{lvl.description}</p>
                  )}
                </div>
                <div className="w-24 text-center">
                  <span className="inline-flex items-center justify-center min-w-8 h-6 px-2 rounded-[var(--radius-sm)] bg-primary-light text-primary text-xs font-semibold">
                    {lvl.total} 字
                  </span>
                </div>
                <div className="w-32 text-sm text-text-muted">
                  {new Date(lvl.created_at).toLocaleDateString('zh-CN')}
                </div>
                <div className="w-24 flex items-center justify-end gap-1">
                  <button
                    onClick={() => openEdit(lvl)}
                    className="w-8 h-8 rounded-[var(--radius-sm)] flex items-center justify-center text-text-muted hover:text-primary hover:bg-primary-light transition-colors cursor-pointer"
                    aria-label="编辑"
                  >
                    <Pencil size={14} />
                  </button>
                  <button
                    onClick={() => handleDelete(lvl)}
                    className="w-8 h-8 rounded-[var(--radius-sm)] flex items-center justify-center text-text-muted hover:text-error hover:bg-error-light transition-colors cursor-pointer"
                    aria-label="删除"
                  >
                    <Trash2 size={14} />
                  </button>
                </div>
              </div>
            ))}
        </div>
      )}

      <LevelEditModal
        open={modalOpen}
        onClose={() => setModalOpen(false)}
        onSubmit={handleSubmit}
        level={editing}
        nextOrderIndex={nextOrder}
        submitting={submitting}
      />
    </div>
  )
}
