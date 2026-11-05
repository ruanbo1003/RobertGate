import { useCallback, useEffect, useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { Clapperboard, Plus, Users } from 'lucide-react'
import Navbar from '../../components/layout/Navbar'
import Footer from '../../components/layout/Footer'
import ProjectCard from '../../components/ai-videos/ProjectCard'
import CreateWizard from '../../components/ai-videos/CreateWizard'
import ConfirmDialog from '../../components/ai-videos/ConfirmDialog'
import type { Character, ModelsMap, ProjectSummary } from '../../types/aiVideos'
import {
  deleteProject,
  getModels,
  listCharacters,
  listProjects,
} from '../../services/aiVideos'

export default function ProjectListPage() {
  const navigate = useNavigate()
  const [projects, setProjects] = useState<ProjectSummary[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [wizardOpen, setWizardOpen] = useState(false)
  const [characters, setCharacters] = useState<Character[]>([])
  const [models, setModels] = useState<ModelsMap | null>(null)
  const [deleteTarget, setDeleteTarget] = useState<ProjectSummary | null>(null)
  const [deleting, setDeleting] = useState(false)

  const load = useCallback(() => {
    return listProjects().then((res) => {
      if (res.code === 0 && res.data) {
        setProjects(res.data.items)
        setError('')
      } else {
        setError(res.message)
      }
      setLoading(false)
    })
  }, [])

  useEffect(() => {
    void load()
  }, [load])

  const openWizard = async () => {
    if (!models) {
      const [mRes, cRes] = await Promise.all([getModels(), listCharacters()])
      if (mRes.code === 0 && mRes.data) setModels(mRes.data.models)
      if (cRes.code === 0 && cRes.data) setCharacters(cRes.data.characters)
    } else {
      const cRes = await listCharacters()
      if (cRes.code === 0 && cRes.data) setCharacters(cRes.data.characters)
    }
    setWizardOpen(true)
  }

  const handleDelete = async () => {
    if (!deleteTarget) return
    setDeleting(true)
    const res = await deleteProject(deleteTarget.id)
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
            <h1 className="text-2xl font-bold text-text-primary tracking-tight">AI Videos</h1>
            <p className="text-sm text-text-muted mt-1">
              English learning short videos, powered by AI
            </p>
          </div>
          <div className="flex items-center gap-3">
            <Link
              to="/ai-videos/characters"
              className="flex items-center gap-2 h-11 px-5 bg-card border border-border text-text-primary text-sm font-semibold rounded-[var(--radius-sm)] hover:border-primary hover:text-primary transition-colors"
            >
              <Users size={15} />
              角色库
            </Link>
            <button
              onClick={openWizard}
              className="flex items-center gap-2 h-11 px-5 bg-primary hover:bg-primary-hover text-white text-sm font-semibold rounded-[var(--radius-sm)] transition-colors cursor-pointer"
            >
              <Plus size={15} />
              新建视频
            </button>
          </div>
        </div>

        {error && (
          <div className="mb-5 px-4 py-3 bg-error-light text-error text-sm rounded-[var(--radius-sm)]">
            {error}
          </div>
        )}

        {loading ? (
          <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-5 gap-5">
            {Array.from({ length: 5 }).map((_, i) => (
              <div
                key={i}
                className="bg-card rounded-[var(--radius-lg)] border border-border overflow-hidden animate-pulse"
              >
                <div className="w-full aspect-[3/4] bg-page-alt" />
                <div className="p-4 flex flex-col gap-2">
                  <div className="h-4 bg-page-alt rounded w-3/4" />
                  <div className="h-3 bg-page-alt rounded w-1/2" />
                </div>
              </div>
            ))}
          </div>
        ) : projects.length === 0 ? (
          <div className="flex flex-col items-center gap-4 py-24 text-center">
            <div className="w-14 h-14 flex items-center justify-center bg-primary-light rounded-full">
              <Clapperboard size={24} className="text-primary" />
            </div>
            <div>
              <p className="text-base font-bold text-text-primary">还没有视频</p>
              <p className="text-sm text-text-muted mt-1">创建第一集英语启蒙短视频吧</p>
            </div>
            <button
              onClick={openWizard}
              className="flex items-center gap-2 h-11 px-6 bg-primary hover:bg-primary-hover text-white text-sm font-semibold rounded-[var(--radius-sm)] transition-colors cursor-pointer"
            >
              <Plus size={15} />
              新建视频
            </button>
          </div>
        ) : (
          <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-5 gap-5">
            {projects.map((p) => (
              <ProjectCard
                key={p.id}
                project={p}
                onOpen={() => navigate(`/ai-videos/${p.id}`)}
                onDelete={() => setDeleteTarget(p)}
              />
            ))}
            <button
              onClick={openWizard}
              className="flex flex-col items-center justify-center gap-3 min-h-[280px] bg-page rounded-[var(--radius-lg)] border border-dashed border-border hover:border-primary/50 transition-colors cursor-pointer group"
            >
              <span className="w-12 h-12 flex items-center justify-center bg-primary-light rounded-full group-hover:scale-105 transition-transform">
                <Plus size={20} className="text-primary" />
              </span>
              <span className="text-[13px] font-semibold text-text-muted">新建视频</span>
            </button>
          </div>
        )}
      </main>
      <Footer />

      {models && (
        <CreateWizard
          open={wizardOpen}
          characters={characters}
          models={models}
          onClose={() => setWizardOpen(false)}
          onDone={(pid) => {
            setWizardOpen(false)
            navigate(`/ai-videos/${pid}`)
          }}
        />
      )}
      <ConfirmDialog
        open={deleteTarget != null}
        title="删除视频"
        danger
        confirmText="删除"
        loading={deleting}
        onConfirm={handleDelete}
        onCancel={() => setDeleteTarget(null)}
      >
        确认删除「{deleteTarget?.title}」？分镜、生成的图片 / 视频 / 配音都会一并删除，不可恢复。
      </ConfirmDialog>
    </div>
  )
}
