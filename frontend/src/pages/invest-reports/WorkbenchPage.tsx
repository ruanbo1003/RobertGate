// 投资报告 · 报告工作台：三栏（章节树 / 编辑器 / Agent 面板）+ 资料库抽屉 + 通读模式。

import { useCallback, useEffect, useMemo, useRef, useState } from 'react'
import { Link, useParams } from 'react-router-dom'
import {
  ArrowLeft, BookOpen, Download, FolderOpen, Loader2, Play, RefreshCw, X, Zap,
} from 'lucide-react'
import Modal from '../../components/ui/Modal'
import ChapterTree from '../../components/invest-reports/ChapterTree'
import ParagraphView from '../../components/invest-reports/ParagraphView'
import AgentPanel, { type PanelTab } from '../../components/invest-reports/AgentPanel'
import SourceDrawer from '../../components/invest-reports/SourceDrawer'
import { ChapterStateChip, TypeBadge, ProjectStateChip } from '../../components/invest-reports/badges'
import type {
  ChapterDetail, ChatMessage, ExportPendingItem, FeedEvent, ProjectDetail,
} from '../../types/investReports'
import * as api from '../../services/investReports'

export default function WorkbenchPage() {
  const { projectId } = useParams()
  const pid = Number(projectId)

  const [project, setProject] = useState<ProjectDetail | null>(null)
  const [selectedId, setSelectedId] = useState<number | null>(null)
  const [chapter, setChapter] = useState<ChapterDetail | null>(null)
  const [feed, setFeed] = useState<FeedEvent[]>([])
  const [messages, setMessages] = useState<ChatMessage[]>([])
  const [tab, setTab] = useState<PanelTab>('feed')
  const [drawerOpen, setDrawerOpen] = useState(false)
  const [reading, setReading] = useState(false)
  const [readingChapters, setReadingChapters] = useState<ChapterDetail[] | null>(null)
  const [sending, setSending] = useState(false)
  const [exporting, setExporting] = useState(false)
  const [exportPending, setExportPending] = useState<ExportPendingItem[] | null>(null)
  const [toast, setToast] = useState('')
  const feedCursor = useRef(0)
  const versions = useRef<Map<number, number>>(new Map())

  const notify = (msg: string) => {
    setToast(msg)
    window.setTimeout(() => setToast(''), 3500)
  }

  const loadProject = useCallback(async () => {
    const res = await api.getProject(pid)
    if (res.code === 0) {
      setProject(res.data.project)
      setSelectedId((cur) => cur ?? res.data.project.chapters[0]?.id ?? null)
    } else {
      notify(res.message)
    }
  }, [pid])

  const loadChapter = useCallback(async (cid: number) => {
    const res = await api.getChapter(pid, cid)
    if (res.code === 0) {
      setChapter(res.data.chapter)
      versions.current.set(cid, res.data.chapter.version)
    }
  }, [pid])

  useEffect(() => {
    // 异步取数，setState 发生在 await 之后；规则对此误报
    // eslint-disable-next-line react-hooks/set-state-in-effect
    loadProject()
    api.listChat(pid).then((r) => r.code === 0 && setMessages(r.data.messages))
  }, [pid, loadProject])

  useEffect(() => {
    // 异步取数，setState 发生在 await 之后；规则对此误报
    // eslint-disable-next-line react-hooks/set-state-in-effect
    if (selectedId != null) loadChapter(selectedId)
  }, [selectedId, loadChapter])

  // 状态轮询：章节状态 + 进度流增量 + 版本变化重拉当前章
  useEffect(() => {
    const timer = window.setInterval(async () => {
      const res = await api.getStatus(pid, feedCursor.current)
      if (res.code !== 0) return
      const st = res.data
      if (st.feed.length > 0) {
        feedCursor.current = st.feed[st.feed.length - 1].id
        setFeed((f) => [...f, ...st.feed].slice(-200))
      }
      setProject((p) =>
        p
          ? {
              ...p,
              status: st.status,
              tbd_count: st.tbd_count,
              chapters: p.chapters.map((c) => {
                const s = st.chapters.find((x) => x.id === c.id)
                return s ? { ...c, state: s.state, tbd_count: s.tbd_count, version: s.version, error: s.error } : c
              }),
            }
          : p,
      )
      const cur = st.chapters.find((c) => c.id === selectedId)
      if (cur && selectedId != null && cur.version !== (versions.current.get(selectedId) ?? -1)) {
        loadChapter(selectedId)
      }
    }, 2000)
    return () => window.clearInterval(timer)
  }, [pid, selectedId, loadChapter])

  const selectedMeta = useMemo(
    () => project?.chapters.find((c) => c.id === selectedId) ?? null,
    [project, selectedId],
  )
  const busyChapter = selectedMeta?.state === 'researching' || selectedMeta?.state === 'updating'
  const researchingAny = project?.chapters.some((c) => c.state === 'researching' || c.state === 'updating') ?? false

  const run = async <T,>(fn: () => Promise<{ code: number; message: string; data: T }>, okMsg?: string) => {
    const res = await fn()
    if (res.code !== 0) notify(res.message)
    else if (okMsg) notify(okMsg)
    return res
  }

  const startAll = async () => {
    await run(() => api.startResearch(pid), '已加入研究队列')
    setTab('feed')
    loadProject()
  }

  const handleSend = async (msg: string) => {
    setSending(true)
    setMessages((m) => [...m, { id: Date.now(), role: 'user', content: msg, chapter_id: selectedId, updated_chapter_ids: [], ts: '' }])
    const res = await api.sendChat(pid, msg, selectedId)
    setSending(false)
    if (res.code === 0) {
      setMessages((m) => [...m, { id: Date.now() + 1, role: 'assistant', content: res.data.reply, chapter_id: selectedId, updated_chapter_ids: res.data.updated_chapter_ids, ts: '' }])
      if (selectedId != null && res.data.updated_chapter_ids.includes(selectedId)) loadChapter(selectedId)
    } else {
      notify(res.message)
    }
  }

  const handleExport = async () => {
    setExporting(true)
    const res = await api.exportReport(pid)
    setExporting(false)
    if (res.code === 2045 && res.data && 'pending' in res.data) {
      setExportPending(res.data.pending)
    } else if (res.code === 0 && 'download_url' in res.data) {
      notify('已生成 Word，开始下载')
      if (res.data.download_url !== '#mock-download') window.open(res.data.download_url, '_blank')
    } else {
      notify(res.message)
    }
  }

  const openReading = async () => {
    setReading(true)
    setReadingChapters(null)
    const dones = project?.chapters.filter((c) => c.state === 'done' || c.state === 'stale') ?? []
    const results = await Promise.all(dones.map((c) => api.getChapter(pid, c.id)))
    setReadingChapters(results.filter((r) => r.code === 0).map((r) => r.data.chapter))
  }

  if (!project) {
    return (
      <div className="min-h-screen bg-page flex items-center justify-center">
        <Loader2 size={22} className="animate-spin text-primary" />
      </div>
    )
  }

  return (
    <div className="h-screen flex flex-col bg-page">
      <header className="h-14 shrink-0 flex items-center gap-3 px-5 bg-card border-b border-border">
        <Link to="/invest-reports" aria-label="返回项目列表" className="text-text-primary hover:text-primary">
          <ArrowLeft size={18} />
        </Link>
        <h1 className="text-[15px] font-bold text-text-primary tracking-tight truncate">{project.title}</h1>
        <TypeBadge type={project.type} />
        <ProjectStateChip status={project.status} />
        <div className="flex-1" />
        <button
          onClick={openReading}
          className="inline-flex items-center gap-1.5 h-9 px-3 text-[13px] font-semibold rounded-[var(--radius-sm)] bg-card border border-border text-text-primary hover:bg-page-alt cursor-pointer"
        >
          <BookOpen size={14} />
          通读模式
        </button>
        <button
          onClick={() => setDrawerOpen(true)}
          className="inline-flex items-center gap-1.5 h-9 px-3 text-[13px] font-semibold rounded-[var(--radius-sm)] bg-card border border-border text-text-primary hover:bg-page-alt cursor-pointer"
        >
          <FolderOpen size={14} />
          资料库 · {project.sources.length}
        </button>
        <button
          onClick={startAll}
          disabled={researchingAny}
          className="inline-flex items-center gap-1.5 h-9 px-3 text-[13px] font-semibold rounded-[var(--radius-sm)] bg-accent text-white hover:opacity-90 disabled:opacity-50 cursor-pointer"
        >
          {researchingAny ? <Loader2 size={14} className="animate-spin" /> : <Zap size={14} />}
          批量研究
        </button>
        <button
          onClick={handleExport}
          disabled={exporting}
          className="inline-flex items-center gap-1.5 h-9 px-3.5 text-[13px] font-semibold rounded-[var(--radius-sm)] bg-primary text-white hover:bg-primary-hover disabled:opacity-60 cursor-pointer"
        >
          {exporting ? <Loader2 size={14} className="animate-spin" /> : <Download size={14} />}
          导出 Word
        </button>
      </header>

      <div className="flex-1 min-h-0 flex">
        <ChapterTree chapters={project.chapters} selectedId={selectedId} onSelect={setSelectedId} />

        <main className="flex-1 min-w-0 overflow-y-auto">
          <div className="max-w-[760px] mx-auto px-6 py-7">
            {selectedMeta && (
              <div className="flex items-center gap-2.5 mb-4">
                <h2 className="text-[21px] font-bold text-text-primary tracking-tight">{selectedMeta.title}</h2>
                <ChapterStateChip state={selectedMeta.state} />
                <div className="flex-1" />
                {(selectedMeta.state === 'failed' || selectedMeta.state === 'stale' || selectedMeta.state === 'done') && (
                  <button
                    onClick={() => run(() => api.startResearch(pid, [selectedMeta.id]), '已加入研究队列')}
                    className="inline-flex items-center gap-1 h-8 px-2.5 text-xs font-semibold rounded-[var(--radius-sm)] bg-card border border-border text-text-primary hover:bg-page-alt cursor-pointer"
                  >
                    <RefreshCw size={12} />
                    {selectedMeta.state === 'failed' ? '重试本章' : '重新研究本章'}
                  </button>
                )}
              </div>
            )}

            {selectedMeta?.state === 'failed' && (
              <p role="alert" className="mb-4 px-3.5 py-2.5 rounded-[var(--radius-sm)] bg-error-light text-error text-xs leading-relaxed">
                本章研究失败：{selectedMeta.error ?? '未知错误'}
              </p>
            )}

            {chapter && chapter.id === selectedId && chapter.paragraphs.length > 0 ? (
              <div className="flex flex-col gap-1.5">
                {chapter.paragraphs.map((p) => (
                  <ParagraphView
                    key={p.id}
                    paragraph={p}
                    citations={chapter.citations}
                    tbds={chapter.tbds}
                    busy={busyChapter}
                    onRewrite={async (pidKey, ins) => {
                      await run(() => api.rewriteParagraph(pid, chapter.id, pidKey, ins), '本段已重写')
                      loadChapter(chapter.id)
                    }}
                    onEdit={async (pidKey, text) => {
                      await run(() => api.updateParagraph(pid, chapter.id, pidKey, text))
                      loadChapter(chapter.id)
                    }}
                    onResolveTbd={async (tid, value) => {
                      await run(() => api.resolveTbd(pid, tid, value), '已补充并标注「人工提供」')
                      loadChapter(chapter.id)
                    }}
                  />
                ))}
              </div>
            ) : busyChapter ? (
              <div className="flex flex-col gap-3" aria-label="本章生成中">
                {[0, 1, 2].map((i) => (
                  <div key={i} className="h-16 rounded-[var(--radius-md)] bg-card border border-border animate-pulse" />
                ))}
                <p className="text-xs text-text-muted">Agent 正在研究本章，过程见右侧「研究进度」。</p>
              </div>
            ) : (
              <div className="py-16 flex flex-col items-center gap-3 text-center">
                <p className="text-sm font-semibold text-text-primary">本章还未生成</p>
                <p className="text-xs text-text-muted max-w-[380px] leading-relaxed">
                  {project.sources.length === 0
                    ? '先打开「资料库」上传标的资料（BP / 财务 / 天眼查导出件），再发起研究。'
                    : '点击发起本章研究，Agent 将检索资料与公开信息后成稿。'}
                </p>
                {project.sources.length === 0 ? (
                  <button onClick={() => setDrawerOpen(true)} className="h-10 px-4 text-[13px] font-semibold rounded-[var(--radius-sm)] bg-primary text-white hover:bg-primary-hover cursor-pointer">
                    打开资料库
                  </button>
                ) : (
                  selectedMeta && (
                    <button
                      onClick={() => run(() => api.startResearch(pid, [selectedMeta.id]), '已加入研究队列')}
                      className="inline-flex items-center gap-1.5 h-10 px-4 text-[13px] font-semibold rounded-[var(--radius-sm)] bg-primary text-white hover:bg-primary-hover cursor-pointer"
                    >
                      <Play size={13} />
                      研究本章
                    </button>
                  )
                )}
              </div>
            )}
          </div>
        </main>

        <AgentPanel
          tab={tab}
          onTabChange={setTab}
          feed={feed}
          researching={researchingAny}
          messages={messages}
          citations={chapter?.id === selectedId ? chapter.citations : []}
          chapterTitle={selectedMeta?.title ?? null}
          sending={sending}
          onSend={handleSend}
        />
      </div>

      <SourceDrawer
        open={drawerOpen}
        sources={project.sources}
        checklist={project.checklist}
        onClose={() => setDrawerOpen(false)}
        onUpload={async (files) => {
          await run(() => api.uploadSources(pid, files))
          loadProject()
        }}
        onAddUrl={async (url) => {
          await run(() => api.addUrlSource(pid, url))
          loadProject()
        }}
        onDelete={async (sid) => {
          await run(() => api.deleteSource(pid, sid))
          loadProject()
        }}
        onAnalyzeImpact={async (sid) => {
          const res = await api.analyzeImpact(pid, sid)
          if (res.code !== 0) {
            notify(res.message)
            return []
          }
          return res.data.affected
        }}
        onApplyUpdate={async (chapterIds) => {
          await run(() => api.startResearch(pid, chapterIds), '已开始更新相关章节')
          setTab('feed')
        }}
      />

      <Modal open={exportPending !== null} onClose={() => setExportPending(null)} title="导出被阻止" width={460}>
        <p className="text-[13px] text-text-primary leading-relaxed">
          还有 {exportPending?.length ?? 0} 处「待补充」未处理。请在正文中点击黄色胶囊补充数值（将标注为人工提供），或删除对应表述后再导出。
        </p>
        <ul className="mt-3 flex flex-col gap-1.5">
          {exportPending?.map((p) => (
            <li key={p.tbd_id} className="px-3 py-2 rounded-[var(--radius-sm)] bg-warning-light text-xs text-warning">
              {project.chapters.find((c) => c.id === p.chapter_id)?.title ?? `章节 ${p.chapter_id}`}：{p.reason}
            </li>
          ))}
        </ul>
      </Modal>

      {reading && (
        <div className="fixed inset-0 z-50 bg-page overflow-y-auto">
          <div className="sticky top-0 bg-card border-b border-border h-14 flex items-center justify-between px-6">
            <h2 className="text-sm font-bold text-text-primary">通读 · {project.title}</h2>
            <button
              onClick={() => setReading(false)}
              aria-label="退出通读模式"
              className="inline-flex items-center gap-1.5 h-9 px-3 text-[13px] font-semibold rounded-[var(--radius-sm)] border border-border text-text-primary hover:bg-page-alt cursor-pointer"
            >
              <X size={14} />
              退出通读
            </button>
          </div>
          <div className="max-w-[760px] mx-auto px-6 py-8">
            {!readingChapters ? (
              <Loader2 size={20} className="animate-spin text-primary mx-auto" />
            ) : readingChapters.length === 0 ? (
              <p className="text-sm text-text-muted text-center py-16">还没有已完成的章节。</p>
            ) : (
              readingChapters.map((c) => (
                <section key={c.id} className="mb-9">
                  <h3 className="text-lg font-bold text-text-primary mb-3">{c.title}</h3>
                  {c.paragraphs.map((p) => (
                    <p key={p.id} className="text-sm leading-[1.9] text-text-primary mb-3">
                      {p.text.replace(/⟦[^⟧]+⟧/g, '')}
                    </p>
                  ))}
                </section>
              ))
            )}
          </div>
        </div>
      )}

      {toast && (
        <div aria-live="polite" className="fixed bottom-6 left-1/2 -translate-x-1/2 z-50 px-4 py-2.5 rounded-[var(--radius-md)] bg-text-primary text-white text-[13px] shadow-[0_8px_32px_rgba(0,0,0,0.2)]">
          {toast}
        </div>
      )}
    </div>
  )
}
