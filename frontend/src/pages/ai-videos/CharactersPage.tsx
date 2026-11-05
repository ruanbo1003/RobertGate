import { useCallback, useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { ChevronRight, UserPlus } from 'lucide-react'
import Navbar from '../../components/layout/Navbar'
import Footer from '../../components/layout/Footer'
import CharacterCard from '../../components/ai-videos/CharacterCard'
import CharacterEditorModal from '../../components/ai-videos/CharacterEditorModal'
import ConfirmDialog from '../../components/ai-videos/ConfirmDialog'
import type { Character, ModelInfo } from '../../types/aiVideos'
import { deleteCharacter, getModels, listCharacters } from '../../services/aiVideos'

export default function CharactersPage() {
  const [characters, setCharacters] = useState<Character[]>([])
  const [t2iModels, setT2iModels] = useState<ModelInfo[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [editorOpen, setEditorOpen] = useState(false)
  const [editing, setEditing] = useState<Character | null>(null)
  const [deleteTarget, setDeleteTarget] = useState<Character | null>(null)
  const [deleting, setDeleting] = useState(false)

  const load = useCallback(() => {
    return listCharacters().then((res) => {
      if (res.code === 0 && res.data) {
        setCharacters(res.data.characters)
        setError('')
      } else {
        setError(res.message)
      }
      setLoading(false)
    })
  }, [])

  useEffect(() => {
    void load()
    void getModels().then((res) => {
      if (res.code === 0 && res.data) setT2iModels(res.data.models.t2i ?? [])
    })
  }, [load])

  const [editorSession, setEditorSession] = useState(0)

  const openEditor = (char: Character | null) => {
    setEditing(char)
    setEditorSession((s) => s + 1) // key 重挂载，重置弹层表单
    setEditorOpen(true)
  }

  const handleDelete = async () => {
    if (!deleteTarget) return
    setDeleting(true)
    const res = await deleteCharacter(deleteTarget.id)
    setDeleting(false)
    setDeleteTarget(null)
    if (res.code !== 0) {
      setError(res.message)
      return
    }
    void load()
  }

  return (
    <div className="min-h-screen flex flex-col bg-page">
      <Navbar />
      <main className="flex-1 w-full max-w-6xl mx-auto px-5 py-8">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 mb-7">
          <div>
            <div className="flex items-center gap-1.5 text-xs text-text-muted mb-1.5">
              <Link to="/ai-videos" className="hover:text-primary transition-colors">
                AI Videos
              </Link>
              <ChevronRight size={12} />
              <span>角色库</span>
            </div>
            <h1 className="text-2xl font-bold text-text-primary tracking-tight">角色库</h1>
          </div>
          <button
            onClick={() => openEditor(null)}
            className="flex items-center gap-2 h-11 px-5 bg-primary hover:bg-primary-hover text-white text-sm font-semibold rounded-[var(--radius-sm)] transition-colors cursor-pointer"
          >
            <UserPlus size={15} />
            新建角色
          </button>
        </div>

        {error && (
          <div className="mb-5 px-4 py-3 bg-error-light text-error text-sm rounded-[var(--radius-sm)]">
            {error}
          </div>
        )}

        {loading ? (
          <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-5">
            {Array.from({ length: 4 }).map((_, i) => (
              <div
                key={i}
                className="bg-card rounded-[var(--radius-lg)] border border-border overflow-hidden animate-pulse"
              >
                <div className="w-full aspect-[9/16] bg-page-alt" />
                <div className="p-4 flex flex-col gap-2">
                  <div className="h-4 bg-page-alt rounded w-1/3" />
                  <div className="h-3 bg-page-alt rounded w-3/4" />
                </div>
              </div>
            ))}
          </div>
        ) : characters.length === 0 ? (
          <div className="flex flex-col items-center gap-4 py-24 text-center">
            <div className="w-14 h-14 flex items-center justify-center bg-primary-light rounded-full">
              <UserPlus size={24} className="text-primary" />
            </div>
            <div>
              <p className="text-base font-bold text-text-primary">角色库还是空的</p>
              <p className="text-sm text-text-muted mt-1">先创建第一个角色，视频里的主角从这里来</p>
            </div>
            <button
              onClick={() => openEditor(null)}
              className="flex items-center gap-2 h-11 px-6 bg-primary hover:bg-primary-hover text-white text-sm font-semibold rounded-[var(--radius-sm)] transition-colors cursor-pointer"
            >
              <UserPlus size={15} />
              新建角色
            </button>
          </div>
        ) : (
          <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-5">
            {characters.map((c) => (
              <CharacterCard
                key={c.id}
                character={c}
                onEdit={() => openEditor(c)}
                onDelete={() => setDeleteTarget(c)}
              />
            ))}
            <button
              onClick={() => openEditor(null)}
              className="flex flex-col items-center justify-center gap-3 min-h-[300px] bg-page rounded-[var(--radius-lg)] border border-dashed border-border hover:border-primary/50 transition-colors cursor-pointer group"
            >
              <span className="w-12 h-12 flex items-center justify-center bg-primary-light rounded-full group-hover:scale-105 transition-transform">
                <UserPlus size={20} className="text-primary" />
              </span>
              <span className="text-[13px] font-semibold text-text-muted">新建角色</span>
            </button>
          </div>
        )}
      </main>
      <Footer />

      <CharacterEditorModal
        key={editorSession}
        open={editorOpen}
        character={editing}
        t2iModels={t2iModels}
        onClose={() => {
          setEditorOpen(false)
          void load() // 新建模式下可能已落库草稿，关闭也要刷新
        }}
        onSaved={() => void load()}
      />
      <ConfirmDialog
        open={deleteTarget != null}
        title="删除角色"
        danger
        confirmText="删除"
        loading={deleting}
        onConfirm={handleDelete}
        onCancel={() => setDeleteTarget(null)}
      >
        确认删除角色「{deleteTarget?.name}」？已被视频引用的角色无法删除。
      </ConfirmDialog>
    </div>
  )
}
