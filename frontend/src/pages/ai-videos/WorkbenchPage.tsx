import { useCallback, useEffect, useMemo, useRef, useState } from 'react'
import { Link, useNavigate, useParams } from 'react-router-dom'
import { ArrowLeft, FileText, MonitorX, X } from 'lucide-react'
import ShotTrack from '../../components/ai-videos/ShotTrack'
import ShotEditor from '../../components/ai-videos/ShotEditor'
import GlobalPanel from '../../components/ai-videos/GlobalPanel'
import ScriptDrawer from '../../components/ai-videos/ScriptDrawer'
import ConfirmDialog from '../../components/ai-videos/ConfirmDialog'
import type {
  AssetKind,
  ModelsMap,
  ProjectDetail,
  ProjectStatusResponse,
  Script,
  ShotPatch,
  StaleItem,
} from '../../types/aiVideos'
import {
  cancelQueue,
  composeProject,
  createShot,
  deleteShot,
  downloadUrl,
  generateAll,
  generateAsset,
  getModels,
  getProject,
  getProjectStatus,
  reorderShots,
  splitShots,
  updateScript,
  updateShot,
  generateScript,
  updateProject,
} from '../../services/aiVideos'

const STATUS_LABEL: Record<string, { label: string; cls: string }> = {
  draft: { label: '草稿', cls: 'bg-page-alt text-text-muted' },
  generating: { label: '生成中', cls: 'bg-primary-light text-primary' },
  partial_failed: { label: '部分失败', cls: 'bg-error-light text-error' },
  completed: { label: '已完成', cls: 'bg-success-light text-success' },
}

