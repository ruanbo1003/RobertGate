// 段落渲染：解析正文内联标记 ⟦c:引用id⟧ → 引用角标（hover 出处卡），⟦tbd:id⟧ → 待补充胶囊。
// 段落 hover 出「重写本段 / 编辑」操作；重写弹指令输入。

import { useState } from 'react'
import { CircleAlert, ExternalLink, Loader2, Pencil, Sparkles } from 'lucide-react'
import type { Citation, Paragraph, Tbd } from '../../types/investReports'

interface ParagraphViewProps {
  paragraph: Paragraph
  citations: Citation[]
  tbds: Tbd[]
  busy: boolean
  onRewrite: (pid: string, instruction: string) => Promise<void>
  onEdit: (pid: string, text: string) => Promise<void>
  onResolveTbd: (tid: number, value: string) => Promise<void>
}

function CitationMark({ cite }: { cite: Citation }) {
  return (
    <span className="relative group/cite inline-block align-super">
      <span className="mx-0.5 px-1 py-px rounded bg-primary-light text-primary text-[10px] font-bold cursor-pointer">
        [{cite.n}]
      </span>
      <span className="invisible group-hover/cite:visible absolute left-0 top-5 z-20 w-[300px] p-3 rounded-[var(--radius-md)] bg-card border border-border shadow-[0_8px_24px_rgba(0,0,0,0.14)] text-left">
        <span className="flex items-center justify-between gap-2">
          <span className="text-xs font-bold text-text-primary">
            [{cite.n}] {cite.title}
            {cite.page != null && ` · 第 ${cite.page} 页`}
          </span>
          <span className="text-[10px] text-text-muted shrink-0">{cite.captured_at}</span>
        </span>
        <span className="block mt-1 text-xs leading-relaxed text-text-muted font-normal">“{cite.quote}”</span>
        {cite.url && (
          <span className="mt-1.5 flex items-center gap-1 text-[11px] text-primary">
            <ExternalLink size={10} />
            <span className="truncate">{cite.url}</span>
          </span>
        )}
        {cite.source_type === 'manual' && (
          <span className="mt-1.5 block text-[11px] text-warning">人工提供的数据</span>
        )}
      </span>
    </span>
  )
}

function TbdMark({ tbd, onResolve }: { tbd: Tbd; onResolve: (value: string) => void }) {
  return (
    <button
      onClick={() => {
        const v = window.prompt(`待补充：${tbd.reason}\n\n请输入数值/内容（将标注为「人工提供」）：`)
        if (v?.trim()) onResolve(v.trim())
      }}
      title={tbd.reason}
      className="mx-0.5 inline-flex items-center gap-1 px-1.5 py-px rounded border border-warning bg-warning-light text-warning text-[11px] font-semibold cursor-pointer align-baseline"
    >
      <CircleAlert size={10} />
      待补充
    </button>
  )
}

/** 把带内联标记的正文拆成 React 片段 */
function renderText(
  text: string,
  citations: Citation[],
  tbds: Tbd[],
  onResolveTbd: (tid: number, value: string) => void,
) {
  const parts: React.ReactNode[] = []
  const re = /⟦(c|tbd):(\d+)⟧/g
  let last = 0
  let m: RegExpExecArray | null
  let key = 0
  while ((m = re.exec(text)) !== null) {
    if (m.index > last) parts.push(<span key={key++}>{text.slice(last, m.index)}</span>)
    const id = Number(m[2])
    if (m[1] === 'c') {
      const cite = citations.find((c) => c.id === id)
      if (cite) parts.push(<CitationMark key={key++} cite={cite} />)
    } else {
      const tbd = tbds.find((t) => t.id === id)
      if (tbd && !tbd.resolved) {
        parts.push(<TbdMark key={key++} tbd={tbd} onResolve={(v) => onResolveTbd(tbd.id, v)} />)
      }
    }
    last = m.index + m[0].length
  }
  if (last < text.length) parts.push(<span key={key++}>{text.slice(last)}</span>)
  return parts
}

