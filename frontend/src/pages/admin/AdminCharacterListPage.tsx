import { useEffect, useState } from 'react'
import { Link, useParams } from 'react-router-dom'
import { motion } from 'framer-motion'
import { Plus, Upload, Pencil, Trash2, ChevronLeft } from 'lucide-react'
import CharacterEditModal from '../../components/admin/CharacterEditModal'
import CharacterBatchImportModal from '../../components/admin/CharacterBatchImportModal'
import {
  adminBatchImport,
  adminCreateCharacter,
  adminDeleteCharacter,
  adminListCharacters,
  adminUpdateCharacter,
} from '../../services/hanzi'
import type {
  BatchImportItem,
  HanziCharacter,
  HanziLevelSummary,
} from '../../types/hanzi'

export default function AdminCharacterListPage() {
  const { levelId = '' } = useParams()
  const [level, setLevel] = useState<HanziLevelSummary | null>(null)
  const [chars, setChars] = useState<HanziCharacter[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  const [editing, setEditing] = useState<HanziCharacter | null>(null)
  const [editOpen, setEditOpen] = useState(false)
  const [batchOpen, setBatchOpen] = useState(false)
  const [submitting, setSubmitting] = useState(false)

  const refresh = () => {
    setLoading(true)
    return adminListCharacters(levelId).then((res) => {
      if (res.code === 0 && res.data) {
        setLevel(res.data.level)
        setChars(res.data.characters)
        setError(null)
      } else {
        setError(res.message)
      }
      setLoading(false)
    })
  }

  useEffect(() => {
    refresh()
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [levelId])

  const nextOrder = chars.length > 0 ? Math.max(...chars.map((c) => c.order_index)) + 1 : 0

  const openCreate = () => {
    setEditing(null)
    setEditOpen(true)
  }
  const openEdit = (c: HanziCharacter) => {
    setEditing(c)
    setEditOpen(true)
  }

  const handleSubmit = async (payload: {
    char: string
    pinyin: string
    meaning: string
    order_index: number
  }) => {
    setSubmitting(true)
    const res = editing
      ? await adminUpdateCharacter(editing.id, {
          char: payload.char,
          pinyin: payload.pinyin,
          meaning: payload.meaning,
          order_index: payload.order_index,
        })
      : await adminCreateCharacter(levelId, {
          char: payload.char,
          pinyin: payload.pinyin,
          meaning: payload.meaning,
          order_index: payload.order_index,
        })
    setSubmitting(false)
    if (res.code !== 0) {
      alert(res.message)
      return
    }
    setEditOpen(false)
    refresh()
  }

  const handleDelete = async (c: HanziCharacter) => {
    if (!confirm(`确认删除「${c.char}」？关联的用户学习记录也会一并删除。`)) return
    const res = await adminDeleteCharacter(c.id)
    if (res.code !== 0) {
      alert(res.message)
      return
    }
    refresh()
  }

  const handleBatch = async (items: BatchImportItem[]) => {
    const res = await adminBatchImport(levelId, items)
    if (res.code !== 0 || !res.data) {
      alert(res.message)
      return { ok: 0, failed: items.map((i) => ({ char: i.char, reason: res.message })) }
    }
    refresh()
    return res.data
  }

  if (loading) {
    return (
      <div className="max-w-6xl mx-auto flex flex-col gap-6">
        <div className="h-24 bg-card border border-border rounded-[var(--radius-lg)] animate-pulse" />
        <div className="grid grid-cols-3 sm:grid-cols-4 md:grid-cols-5 lg:grid-cols-6 xl:grid-cols-7 gap-3">
          {Array.from({ length: 14 }).map((_, i) => (
            <div
              key={i}
              className="h-24 bg-card border border-border rounded-[var(--radius-lg)] animate-pulse"
            />
          ))}
        </div>
      </div>
    )
  }

  if (error || !level) {
    return (
      <div className="max-w-5xl mx-auto text-center py-12">
        <p className="text-sm text-text-muted">{error ?? '级别不存在'}</p>
        <Link
          to="/ai-tools/admin/hanzi"
          className="text-sm text-primary hover:text-primary-hover cursor-pointer font-medium mt-2 inline-block"
        >
          返回级别列表
        </Link>
      </div>
    )
  }

  return (
    <div className="max-w-6xl mx-auto flex flex-col gap-6">
      <div className="flex items-center justify-between gap-4">
        <div className="min-w-0">
          <Link
            to="/ai-tools/admin/hanzi"
            className="inline-flex items-center gap-1 text-xs text-text-muted hover:text-primary transition-colors mb-1.5 cursor-pointer"
          >
            <ChevronLeft size={12} />
            返回级别列表
          </Link>
          <h1 className="text-2xl font-bold text-text-primary tracking-tight truncate">
            {level.name}
          </h1>
          {level.description && (
            <p className="text-sm text-text-muted mt-1 truncate">{level.description}</p>
          )}
        </div>
        <div className="flex items-center gap-2 shrink-0">
          <motion.button
            onClick={() => setBatchOpen(true)}
            whileHover={{ scale: 1.01 }}
            whileTap={{ scale: 0.98 }}
            className="flex items-center gap-1.5 h-11 px-4 bg-card border border-border text-text-primary text-sm font-semibold rounded-[var(--radius-sm)] hover:border-primary hover:text-primary transition-colors cursor-pointer"
          >
            <Upload size={16} />
            批量导入
          </motion.button>
          <motion.button
            onClick={openCreate}
            whileHover={{ scale: 1.01 }}
            whileTap={{ scale: 0.98 }}
            className="flex items-center gap-1.5 h-11 px-4 bg-primary text-text-on-primary text-sm font-semibold rounded-[var(--radius-sm)] hover:bg-primary-hover transition-colors cursor-pointer"
          >
            <Plus size={16} />
            单条添加
          </motion.button>
        </div>
      </div>

      <div className="flex items-center gap-2 text-sm text-text-secondary">
        <span>共</span>
        <span className="font-semibold text-primary">{chars.length}</span>
        <span>字</span>
      </div>

      {chars.length === 0 ? (
        <div className="bg-card border border-border rounded-[var(--radius-lg)] p-12 text-center">
          <div className="text-4xl mb-3">📝</div>
          <p className="text-sm text-text-muted mb-4">该级别还没有字条</p>
          <div className="flex items-center justify-center gap-4">
            <button
              onClick={openCreate}
              className="text-sm text-primary hover:text-primary-hover cursor-pointer font-medium"
            >
              添加第一个
            </button>
            <span className="text-text-muted">·</span>
            <button
              onClick={() => setBatchOpen(true)}
              className="text-sm text-primary hover:text-primary-hover cursor-pointer font-medium"
            >
              批量导入
            </button>
          </div>
        </div>
      ) : (
        <div className="grid grid-cols-3 sm:grid-cols-4 md:grid-cols-5 lg:grid-cols-6 xl:grid-cols-7 gap-3">
          {[...chars]
            .sort((a, b) => a.order_index - b.order_index)
            .map((c) => (
              <div
                key={c.id}
                className="group relative bg-card border border-border rounded-[var(--radius-lg)] p-3 flex flex-col items-center gap-1 hover:border-primary hover:shadow-sm transition-all"
              >
                <div className="text-4xl font-semibold text-text-primary leading-none">
                  {c.char}
                </div>
                <div className="text-sm text-text-muted">{c.pinyin}</div>
                {c.meaning && (
                  <div
                    className="text-xs text-text-muted text-center truncate w-full"
                    title={c.meaning}
                  >
                    {c.meaning}
                  </div>
                )}
                <div className="absolute top-1.5 right-1.5 flex items-center gap-0.5 opacity-0 group-hover:opacity-100 transition-opacity">
                  <button
                    onClick={() => openEdit(c)}
                    className="w-6 h-6 rounded-[var(--radius-sm)] flex items-center justify-center bg-card border border-border text-text-muted hover:text-primary hover:border-primary transition-colors cursor-pointer"
                    aria-label="编辑"
                  >
                    <Pencil size={11} />
                  </button>
                  <button
                    onClick={() => handleDelete(c)}
                    className="w-6 h-6 rounded-[var(--radius-sm)] flex items-center justify-center bg-card border border-border text-text-muted hover:text-error hover:border-error transition-colors cursor-pointer"
                    aria-label="删除"
                  >
                    <Trash2 size={11} />
                  </button>
                </div>
              </div>
            ))}
        </div>
      )}

      <CharacterEditModal
        open={editOpen}
        onClose={() => setEditOpen(false)}
        onSubmit={handleSubmit}
        character={editing}
        nextOrderIndex={nextOrder}
        submitting={submitting}
      />
      <CharacterBatchImportModal
        open={batchOpen}
        onClose={() => setBatchOpen(false)}
        onSubmit={handleBatch}
      />
    </div>
  )
}