export default function WorkbenchPage() {
  const { projectId } = useParams()
  const pid = Number(projectId)
  const navigate = useNavigate()

  const [project, setProject] = useState<ProjectDetail | null>(null)
  const [models, setModels] = useState<ModelsMap | null>(null)
  const [status, setStatus] = useState<ProjectStatusResponse | null>(null)
  const [selectedId, setSelectedId] = useState<number | null>(null)
  const [loading, setLoading] = useState(true)
  const [notFound, setNotFound] = useState(false)
  const [banner, setBanner] = useState('')
  const [scriptOpen, setScriptOpen] = useState(false)
  const [scriptSaving, setScriptSaving] = useState(false)
  const [scriptGenerating, setScriptGenerating] = useState(false)
  const [scriptGenError, setScriptGenError] = useState('')
  const [scriptVersion, setScriptVersion] = useState(0)
  const [composeBusy, setComposeBusy] = useState(false)
  const [staleConfirm, setStaleConfirm] = useState<StaleItem[] | null>(null)
  const [resplitScript, setResplitScript] = useState<Script | null>(null)
  const [deleteShotId, setDeleteShotId] = useState<number | null>(null)
  const bannerTimer = useRef<ReturnType<typeof setTimeout> | null>(null)

  const showBanner = useCallback((msg: string) => {
    setBanner(msg)
    if (bannerTimer.current) clearTimeout(bannerTimer.current)
    bannerTimer.current = setTimeout(() => setBanner(''), 6000)
  }, [])

  const reload = useCallback(() => {
    return getProject(pid).then((res) => {
      if (res.code !== 0 || !res.data) {
        setNotFound(true)
        setLoading(false)
        return
      }
      const proj = res.data.project
      setProject(proj)
      setSelectedId((prev) =>
        prev != null && proj.shots.some((s) => s.id === prev) ? prev : (proj.shots[0]?.id ?? null),
      )
      setLoading(false)
    })
  }, [pid])

  useEffect(() => {
    void reload()
    void getModels().then((res) => {
      if (res.code === 0 && res.data) setModels(res.data.models)
    })
  }, [reload])

  // 轮询聚合状态，把产物状态合并进本地分镜（不覆盖正在编辑的文案字段）
  useEffect(() => {
    if (loading || notFound) return
    const timer = setInterval(async () => {
      const res = await getProjectStatus(pid)
      if (res.code !== 0 || !res.data) return
      const st = res.data
      setStatus(st)
      setProject((prev) => {
        if (!prev) return prev
        const byId = new Map(st.shots.map((s) => [s.id, s]))
        return {
          ...prev,
          status: st.status,
          compose: st.compose,
          shots: prev.shots.map((shot) => {
            const s = byId.get(shot.id)
            if (!s) return shot
            return {
              ...shot,
              image: { ...shot.image, ...s.image },
              video: { ...shot.video, ...s.video },
              // 对白镜 audio 恒为 null（has_dialogue 不随轮询变化），本地已 null 就不用服务端片段重建
              audio: shot.audio ? (s.audio ? { ...shot.audio, ...s.audio } : shot.audio) : null,
            }
          }),
        }
      })
    }, 2500)
    return () => clearInterval(timer)
  }, [pid, loading, notFound])

  const selectedShot = useMemo(
    () => project?.shots.find((s) => s.id === selectedId) ?? null,
    [project, selectedId],
  )
  const handlePatch = async (patch: ShotPatch) => {
    if (!selectedShot) return
    const res = await updateShot(pid, selectedShot.id, patch)
    if (res.code !== 0 || !res.data) {
      showBanner(res.message)
      return
    }
    const updated = res.data.shot
    setProject((prev) =>
      prev
        ? { ...prev, shots: prev.shots.map((s) => (s.id === updated.id ? updated : s)) }
        : prev,
    )
  }

  const handleGenerate = async (kind: AssetKind, model: string, voice?: string) => {
    if (!selectedShot) return
    const res = await generateAsset(pid, selectedShot.id, kind, model, voice)
    if (res.code !== 0) {
      showBanner(res.message)
      return
    }
    setProject((prev) =>
      prev
        ? {
            ...prev,
            shots: prev.shots.map((s) =>
              s.id === selectedShot.id
                ? { ...s, [kind]: { ...s[kind], state: 'pending' as const, error: null } }
                : s,
            ),
          }
        : prev,
    )
  }

  const handleAddShot = async () => {
    const res = await createShot(pid, selectedId)
    if (res.code !== 0 || !res.data) {
      showBanner(res.message)
      return
    }
    await reload()
    setSelectedId(res.data.shot.id)
  }

  const handleMove = async (id: number, dir: -1 | 1) => {
    if (!project) return
    const ids = project.shots.map((s) => s.id)
    const idx = ids.indexOf(id)
    const target = idx + dir
    if (target < 0 || target >= ids.length) return
    ;[ids[idx], ids[target]] = [ids[target], ids[idx]]
    const res = await reorderShots(pid, ids)
    if (res.code !== 0) {
      showBanner(res.message)
      return
    }
    void reload()
  }

  const handleDeleteShot = async () => {
    if (deleteShotId == null) return
    const res = await deleteShot(pid, deleteShotId)
    setDeleteShotId(null)
    if (res.code !== 0) {
      showBanner(res.message)
      return
    }
    setSelectedId(null)
    void reload()
  }

  const handleGenerateAll = async () => {
    const res = await generateAll(pid, { types: ['image', 'video', 'audio'], scope: 'missing' })
    if (res.code !== 0) {
      showBanner(res.message)
      return
    }
    void reload()
  }

  const handleCompose = async (ignoreStale: boolean) => {
    setComposeBusy(true)
    const res = await composeProject(pid, ignoreStale)
    setComposeBusy(false)
    if (res.code === 2004) {
      const data = res.data as unknown as { stale_items: StaleItem[] } | null
      setStaleConfirm(data?.stale_items ?? [])
      return
    }
    if (res.code !== 0) {
      showBanner(res.message)
      return
    }
    void reload()
  }

  const handleScriptGenerate = async (synopsis: string) => {
    if (!project) return
    setScriptGenerating(true)
    setScriptGenError('')
    if (synopsis && synopsis !== project.synopsis) {
      const up = await updateProject(pid, { synopsis })
      if (up.code !== 0) {
        setScriptGenError(up.message)
        setScriptGenerating(false)
        return
      }
      setProject((prev) => (prev ? { ...prev, synopsis } : prev))
    }
    const res = await generateScript(pid, project.default_models.llm)
    setScriptGenerating(false)
    if (res.code !== 0 || !res.data) {
      setScriptGenError(res.message || '生成失败，请重试')
      return
    }
    const script = res.data.script
    setProject((prev) => (prev ? { ...prev, script } : prev))
    setScriptVersion((v) => v + 1)
  }

  const handleScriptSave = async (script: Script) => {
    setScriptSaving(true)
    const res = await updateScript(pid, script)
    setScriptSaving(false)
    if (res.code !== 0) {
      showBanner(res.message)
      return
    }
    setProject((prev) => (prev ? { ...prev, script } : prev))
    setScriptOpen(false)
  }

  const handleResplit = async () => {
    if (!resplitScript) return
    setScriptSaving(true)
    const saveRes = await updateScript(pid, resplitScript)
    if (saveRes.code !== 0) {
      setScriptSaving(false)
      showBanner(saveRes.message)
      return
    }
    const res = await splitShots(pid, project?.default_models.llm ?? '', true)
    setScriptSaving(false)
    setResplitScript(null)
    setScriptOpen(false)
    if (res.code !== 0) {
      showBanner(res.message)
      return
    }
    setSelectedId(null)
    void reload()
  }

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-page">
        <div className="w-8 h-8 border-[3px] border-primary/20 border-t-primary rounded-full animate-spin" />
      </div>
    )
  }

  if (notFound || !project) {
    return (
      <div className="min-h-screen flex flex-col items-center justify-center gap-4 bg-page">
        <p className="text-base font-bold text-text-primary">项目不存在或已被删除</p>
        <button
          onClick={() => navigate('/ai-videos')}
          className="flex items-center gap-2 h-11 px-5 bg-primary hover:bg-primary-hover text-white text-sm font-semibold rounded-[var(--radius-sm)] transition-colors cursor-pointer"
        >
          <ArrowLeft size={15} />
          返回列表
        </button>
      </div>
    )
  }

  const statusMeta = STATUS_LABEL[project.status] ?? STATUS_LABEL.draft

  return (
    <>
      {/* 工作台为桌面端专用 */}
      <div className="lg:hidden min-h-screen flex flex-col items-center justify-center gap-4 bg-page px-8 text-center">
        <MonitorX size={32} className="text-text-muted" />
        <p className="text-base font-bold text-text-primary">创作工作台仅支持桌面端</p>
        <p className="text-sm text-text-muted">请在更宽的屏幕上打开此页面</p>
        <Link
          to="/ai-videos"
          className="flex items-center gap-2 h-11 px-5 bg-primary text-white text-sm font-semibold rounded-[var(--radius-sm)]"
        >
          <ArrowLeft size={15} />
          返回列表
        </Link>
      </div>

      <div className="hidden lg:flex flex-col h-screen bg-page overflow-hidden">
        {/* 顶部工具栏 */}
        <header className="h-14 shrink-0 flex items-center justify-between px-5 bg-card border-b border-border">
          <div className="flex items-center gap-3 min-w-0">
            <Link
              to="/ai-videos"
              aria-label="返回列表"
              className="w-9 h-9 flex items-center justify-center rounded-[var(--radius-sm)] text-text-muted hover:text-text-primary hover:bg-page transition-colors"
            >
              <ArrowLeft size={17} />
            </Link>
            <h1 className="text-[15px] font-bold text-text-primary truncate">{project.title}</h1>
            <span
              className={`shrink-0 px-2.5 py-1 rounded-full text-[11px] font-semibold ${statusMeta.cls}`}
            >
              {statusMeta.label}
            </span>
          </div>
          <button
            onClick={() => setScriptOpen(true)}
            className="flex items-center gap-1.5 h-9 px-3.5 text-[13px] font-semibold text-text-primary bg-card border border-border rounded-[var(--radius-sm)] hover:bg-page transition-colors cursor-pointer"
          >
            <FileText size={14} />
            剧本
          </button>
        </header>

        {banner && (
          <div className="shrink-0 flex items-center justify-between gap-3 px-5 py-2.5 bg-error-light">
            <p className="text-xs text-error">{banner}</p>
            <button
              onClick={() => setBanner('')}
              aria-label="关闭提示"
              className="text-error hover:opacity-70 cursor-pointer"
            >
              <X size={13} />
            </button>
          </div>
        )}

        {/* 三栏主体 */}
        <div className="flex-1 flex min-h-0">
          <ShotTrack
            shots={project.shots}
            selectedId={selectedId}
            onSelect={setSelectedId}
            onAdd={handleAddShot}
            onMove={handleMove}
          />
          {selectedShot && models ? (
            <ShotEditor
              key={selectedShot.id}
              shot={selectedShot}
              characters={project.characters}
              models={models}
              defaultVoice={project.tts_voice}
              onPatch={handlePatch}
              onGenerate={handleGenerate}
              onDelete={() => setDeleteShotId(selectedShot.id)}
            />
          ) : (
            <section className="flex-1 flex items-center justify-center">
              <p className="text-sm text-text-muted">
                {project.shots.length === 0 ? '先在「剧本」里拆分镜' : '选择左侧分镜开始编辑'}
              </p>
            </section>
          )}
          <GlobalPanel
            shot={selectedShot}
            status={status}
            onGenerateAll={handleGenerateAll}
            onCancelQueue={() => void cancelQueue(pid)}
            onCompose={() => void handleCompose(false)}
            composeBusy={composeBusy}
            downloadHref={downloadUrl(pid)}
          />
        </div>
      </div>

      <ScriptDrawer
        open={scriptOpen}
        script={project.script}
        synopsis={project.synopsis}
        generating={scriptGenerating}
        generateError={scriptGenError}
        scriptVersion={scriptVersion}
        onGenerate={handleScriptGenerate}
        characters={project.characters}
        saving={scriptSaving}
        onClose={() => setScriptOpen(false)}
        onSave={handleScriptSave}
        onResplit={(script) => setResplitScript(script)}
      />

      {/* 重拆分镜确认 */}
      <ConfirmDialog
        open={resplitScript != null}
        title="重新拆分镜"
        danger
        confirmText="重拆并清空产物"
        loading={scriptSaving}
        onConfirm={handleResplit}
        onCancel={() => setResplitScript(null)}
      >
        将按当前剧本重新拆分镜，现有 {project.shots.length} 个分镜及其已生成的图片 / 视频 /
        配音会全部删除，不可恢复。确定继续？
      </ConfirmDialog>

      {/* 过期产物合成确认 */}
      <ConfirmDialog
        open={staleConfirm != null}
        title="存在过期产物"
        confirmText="仍然合成"
        loading={composeBusy}
        onConfirm={() => {
          setStaleConfirm(null)
          void handleCompose(true)
        }}
        onCancel={() => setStaleConfirm(null)}
      >
        <p className="mb-2">以下产物在上游修改后未重新生成，继续合成可能出现画面与字幕不一致：</p>
        <ul className="list-disc pl-5 flex flex-col gap-0.5">
          {(staleConfirm ?? []).map((item, i) => (
            <li key={i} className="text-xs">
              镜 {item.shot_order} ·{' '}
              {item.kind === 'image' ? '分镜图' : item.kind === 'video' ? '视频' : '配音'}
            </li>
          ))}
        </ul>
      </ConfirmDialog>

      {/* 删除分镜确认 */}
      <ConfirmDialog
        open={deleteShotId != null}
        title="删除分镜"
        danger
        confirmText="删除"
        onConfirm={handleDeleteShot}
        onCancel={() => setDeleteShotId(null)}
      >
        确认删除该分镜？已生成的图片 / 视频 / 配音会一并删除。
      </ConfirmDialog>
    </>
  )
}