export default function ParagraphView({
  paragraph, citations, tbds, busy, onRewrite, onEdit, onResolveTbd,
}: ParagraphViewProps) {
  const [mode, setMode] = useState<'view' | 'rewrite' | 'edit'>('view')
  const [instruction, setInstruction] = useState('')
  const [draft, setDraft] = useState('')
  const [working, setWorking] = useState(false)

  const submitRewrite = async () => {
    if (!instruction.trim()) return
    setWorking(true)
    await onRewrite(paragraph.id, instruction.trim())
    setWorking(false)
    setMode('view')
    setInstruction('')
  }

  const submitEdit = async () => {
    setWorking(true)
    await onEdit(paragraph.id, draft)
    setWorking(false)
    setMode('view')
  }

  if (mode === 'edit') {
    return (
      <div className="px-3 py-2.5 rounded-[var(--radius-sm)] border border-primary bg-card">
        <textarea
          value={draft}
          onChange={(e) => setDraft(e.target.value)}
          rows={4}
          aria-label="编辑段落"
          className="w-full text-sm leading-relaxed text-text-primary bg-transparent focus:outline-none resize-y"
        />
        <div className="flex justify-end gap-2 mt-1.5">
          <button onClick={() => setMode('view')} className="h-8 px-3 text-xs font-semibold text-text-muted hover:text-text-primary cursor-pointer">
            取消
          </button>
          <button
            onClick={submitEdit}
            disabled={working}
            className="h-8 px-3 text-xs font-semibold rounded-[var(--radius-sm)] bg-primary text-white hover:bg-primary-hover disabled:opacity-50 cursor-pointer"
          >
            {working ? '保存中…' : '保存'}
          </button>
        </div>
      </div>
    )
  }

  return (
    <div className="group relative px-3 py-2.5 rounded-[var(--radius-sm)] hover:bg-primary-light/50 transition-colors">
      <p className="text-sm leading-[1.9] text-text-primary">
        {renderText(paragraph.text, citations, tbds, onResolveTbd)}
      </p>
      {mode === 'rewrite' ? (
        <div className="mt-2 flex items-center gap-2">
          <input
            autoFocus
            value={instruction}
            onChange={(e) => setInstruction(e.target.value)}
            onKeyDown={(e) => e.key === 'Enter' && submitRewrite()}
            placeholder="重写指令，如：更简洁，补一句与竞品的对比"
            aria-label="重写指令"
            className="flex-1 h-9 px-3 text-xs bg-card border border-primary rounded-[var(--radius-sm)] text-text-primary placeholder:text-text-muted focus:outline-none focus:ring-2 focus:ring-primary/30"
          />
          <button
            onClick={submitRewrite}
            disabled={working || !instruction.trim()}
            className="h-9 px-3 text-xs font-semibold rounded-[var(--radius-sm)] bg-primary text-white hover:bg-primary-hover disabled:opacity-50 cursor-pointer inline-flex items-center gap-1.5"
          >
            {working ? <Loader2 size={12} className="animate-spin" /> : <Sparkles size={12} />}
            {working ? '重写中…' : '重写'}
          </button>
          <button onClick={() => setMode('view')} className="h-9 px-2 text-xs text-text-muted hover:text-text-primary cursor-pointer">
            取消
          </button>
        </div>
      ) : (
        !busy && (
          <div className="absolute -top-3 right-3 hidden group-hover:flex items-center gap-1.5">
            <button
              onClick={() => setMode('rewrite')}
              className="inline-flex items-center gap-1 h-7 px-2.5 text-[11px] font-semibold rounded-[var(--radius-sm)] bg-card border border-border shadow-sm text-primary hover:border-primary cursor-pointer"
            >
              <Sparkles size={11} />
              重写本段
            </button>
            <button
              onClick={() => {
                setDraft(paragraph.text)
                setMode('edit')
              }}
              className="inline-flex items-center gap-1 h-7 px-2.5 text-[11px] font-semibold rounded-[var(--radius-sm)] bg-card border border-border shadow-sm text-text-primary hover:border-primary cursor-pointer"
            >
              <Pencil size={11} />
              编辑
            </button>
          </div>
        )
      )}
    </div>
  )
}
