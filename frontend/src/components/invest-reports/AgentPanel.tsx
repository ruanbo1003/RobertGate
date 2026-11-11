// 右栏：Agent 对话 / 研究进度 / 本章引用 三 Tab + 底部常驻对话输入。

import { useEffect, useRef, useState } from 'react'
import {
  Check, ExternalLink, FileText, Globe, Loader2, PenLine, Search, Send, Table2, TriangleAlert,
} from 'lucide-react'
import type { ChatMessage, Citation, FeedEvent } from '../../types/investReports'

export type PanelTab = 'chat' | 'feed' | 'citations'

interface AgentPanelProps {
  tab: PanelTab
  onTabChange: (t: PanelTab) => void
  feed: FeedEvent[]
  researching: boolean
  messages: ChatMessage[]
  citations: Citation[]
  chapterTitle: string | null
  sending: boolean
  onSend: (message: string) => void
}

const FEED_ICON: Record<FeedEvent['kind'], typeof Search> = {
  search: Search, read_url: Globe, read_source: FileText, extract: Table2,
  write: PenLine, done: Check, error: TriangleAlert,
}

const TABS: Array<{ key: PanelTab; label: string }> = [
  { key: 'chat', label: 'Agent 对话' },
  { key: 'feed', label: '研究进度' },
  { key: 'citations', label: '本章引用' },
]

export default function AgentPanel({
  tab, onTabChange, feed, researching, messages, citations, chapterTitle, sending, onSend,
}: AgentPanelProps) {
  const [input, setInput] = useState('')
  const scrollRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    scrollRef.current?.scrollTo({ top: scrollRef.current.scrollHeight })
  }, [feed.length, messages.length, tab])

  const send = () => {
    const msg = input.trim()
    if (!msg || sending) return
    setInput('')
    onSend(msg)
  }

  return (
    <aside className="w-[360px] shrink-0 h-full flex flex-col bg-card border-l border-border">
      <div className="flex border-b border-border" role="tablist" aria-label="Agent 面板">
        {TABS.map((t) => (
          <button
            key={t.key}
            role="tab"
            aria-selected={tab === t.key}
            onClick={() => onTabChange(t.key)}
            className={`flex-1 h-11 text-[13px] font-semibold transition-colors cursor-pointer ${
              tab === t.key ? 'text-primary border-b-2 border-primary' : 'text-text-muted hover:text-text-primary'
            }`}
          >
            {t.label}
          </button>
        ))}
      </div>

      <div ref={scrollRef} className="flex-1 overflow-y-auto px-4 py-3.5">
        {tab === 'feed' && (
          <div className="flex flex-col gap-2.5">
            {feed.length === 0 ? (
              <p className="text-xs text-text-muted py-6 text-center">还没有研究动作。点「批量研究」或在章节里发起。</p>
            ) : (
              feed.map((e) => {
                const Icon = FEED_ICON[e.kind]
                const running = e.kind === 'write' && researching
                return (
                  <div
                    key={e.id}
                    className={`flex items-center gap-2 px-2.5 py-2 rounded-[var(--radius-sm)] ${
                      e.kind === 'error' ? 'bg-error-light' : running ? 'bg-warning-light' : 'bg-page-alt'
                    }`}
                  >
                    <Icon size={13} className={e.kind === 'error' ? 'text-error' : running ? 'text-warning' : 'text-text-muted'} />
                    <p className="flex-1 min-w-0 text-xs leading-relaxed text-text-primary">{e.text}</p>
                    {e.ref?.url && (
                      <a href={e.ref.url} target="_blank" rel="noreferrer" aria-label="打开来源链接" className="text-primary shrink-0">
                        <ExternalLink size={12} />
                      </a>
                    )}
                    {running ? (
                      <Loader2 size={12} className="animate-spin text-warning shrink-0" />
                    ) : e.kind === 'done' ? (
                      <Check size={12} className="text-success shrink-0" />
                    ) : null}
                  </div>
                )
              })
            )}
          </div>
        )}

        {tab === 'chat' && (
          <div className="flex flex-col gap-3">
            {messages.length === 0 ? (
              <p className="text-xs text-text-muted py-6 text-center">
                和 Agent 讨论报告：指出问题、要求补充、粘贴 URL 作为新资料。
              </p>
            ) : (
              messages.map((m) => (
                <div
                  key={m.id}
                  className={`max-w-[85%] px-3 py-2 rounded-[var(--radius-md)] text-[13px] leading-relaxed ${
                    m.role === 'user' ? 'self-end bg-primary text-white' : 'self-start bg-page-alt text-text-primary'
                  }`}
                >
                  {m.content}
                  {m.updated_chapter_ids.length > 0 && (
                    <span className="block mt-1 text-[10px] opacity-80">已更新 {m.updated_chapter_ids.length} 个章节</span>
                  )}
                </div>
              ))
            )}
            {sending && (
              <div className="self-start flex items-center gap-1.5 px-3 py-2 rounded-[var(--radius-md)] bg-page-alt text-xs text-text-muted">
                <Loader2 size={12} className="animate-spin" />
                Agent 思考中…
              </div>
            )}
          </div>
        )}

        {tab === 'citations' && (
          <div className="flex flex-col gap-2.5">
            {citations.length === 0 ? (
              <p className="text-xs text-text-muted py-6 text-center">
                {chapterTitle ? `「${chapterTitle}」还没有引用` : '选择章节查看引用'}
              </p>
            ) : (
              citations.map((c) => (
                <div key={c.id} className="px-3 py-2.5 rounded-[var(--radius-sm)] border border-border">
                  <div className="flex items-start justify-between gap-2">
                    <p className="text-xs font-bold text-text-primary">
                      [{c.n}] {c.title}
                      {c.page != null && ` · 第 ${c.page} 页`}
                    </p>
                    <span className="text-[10px] text-text-muted shrink-0">{c.captured_at}</span>
                  </div>
                  <p className="mt-1 text-[11px] leading-relaxed text-text-muted">“{c.quote}”</p>
                  {c.url && (
                    <a
                      href={c.url}
                      target="_blank"
                      rel="noreferrer"
                      className="mt-1 inline-flex items-center gap-1 text-[11px] text-primary hover:underline"
                    >
                      <ExternalLink size={10} />
                      <span className="truncate max-w-[260px]">{c.url}</span>
                    </a>
                  )}
                  {c.source_type === 'manual' && <p className="mt-1 text-[11px] text-warning">人工提供</p>}
                </div>
              ))
            )}
          </div>
        )}
      </div>

      <div className="border-t border-border px-4 py-3">
        <div className="flex items-center gap-2 px-3 py-2.5 rounded-[var(--radius-md)] bg-page-alt border border-border focus-within:border-primary focus-within:ring-2 focus-within:ring-primary/20">
          <input
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={(e) => e.key === 'Enter' && send()}
            placeholder={chapterTitle ? `讨论「${chapterTitle}」，或粘贴 URL…` : '和 Agent 讨论报告…'}
            aria-label="发送消息给 Agent"
            className="flex-1 bg-transparent text-[13px] text-text-primary placeholder:text-text-muted focus:outline-none"
          />
          <button onClick={send} disabled={sending || !input.trim()} aria-label="发送" className="text-primary disabled:opacity-40 cursor-pointer">
            <Send size={15} />
          </button>
        </div>
      </div>
    </aside>
  )
}
