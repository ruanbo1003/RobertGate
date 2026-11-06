// 投资报告 · 项目列表：新建报告（模板硬门槛）+ 项目卡片网格。

import { useCallback, useEffect, useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { ChevronRight, Library, Plus } from 'lucide-react'
import Navbar from '../../components/layout/Navbar'
import Modal from '../../components/ui/Modal'
import ReportCard from '../../components/invest-reports/ReportCard'
import type { ProjectSummary, ReportType } from '../../types/investReports'
import { createProject, listProjects } from '../../services/investReports'

export default function ProjectListPage() {
  const navigate = useNavigate()
  const [items, setItems] = useState<ProjectSummary[] | null>(null)
  const [error, setError] = useState('')
  const [creating, setCreating] = useState(false)
  const [dialogOpen, setDialogOpen] = useState(false)
  const [title, setTitle] = useState('')
  const [type, setType] = useState<ReportType>('advice')
  const [dialogError, setDialogError] = useState('')

  const load = useCallback(async () => {
    const res = await listProjects()
    if (res.code === 0) setItems(res.data.items)
    else setError(res.message)
  }, [])

  useEffect(() => {
    // 异步取数，setState 发生在 await 之后；规则对此误报
    // eslint-disable-next-line react-hooks/set-state-in-effect
    load()
    const timer = window.setInterval(load, 5000)
    return () => window.clearInterval(timer)
  }, [load])

  const submit = async () => {
    if (!title.trim()) return
    setCreating(true)
    setDialogError('')
    const res = await createProject(title.trim(), type)
    setCreating(false)
    if (res.code === 0) {
      setDialogOpen(false)
      setTitle('')
      navigate(`/invest-reports/${res.data.project.id}`)
    } else {
      setDialogError(res.message)
    }
  }

  return (
    <div className="min-h-screen bg-page">
      <Navbar />
      <header className="bg-card border-b border-border">
        <div className="max-w-6xl mx-auto px-5 h-14 flex items-center gap-2">
          <span className="text-[13px] text-text-muted">投资报告</span>
          <ChevronRight size={14} className="text-text-muted" />
          <h1 className="text-base font-bold text-text-primary tracking-tight">报告项目</h1>
          <div className="flex-1" />
          <Link
            to="/invest-reports/library"
            className="inline-flex items-center gap-1.5 h-9 px-3.5 text-[13px] font-semibold rounded-[var(--radius-sm)] bg-card border border-border text-text-primary hover:bg-page-alt transition-colors"
          >
            <Library size={14} />
            范本库
          </Link>
          <button
            onClick={() => setDialogOpen(true)}
            className="ml-2 inline-flex items-center gap-1.5 h-9 px-3.5 text-[13px] font-semibold rounded-[var(--radius-sm)] bg-primary text-white hover:bg-primary-hover transition-colors cursor-pointer"
          >
            <Plus size={14} />
            新建报告
          </button>
        </div>
      </header>

      <main className="max-w-6xl mx-auto px-5 py-6">
        {error && <p role="alert" className="mb-4 px-3.5 py-2.5 rounded-[var(--radius-sm)] bg-error-light text-error text-xs">{error}</p>}
        {!items ? (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-5">
            {[0, 1, 2].map((i) => (
              <div key={i} className="h-40 rounded-2xl bg-card border border-border animate-pulse" />
            ))}
          </div>
        ) : items.length === 0 ? (
          <div className="py-24 flex flex-col items-center gap-3 text-center">
            <p className="text-sm font-semibold text-text-primary">还没有报告项目</p>
            <p className="text-xs text-text-muted">先到范本库上传历史报告并学习模板，再回来新建报告。</p>
            <Link to="/invest-reports/library" className="mt-1 h-10 px-4 inline-flex items-center text-[13px] font-semibold rounded-[var(--radius-sm)] bg-primary text-white hover:bg-primary-hover">
              去范本库
            </Link>
          </div>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-5">
            {items.map((p) => (
              <ReportCard key={p.id} project={p} onOpen={() => navigate(`/invest-reports/${p.id}`)} />
            ))}
          </div>
        )}
      </main>

      <Modal open={dialogOpen} onClose={() => setDialogOpen(false)} title="新建报告" width={440}>
        <div className="flex flex-col gap-4">
          <div className="flex flex-col gap-1.5">
            <label htmlFor="ir-title" className="text-[13px] font-semibold text-text-primary">报告名称</label>
            <input
              id="ir-title"
              value={title}
              onChange={(e) => setTitle(e.target.value)}
              onKeyDown={(e) => e.key === 'Enter' && submit()}
              placeholder="如：云帆科技 · A 轮"
              className="h-11 px-3 text-base bg-card border border-border rounded-[var(--radius-sm)] text-text-primary placeholder:text-text-muted focus:outline-none focus:ring-2 focus:ring-primary/30 focus:border-primary"
            />
          </div>
          <div className="flex flex-col gap-1.5">
            <span className="text-[13px] font-semibold text-text-primary">报告类型</span>
            <div className="flex gap-2.5">
              {(
                [
                  ['advice', '投资建议书', '给出投/不投结论'],
                  ['dd', '尽调报告', '提示风险供决策'],
                ] as Array<[ReportType, string, string]>
              ).map(([t, label, desc]) => (
                <button
                  key={t}
                  onClick={() => setType(t)}
                  aria-pressed={type === t}
                  className={`flex-1 px-3 py-2.5 rounded-[var(--radius-md)] border text-left transition-colors cursor-pointer ${
                    type === t ? 'border-primary bg-primary-light' : 'border-border bg-card hover:bg-page-alt'
                  }`}
                >
                  <span className="block text-[13px] font-bold text-text-primary">{label}</span>
                  <span className="block mt-0.5 text-[11px] text-text-muted">{desc}</span>
                </button>
              ))}
            </div>
          </div>
          {dialogError && <p role="alert" className="px-3 py-2 rounded-[var(--radius-sm)] bg-error-light text-error text-xs">{dialogError}</p>}
          <button
            onClick={submit}
            disabled={creating || !title.trim()}
            className="h-11 text-sm font-semibold rounded-[var(--radius-sm)] bg-primary text-white hover:bg-primary-hover disabled:opacity-50 transition-colors cursor-pointer"
          >
            {creating ? '创建中…' : '创建并进入工作台'}
          </button>
        </div>
      </Modal>
    </div>
  )
}
