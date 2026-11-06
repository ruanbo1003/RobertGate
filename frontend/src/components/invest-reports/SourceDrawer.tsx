// 资料库抽屉：文件/URL 资料列表、上传、影响分析（增量更新入口）。

import { useRef, useState } from 'react'
import { FileText, Link2, Loader2, Plus, Trash2, Upload, X, Zap } from 'lucide-react'
import type { ImpactItem, Source } from '../../types/investReports'
import { ParseChip } from './badges'

interface SourceDrawerProps {
  open: boolean
  sources: Source[]
  checklist: string[]
  onClose: () => void
  onUpload: (files: File[]) => Promise<void>
  onAddUrl: (url: string) => Promise<void>
  onDelete: (sid: number) => Promise<void>
  onAnalyzeImpact: (sid: number) => Promise<ImpactItem[]>
  onApplyUpdate: (chapterIds: number[]) => Promise<void>
}

export default function SourceDrawer({
  open, sources, checklist, onClose, onUpload, onAddUrl, onDelete, onAnalyzeImpact, onApplyUpdate,
}: SourceDrawerProps) {
  const fileRef = useRef<HTMLInputElement>(null)
  const [url, setUrl] = useState('')
  const [busy, setBusy] = useState(false)
  const [impact, setImpact] = useState<{ sid: number; items: ImpactItem[]; checked: number[] } | null>(null)

  if (!open) return null

  const analyze = async (sid: number) => {
    setBusy(true)
    const items = await onAnalyzeImpact(sid)
    setBusy(false)
    setImpact({ sid, items, checked: items.map((i) => i.chapter_id) })
  }

  return (
    <div className="fixed inset-0 z-40">
      <button aria-label="关闭资料库" onClick={onClose} className="absolute inset-0 bg-black/40 cursor-pointer" />
      <div className="absolute right-0 top-0 h-full w-[420px] bg-card border-l border-border shadow-[0_8px_32px_rgba(0,0,0,0.16)] flex flex-col">
        <div className="flex items-center justify-between px-5 h-14 border-b border-border">
          <h2 className="text-sm font-bold text-text-primary">资料库 · {sources.length}</h2>
          <button onClick={onClose} aria-label="关闭" className="w-8 h-8 flex items-center justify-center rounded-[var(--radius-sm)] text-text-muted hover:bg-page-alt cursor-pointer">
            <X size={16} />
          </button>
        </div>

        <div className="flex-1 overflow-y-auto px-5 py-4 flex flex-col gap-3">
          {sources.length === 0 && (
            <div className="px-3.5 py-3 rounded-[var(--radius-md)] bg-primary-light">
              <p className="text-xs font-bold text-primary">建议上传的资料</p>
              <ul className="mt-1.5 flex flex-col gap-1">
                {checklist.map((c) => (
                  <li key={c} className="text-xs text-text-primary leading-relaxed">· {c}</li>
                ))}
              </ul>
              <p className="mt-1.5 text-[11px] text-text-muted">天眼查无 API：请在网页版导出 PDF / 截图后上传，Agent 会作为高可信来源解析。</p>
            </div>
          )}

          {sources.map((s) => (
            <div key={s.id} className="flex items-center gap-2.5 px-3 py-2.5 rounded-[var(--radius-md)] border border-border">
              {s.kind === 'file' ? <FileText size={15} className="text-primary shrink-0" /> : <Link2 size={15} className="text-primary shrink-0" />}
              <span className="flex-1 min-w-0 text-[13px] text-text-primary truncate">{s.filename ?? s.url}</span>
              <ParseChip state={s.parse_state} quality={s.quality} />
              {s.parse_state === 'ready' && (
                <button
                  onClick={() => analyze(s.id)}
                  disabled={busy}
                  title="影响分析：这份资料会影响哪些已成稿章节"
                  aria-label="影响分析"
                  className="w-7 h-7 flex items-center justify-center rounded-[var(--radius-sm)] text-warning hover:bg-warning-light cursor-pointer disabled:opacity-50"
                >
                  {busy ? <Loader2 size={13} className="animate-spin" /> : <Zap size={13} />}
                </button>
              )}
              <button
                onClick={() => onDelete(s.id)}
                aria-label="删除资料"
                className="w-7 h-7 flex items-center justify-center rounded-[var(--radius-sm)] text-text-muted hover:text-error hover:bg-error-light cursor-pointer"
              >
                <Trash2 size={13} />
              </button>
            </div>
          ))}

          {impact && (
            <div className="px-3.5 py-3 rounded-[var(--radius-md)] border border-warning bg-warning-light">
              <p className="text-xs font-bold text-warning">影响分析 · 建议更新 {impact.items.length} 个章节</p>
              {impact.items.length === 0 ? (
                <p className="mt-1 text-xs text-text-primary">暂无已成稿章节受影响。</p>
              ) : (
                <>
                  {impact.items.map((i) => (
                    <label key={i.chapter_id} className="mt-1.5 flex items-start gap-2 cursor-pointer">
                      <input
                        type="checkbox"
                        checked={impact.checked.includes(i.chapter_id)}
                        onChange={(e) =>
                          setImpact({
                            ...impact,
                            checked: e.target.checked
                              ? [...impact.checked, i.chapter_id]
                              : impact.checked.filter((x) => x !== i.chapter_id),
                          })
                        }
                        className="mt-0.5 accent-[#2563EB]"
                      />
                      <span className="text-xs text-text-primary leading-relaxed">
                        <b>{i.title}</b> — {i.reason}
                      </span>
                    </label>
                  ))}
                  <button
                    onClick={async () => {
                      await onApplyUpdate(impact.checked)
                      setImpact(null)
                      onClose()
                    }}
                    disabled={impact.checked.length === 0}
                    className="mt-2.5 h-9 w-full text-xs font-semibold rounded-[var(--radius-sm)] bg-primary text-white hover:bg-primary-hover disabled:opacity-50 cursor-pointer"
                  >
                    确认更新所选章节
                  </button>
                </>
              )}
            </div>
          )}
        </div>

        <div className="border-t border-border px-5 py-4 flex flex-col gap-2.5">
          <input ref={fileRef} type="file" multiple accept=".docx,.pdf,.xlsx,.png,.jpg,.jpeg" className="hidden" onChange={async (e) => {
            const files = Array.from(e.target.files ?? [])
            if (files.length) await onUpload(files)
            e.target.value = ''
          }} />
          <button
            onClick={() => fileRef.current?.click()}
            className="h-11 w-full inline-flex items-center justify-center gap-2 text-[13px] font-semibold rounded-[var(--radius-md)] border border-dashed border-border text-text-muted hover:border-primary hover:text-primary cursor-pointer"
          >
            <Upload size={14} />
            上传资料（docx / pdf / xlsx / 图片，≤50MB）
          </button>
          <div className="flex items-center gap-2">
            <input
              value={url}
              onChange={(e) => setUrl(e.target.value)}
              placeholder="粘贴 URL 作为资料…"
              aria-label="URL 资料"
              className="flex-1 h-10 px-3 text-[13px] bg-card border border-border rounded-[var(--radius-sm)] text-text-primary placeholder:text-text-muted focus:outline-none focus:ring-2 focus:ring-primary/30 focus:border-primary"
            />
            <button
              onClick={async () => {
                if (!/^https?:\/\//.test(url)) return
                await onAddUrl(url)
                setUrl('')
              }}
              disabled={!/^https?:\/\//.test(url)}
              aria-label="添加 URL"
              className="h-10 px-3.5 inline-flex items-center gap-1.5 text-[13px] font-semibold rounded-[var(--radius-sm)] bg-primary text-white hover:bg-primary-hover disabled:opacity-50 cursor-pointer"
            >
              <Plus size={14} />
              添加
            </button>
          </div>
        </div>
      </div>
    </div>
  )
}
