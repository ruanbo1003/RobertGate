// 投资报告 Agent 类型定义，对应 docs/api/invest-reports.md

export type ReportType = 'advice' | 'dd'

export type TemplateStatus = 'none' | 'learning' | 'ready' | 'failed'

export interface TemplateChapter {
  key: string
  title: string
  brief: string
}

export interface Template {
  type: ReportType
  status: TemplateStatus
  chapters: TemplateChapter[]
  style_notes: string
  learned_from: number[]
  error: string | null
  updated_at: string
}

export type ParseState = 'pending' | 'parsing' | 'ready' | 'failed'

export interface Sample {
  id: number
  type: ReportType
  filename: string
  parse_state: ParseState
  uploaded_at: string
}

export interface LibraryGroup {
  template: Template | null
  samples: Sample[]
}

export interface LibraryResponse {
  advice: LibraryGroup
  dd: LibraryGroup
}

export type ProjectStatus = 'draft' | 'researching' | 'partial_failed' | 'completed'

export interface ProjectSummary {
  id: number
  title: string
  type: ReportType
  status: ProjectStatus
  chapters_done: number
  chapters_total: number
  tbd_count: number
  updated_at: string
}

export type ChapterState = 'pending' | 'researching' | 'done' | 'failed' | 'stale' | 'updating'

export interface ChapterMeta {
  id: number
  key: string
  title: string
  state: ChapterState
  error: string | null
  tbd_count: number
  version: number
}

export type SourceKind = 'file' | 'url'

export interface Source {
  id: number
  kind: SourceKind
  filename: string | null
  url: string | null
  parse_state: ParseState
  quality: 'ok' | 'low'
  uploaded_at: string
}

export interface ProjectDetail extends ProjectSummary {
  chapters: ChapterMeta[]
  sources: Source[]
  checklist: string[]
}

export type CitationSourceType = 'web' | 'file' | 'manual'

export interface Citation {
  id: number
  n: number
  source_type: CitationSourceType
  title: string
  url: string | null
  source_id: number | null
  page: number | null
  quote: string
  captured_at: string
}

export interface Tbd {
  id: number
  reason: string
  value: string | null
  resolved: boolean
}

export interface Paragraph {
  id: string
  /** 正文，内联标记 ⟦c:引用id⟧ / ⟦tbd:id⟧ */
  text: string
}

export interface ChapterDetail extends ChapterMeta {
  paragraphs: Paragraph[]
  citations: Citation[]
  tbds: Tbd[]
}

export type FeedKind = 'search' | 'read_url' | 'read_source' | 'extract' | 'write' | 'done' | 'error'

export interface FeedEvent {
  id: number
  chapter_id: number
  kind: FeedKind
  text: string
  ref: { url: string | null; source_id: number | null; page: number | null } | null
  ts: string
}

export interface QueueInfo {
  pending: number
  running: number
  paused: boolean
  paused_reason: string | null
}

export interface ChapterStatus {
  id: number
  state: ChapterState
  tbd_count: number
  version: number
  error: string | null
}

export interface ProjectStatusResponse {
  status: ProjectStatus
  queue: QueueInfo
  chapters: ChapterStatus[]
  tbd_count: number
  feed: FeedEvent[]
}

export interface ChatMessage {
  id: number
  role: 'user' | 'assistant'
  content: string
  chapter_id: number | null
  updated_chapter_ids: number[]
  ts: string
}

export interface ImpactItem {
  chapter_id: number
  title: string
  reason: string
}

export interface ExportPendingItem {
  tbd_id: number
  chapter_id: number
  reason: string
}
