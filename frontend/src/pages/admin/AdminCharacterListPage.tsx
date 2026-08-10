import { useEffect, useState } from 'react'
import { Link, useParams } from 'react-router-dom'
import { motion } from 'framer-motion'
import { Sparkles, Pencil, Trash2, ChevronLeft } from 'lucide-react'
import CharacterEditModal from '../../components/admin/CharacterEditModal'
import CharacterAiAddModal from '../../components/admin/CharacterAiAddModal'
import {
  adminAiAddCharacters,
  adminCreateCharacter,
  adminDeleteCharacter,
  adminListCharacters,
  adminUpdateCharacter,
} from '../../services/hanzi'
import type {
  AiAddResponse,
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
  const [aiOpen, setAiOpen] = useState(false)
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

  const openEdit = (c: HanziCharacter) => {
    setEditing(c)
    setEditOpen(true)
  }

  const handleSubmit = async (payload: {
    char: string
    pinyin: string
    example_words: string[]
    order_index: number
  }) => {
    setSubmitting(true)
    const res = editing
      ? await adminUpdateCharacter(editing.id, {
          char: payload.char,
          pinyin: payload.pinyin,
          example_words: payload.example_words,
          order_index: payload.order_index,
        })
      : await adminCreateCharacter(levelId, {
          char: payload.char,
          pinyin: payload.pinyin,
          example_words: payload.example_words,
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

  const handleAiAdd = async (text: string): Promise<AiAddResponse | null> => {
    const res = await adminAiAddCharacters(levelId, text)
    if (res.code !== 0 || !res.data) {
      alert(res.message)
      return null
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
            onClick={() => setAiOpen(true)}
            whileHover={{ scale: 1.01 }}
            whileTap={{ scale: 0.98 }}
            className="flex items-center gap-1.5 h-11 px-4 bg-primary text-text-on-primary text-sm font-semibold rounded-[var(--radius-sm)] hover:bg-primary-hover transition-colors cursor-pointer"
          >
            <Sparkles size={16} />
            汉字添加
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
          <button
            onClick={() => setAiOpen(true)}
            className="inline-flex items-center gap-1.5 text-sm text-primary hover:text-primary-hover cursor-pointer font-medium"
          >
            <Sparkles size={14} />
            汉字添加
          </button>
        </div>
      ) : (
        <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-5 xl:grid-cols-6 gap-3">
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
                {c.example_words && c.example_words.length > 0 && (
                  <div
                    className="text-xs text-text-muted text-center leading-snug line-clamp-2 w-full mt-0.5"
                    title={c.example_words.join('、')}
                  >
                    {c.example_words.join('、')}
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
      <CharacterAiAddModal
        open={aiOpen}
        onClose={() => setAiOpen(false)}
        onSubmit={handleAiAdd}
      />
    </div>
  )
}
