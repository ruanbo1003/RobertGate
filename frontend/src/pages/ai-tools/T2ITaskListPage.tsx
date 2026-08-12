import { useCallback, useEffect, useRef, useState } from 'react'
import { useNavigate, useParams } from 'react-router-dom'
import { motion } from 'framer-motion'
import { ChevronLeft, ChevronRight, Plus, Settings } from 'lucide-react'
import {
  createTask,
  deleteTemplate,
  getTemplates,
  listTasks,
  updateTemplate,
} from '../../services/t2i'
import { useAuth } from '../../store/AuthContext'
import type { T2ITaskSummary, T2ITemplate, T2ITemplateCode } from '../../types/t2i'
import T2ITaskCard from '../../components/t2i/T2ITaskCard'
import T2ITaskCreateModal from '../../components/t2i/T2ITaskCreateModal'
import T2ITemplateEditModal from '../../components/t2i/T2ITemplateEditModal'

const PAGE_SIZE = 20

export default function T2ITaskListPage() {
  const { templateCode } = useParams<{ templateCode: T2ITemplateCode }>()
  const navigate = useNavigate()
  const { user } = useAuth()
  const isAdmin = user?.role === 'admin'

  const [template, setTemplate] = useState<T2ITemplate | null>(null)
  const [tasks, setTasks] = useState<T2ITaskSummary[]>([])
  const [total, setTotal] = useState(0)
  const [page, setPage] = useState(1)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [createOpen, setCreateOpen] = useState(false)
  const [tplEditOpen, setTplEditOpen] = useState(false)
  const [toast, setToast] = useState<string | null>(null)

  const totalPages = Math.max(1, Math.ceil(total / PAGE_SIZE))

  // 拉模板
  useEffect(() => {
    let mounted = true
    getTemplates().then((res) => {
      if (!mounted) return
      if (res.code === 0) {
        const tpl = res.data.templates.find((t) => t.code === templateCode) ?? null
        setTemplate(tpl)
      }
    })
    return () => {
      mounted = false
    }
  }, [templateCode])

  // 拉任务
  const load = useCallback(
    async (targetPage: number) => {
      if (!templateCode) return
      setLoading(true)
      const res = await listTasks(templateCode, targetPage, PAGE_SIZE)
      if (res.code === 0 && res.data) {
        setTasks(res.data.items)
        setTotal(res.data.total)
        setError(null)
      } else {
        setError(res.message)
      }
      setLoading(false)
    },
    [templateCode],
  )

  useEffect(() => {
    setPage(1)
    load(1)
  }, [templateCode, load])

  // 有 generating 任务时轮询更新
  const pollingRef = useRef<number | null>(null)
  useEffect(() => {
    const hasGenerating = tasks.some((t) => t.status === 'generating')
    if (!hasGenerating) return
    pollingRef.current = window.setInterval(() => load(page), 2500)
    return () => {
      if (pollingRef.current) window.clearInterval(pollingRef.current)
    }
  }, [tasks, page, load])

  const handleCreate = async (keywords: Record<string, string>) => {
    if (!templateCode) return
    const res = await createTask(templateCode, keywords)
    if (res.code !== 0 || !res.data) {
      throw new Error(res.message)
    }
    setCreateOpen(false)
    if (res.data.existing) {
      setToast('任务已存在，已为你打开')
      setTimeout(() => setToast(null), 2200)
      navigate(`/ai-tools/text-to-image/${templateCode}/${res.data.task.id}`)
    } else {
      // 回到第 1 页看到新任务
      setPage(1)
      load(1)
    }
  }

  const handleTemplateUpdate = async (payload: {
    code: string
    name: string
    description: string
    prompt: string
    order_index: number
  }) => {
    if (!template) return
    const res = await updateTemplate(template.id, {
      name: payload.name,
      description: payload.description || null,
      prompt: payload.prompt,
      order_index: payload.order_index,
    })
    if (res.code !== 0 || !res.data) {
      throw new Error(res.message)
    }
    setTemplate(res.data)
    setTplEditOpen(false)
    setToast('模板已更新')
    setTimeout(() => setToast(null), 2000)
  }

  const handleTemplateDelete = async (tpl: T2ITemplate) => {
    const res = await deleteTemplate(tpl.id)
    if (res.code !== 0) {
      throw new Error(res.message)
    }
    setTplEditOpen(false)
    // 已删除当前模板，跳回文生图默认页
    navigate('/ai-tools/text-to-image/playground', { replace: true })
  }

  const gotoPage = (p: number) => {
    if (p < 1 || p > totalPages || p === page) return
    setPage(p)
    load(p)
  }

  return (
    <div className="max-w-6xl mx-auto flex flex-col gap-6">
      {/* 页头 */}
      <div className="flex items-start justify-between gap-4">
        <div className="min-w-0">
          <div className="flex items-center gap-1.5">
            <h1 className="text-2xl font-bold text-text-primary tracking-tight">
              {template?.name ?? '文生图'}
            </h1>
            {isAdmin && template && !template.is_builtin && (
              <button
                onClick={() => setTplEditOpen(true)}
                className="w-8 h-8 inline-flex items-center justify-center rounded-full text-text-muted hover:text-primary hover:bg-primary-light transition-colors cursor-pointer"
                aria-label="模板设置"
                title="模板设置"
              >
                <Settings size={16} />
              </button>
            )}
          </div>
          {template?.description && (
            <p className="text-sm text-text-muted mt-1">{template.description}</p>
          )}
        </div>
        {isAdmin && template && (
          <motion.button
            whileHover={{ scale: 1.01 }}
            whileTap={{ scale: 0.98 }}
            onClick={() => setCreateOpen(true)}
            className="shrink-0 inline-flex items-center gap-1.5 h-11 px-4 bg-primary text-text-on-primary text-sm font-semibold rounded-[var(--radius-sm)] hover:bg-primary-hover transition-colors cursor-pointer"
          >
            <Plus size={16} />
            新建任务
          </motion.button>
        )}
      </div>

      {/* 内容区 */}
      {loading && tasks.length === 0 ? (
        <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
          {[0, 1, 2, 3, 4, 5].map((i) => (
            <div
              key={i}
              className="h-64 bg-card border border-border rounded-[var(--radius-lg)] animate-pulse"
            />
          ))}
        </div>
      ) : error ? (
        <div className="bg-card border border-border rounded-[var(--radius-lg)] p-12 text-center">
          <p className="text-sm text-error">{error}</p>
        </div>
      ) : tasks.length === 0 ? (
        <div className="bg-card border border-border rounded-[var(--radius-lg)] p-16 text-center">
          <div className="text-4xl mb-3">🎨</div>
          <p className="text-sm text-text-muted">
            还没有任务{isAdmin ? '，点右上角新建' : ''}
          </p>
        </div>
      ) : (
        <>
          <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
            {tasks.map((t) => (
              <T2ITaskCard
                key={t.id}
                task={t}
                templateCode={templateCode as T2ITemplateCode}
              />
            ))}
          </div>

          {/* 分页 */}
          {totalPages > 1 && (
            <div className="flex items-center justify-center gap-1 mt-2">
              <button
                onClick={() => gotoPage(page - 1)}
                disabled={page === 1}
                className="w-9 h-9 inline-flex items-center justify-center rounded-[var(--radius-sm)] border border-border text-text-secondary hover:border-primary hover:text-primary disabled:opacity-40 disabled:cursor-not-allowed transition-colors cursor-pointer"
                aria-label="上一页"
              >
                <ChevronLeft size={16} />
              </button>
              {Array.from({ length: totalPages }, (_, i) => i + 1).map((p) => (
                <button
                  key={p}
                  onClick={() => gotoPage(p)}
                  className={`min-w-9 h-9 px-3 inline-flex items-center justify-center rounded-[var(--radius-sm)] text-sm font-semibold transition-colors cursor-pointer ${
                    p === page
                      ? 'bg-primary text-text-on-primary'
                      : 'border border-border text-text-secondary hover:border-primary hover:text-primary'
                  }`}
                >
                  {p}
                </button>
              ))}
              <button
                onClick={() => gotoPage(page + 1)}
                disabled={page === totalPages}
                className="w-9 h-9 inline-flex items-center justify-center rounded-[var(--radius-sm)] border border-border text-text-secondary hover:border-primary hover:text-primary disabled:opacity-40 disabled:cursor-not-allowed transition-colors cursor-pointer"
                aria-label="下一页"
              >
                <ChevronRight size={16} />
              </button>
            </div>
          )}
        </>
      )}

      {/* Toast */}
      {toast && (
        <div className="fixed bottom-6 left-1/2 -translate-x-1/2 z-40 bg-text-primary text-white text-sm px-4 py-2 rounded-full shadow-lg">
          {toast}
        </div>
      )}

      <T2ITaskCreateModal
        open={createOpen}
        template={template}
        onClose={() => setCreateOpen(false)}
        onSubmit={handleCreate}
      />

      {isAdmin && template && !template.is_builtin && (
        <T2ITemplateEditModal
          open={tplEditOpen}
          template={template}
          nextOrderIndex={template.order_index}
          onClose={() => setTplEditOpen(false)}
          onSubmit={handleTemplateUpdate}
          onDelete={handleTemplateDelete}
        />
      )}
    </div>
  )
}
