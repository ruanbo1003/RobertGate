// 范本库单列：一种报告类型的模板档案 + 范本文件 + 上传/学习操作。

import { useRef } from 'react'
import {
  FileText, GraduationCap, GripVertical, LayoutTemplate, Loader2, RefreshCw, Trash2, Upload,
} from 'lucide-react'
import type { LibraryGroup, ReportType } from '../../types/investReports'
import { ParseChip } from './badges'

interface TemplateSectionProps {
  type: ReportType
  group: LibraryGroup
  busy: boolean
  onUpload: (files: File[]) => Promise<void>
  onDeleteSample: (id: number) => Promise<void>
  onLearn: () => Promise<void>
}

const TYPE_LABEL: Record<ReportType, string> = { advice: '投资建议书', dd: '尽调报告' }

export default function TemplateSection({ type, group, busy, onUpload, onDeleteSample, onLearn }: TemplateSectionProps) {
  const fileRef = useRef<HTMLInputElement>(null)
  const t = group.template
  const ready = t?.status === 'ready'
  const learning = t?.status === 'learning'
  const readySamples = group.samples.filter((s) => s.parse_state === 'ready').length

  return (
    <section className="flex-1 min-w-0 flex flex-col gap-3.5" aria-label={TYPE_LABEL[type]}>
      <div className="flex items-center gap-2">
        <h2 className="text-[15px] font-bold text-text-primary">{TYPE_LABEL[type]}</h2>
        <span
          className={`px-2 py-0.5 rounded-full text-[10px] font-semibold ${
            ready ? 'bg-success-light text-success' : learning ? 'bg-warning-light text-warning' : 'bg-page-alt text-text-muted'
          }`}
        >
          {ready ? '模板已学习' : learning ? '学习中…' : t?.status === 'failed' ? '学习失败' : '模板未学习'}
        </span>
        <div className="flex-1" />
        <button
          onClick={onLearn}
          disabled={busy || learning || readySamples === 0}
          className={`inline-flex items-center gap-1.5 h-9 px-3 text-xs font-semibold rounded-[var(--radius-sm)] transition-colors cursor-pointer disabled:opacity-50 disabled:cursor-not-allowed ${
            ready
              ? 'bg-card border border-border text-text-primary hover:bg-page-alt'
              : 'bg-primary text-white hover:bg-primary-hover'
          }`}
        >
          {learning ? <Loader2 size={13} className="animate-spin" /> : ready ? <RefreshCw size={12} /> : <GraduationCap size={13} />}
          {learning ? '学习中…' : ready ? '重新学习' : '学习生成模板'}
        </button>
      </div>

      {ready && t ? (
        <div className="bg-card border border-border rounded-2xl p-4.5 flex flex-col gap-2.5">
          <div className="flex items-center justify-between">
            <p className="text-[13px] font-bold text-text-primary">模板档案 · 基于 {t.learned_from.length} 份范本归纳</p>
          </div>
          <div className="flex flex-col gap-1.5">
            {t.chapters.map((c) => (
              <div key={c.key} className="flex items-center gap-2 px-2.5 py-1.5 rounded-[var(--radius-sm)] bg-page-alt" title={c.brief}>
                <span className="flex-1 text-xs text-text-primary truncate">{c.title}</span>
                <GripVertical size={12} className="text-slate-300" />
              </div>
            ))}
          </div>
          {t.style_notes && <p className="text-[11px] text-text-muted leading-relaxed">写作要点：{t.style_notes}</p>}
        </div>
      ) : (
        <div className="bg-card border border-dashed border-border rounded-2xl px-5 py-9 flex flex-col items-center gap-2 text-center">
          {learning ? <Loader2 size={26} className="animate-spin text-warning" /> : <LayoutTemplate size={26} className="text-slate-300" />}
          <p className="text-[13px] font-semibold text-text-primary">
            {learning ? '正在归纳章节骨架与写作要点…' : `还没有${TYPE_LABEL[type]}模板`}
          </p>
          {!learning && (
            <p className="max-w-[340px] text-xs leading-relaxed text-text-muted">
              {t?.status === 'failed'
                ? `学习失败：${t.error ?? '未知错误'}，请重试`
                : readySamples > 0
                  ? `已上传 ${readySamples} 份范本，点击「学习生成模板」归纳章节骨架；学习完成后才能创建${TYPE_LABEL[type]}`
                  : `先上传至少 1 份 ${TYPE_LABEL[type]}范本（.docx），再学习生成模板`}
            </p>
          )}
        </div>
      )}

      <p className="text-xs font-semibold text-text-muted">范本文件 · {group.samples.length}</p>
      {group.samples.map((s) => (
        <div key={s.id} className="flex items-center gap-2.5 px-3.5 py-2.5 bg-card border border-border rounded-[var(--radius-md)]">
          <FileText size={15} className="text-primary shrink-0" />
          <span className="flex-1 min-w-0 text-[13px] text-text-primary truncate">{s.filename}</span>
          <span className="text-[11px] text-text-muted">{s.uploaded_at.slice(0, 10)}</span>
          <ParseChip state={s.parse_state} />
          <button
            onClick={() => onDeleteSample(s.id)}
            aria-label={`删除范本 ${s.filename}`}
            className="w-7 h-7 flex items-center justify-center rounded-[var(--radius-sm)] text-text-muted hover:text-error hover:bg-error-light cursor-pointer"
          >
            <Trash2 size={13} />
          </button>
        </div>
      ))}

      <input
        ref={fileRef}
        type="file"
        multiple
        accept=".docx"
        className="hidden"
        onChange={async (e) => {
          const files = Array.from(e.target.files ?? [])
          if (files.length) await onUpload(files)
          e.target.value = ''
        }}
      />
      <button
        onClick={() => fileRef.current?.click()}
        className="h-11 inline-flex items-center justify-center gap-2 text-xs font-semibold rounded-[var(--radius-md)] border border-dashed border-border text-text-muted hover:border-primary hover:text-primary transition-colors cursor-pointer"
      >
        <Upload size={13} />
        {group.samples.length ? '继续上传范本（.docx，可分批）' : '上传第一批范本（.docx）'}
      </button>
    </section>
  )
}
