// 投资报告 内存 mock 后端。联调前默认启用（VITE_INVEST_REPORTS_MOCK 控制）。
// 模拟异步：范本解析/模板学习/资料解析/章节研究（带进度流事件）。

import type { ApiResponse } from '../types/auth'
import type {
  ChapterDetail,
  ChapterMeta,
  ChatMessage,
  Citation,
  ExportPendingItem,
  FeedEvent,
  ImpactItem,
  LibraryResponse,
  Paragraph,
  ProjectDetail,
  ProjectStatusResponse,
  ProjectSummary,
  ReportType,
  Sample,
  Source,
  Tbd,
  Template,
} from '../types/investReports'

const delay = <T,>(data: T, ms = 220): Promise<T> =>
  new Promise((resolve) => setTimeout(() => resolve(data), ms))
const ok = <T,>(data: T): ApiResponse<T> => ({ code: 0, data, message: 'ok' })
const err = (code: number, message: string): ApiResponse<never> =>
  ({ code, data: null as never, message })
const nowIso = () => new Date().toISOString()

let nextId = 1000
const genId = () => ++nextId

// ---------------- 范本与模板 ----------------

const ADVICE_CHAPTERS = [
  ['overview', '一、交易概览', '交易结构、拟投金额、估值与条款要点'],
  ['company', '二、公司概况', '历史沿革、股权结构、核心产品'],
  ['industry', '三、行业分析', '市场规模与增速、驱动因素、政策环境'],
  ['competition', '四、竞争格局', '主要竞对、份额、差异化壁垒'],
  ['business', '五、商业模式', '收入结构、获客、单位经济模型'],
  ['financials', '六、财务分析', '收入/毛利/现金流、关键财务指标'],
  ['team', '七、核心团队', '创始人与高管背景、股权激励'],
  ['risks', '八、风险因素', '经营/市场/合规风险及缓释'],
  ['conclusion', '九、投资建议', '投/不投/条件投 + 理由（结论章）'],
].map(([key, title, brief]) => ({ key, title, brief }))

const templates: Record<ReportType, Template | null> = {
  advice: {
    type: 'advice',
    status: 'ready',
    chapters: ADVICE_CHAPTERS,
    style_notes: '数据先行，每章末以「小结」收束；表格呈现财务指标；结论章给出明确建议分级。',
    learned_from: [1, 2, 3],
    error: null,
    updated_at: nowIso(),
  },
  dd: null,
}

const samples: Sample[] = [
  { id: 1, type: 'advice', filename: 'XX智造投资建议书_终版.docx', parse_state: 'ready', uploaded_at: '2026-10-12T10:00:00Z' },
  { id: 2, type: 'advice', filename: '新能源材料项目建议书.docx', parse_state: 'ready', uploaded_at: '2026-10-12T10:05:00Z' },
  { id: 3, type: 'advice', filename: '云服务A轮投资建议书.docx', parse_state: 'ready', uploaded_at: '2026-11-01T09:00:00Z' },
  { id: 4, type: 'dd', filename: '制造业标的尽调报告V3.docx', parse_state: 'ready', uploaded_at: '2026-11-05T14:00:00Z' },
]

export function getLibraryMock(): Promise<ApiResponse<LibraryResponse>> {
  return delay(
    ok({
      advice: { template: templates.advice, samples: samples.filter((s) => s.type === 'advice') },
      dd: { template: templates.dd, samples: samples.filter((s) => s.type === 'dd') },
    }),
  )
}

export function uploadSamplesMock(
  type: ReportType,
  files: File[],
): Promise<ApiResponse<{ samples: Sample[] }>> {
  const created = files.map((f) => {
    const s: Sample = { id: genId(), type, filename: f.name, parse_state: 'parsing', uploaded_at: nowIso() }
    samples.push(s)
    setTimeout(() => { s.parse_state = 'ready' }, 1800)
    return s
  })
  return delay(ok({ samples: created }))
}

export function deleteSampleMock(id: number): Promise<ApiResponse<null>> {
  const idx = samples.findIndex((s) => s.id === id)
  if (idx < 0) return delay(err(2041, '范本不存在'))
  samples.splice(idx, 1)
  return delay(ok(null))
}

export function learnTemplateMock(type: ReportType): Promise<ApiResponse<null>> {
  const ready = samples.filter((s) => s.type === type && s.parse_state === 'ready')
  if (ready.length === 0) return delay(err(2040, '该类型暂无已解析的范本'))
  templates[type] = {
    type,
    status: 'learning',
    chapters: [],
    style_notes: '',
    learned_from: ready.map((s) => s.id),
    error: null,
    updated_at: nowIso(),
  }
  setTimeout(() => {
    templates[type] = {
      ...(templates[type] as Template),
      status: 'ready',
      chapters:
        type === 'advice'
          ? ADVICE_CHAPTERS
          : [
              ['summary', '一、尽调结论摘要', '整体结论与风险分级总览'],
              ['corp', '二、公司与治理', '工商/股权/治理结构核查'],
              ['finance', '三、财务核查', '收入确认、应收、现金流核对'],
              ['legal', '四、法律与合规', '涉诉、行政处罚、资质'],
              ['operation', '五、业务与运营', '客户集中度、供应链、合同'],
              ['risks', '六、风险清单', '分级风险（高/中/低）与缓释建议'],
            ].map(([key, title, brief]) => ({ key, title, brief })),
      style_notes: type === 'advice' ? (templates.advice?.style_notes ?? '') : '风险导向，每项发现标注证据来源与风险等级。',
      updated_at: nowIso(),
    }
  }, 2500)
  return delay(ok(null))
}

export function updateTemplateMock(
  type: ReportType,
  payload: { chapters: Template['chapters']; style_notes?: string },
): Promise<ApiResponse<{ template: Template }>> {
  const t = templates[type]
  if (!t || t.status !== 'ready') return delay(err(2041, '模板不存在或未就绪'))
  t.chapters = payload.chapters
  if (payload.style_notes !== undefined) t.style_notes = payload.style_notes
  t.updated_at = nowIso()
  return delay(ok({ template: t }))
}

// ---------------- 项目与章节 ----------------

interface MockChapter extends ChapterMeta {
  paragraphs: Paragraph[]
  citations: Citation[]
  tbds: Tbd[]
}

interface MockProject extends Omit<ProjectDetail, 'chapters'> {
  chapters: MockChapter[]
  feed: FeedEvent[]
  chat: ChatMessage[]
  queue: { pending: number[]; running: number | null }
}

const CHECKLIST = ['商业计划书 BP', '财务明细（Excel）', '天眼查导出：工商信息 / 股权结构 / 涉诉记录']

const projects: MockProject[] = []

function makeChapter(key: string, title: string): MockChapter {
  return {
    id: genId(), key, title,
    state: 'pending', error: null, tbd_count: 0, version: 0,
    paragraphs: [], citations: [], tbds: [],
  }
}

function seedProject(): void {
  const p: MockProject = {
    id: 1, title: '云帆科技 · A 轮', type: 'advice', status: 'draft',
    chapters_done: 0, chapters_total: ADVICE_CHAPTERS.length, tbd_count: 0,
    updated_at: nowIso(), checklist: CHECKLIST,
    chapters: ADVICE_CHAPTERS.map((c) => makeChapter(c.key, c.title)),
    sources: [
      { id: genId(), kind: 'file', filename: 'BP_云帆科技.pdf', url: null, parse_state: 'ready', quality: 'ok', uploaded_at: nowIso() },
      { id: genId(), kind: 'file', filename: '天眼查导出_股权结构.pdf', url: null, parse_state: 'ready', quality: 'ok', uploaded_at: nowIso() },
      { id: genId(), kind: 'file', filename: '财务明细_2023-2025.xlsx', url: null, parse_state: 'ready', quality: 'ok', uploaded_at: nowIso() },
    ],
    feed: [], chat: [], queue: { pending: [], running: null },
  }
  projects.push(p)
}
seedProject()

function summary(p: MockProject): ProjectSummary {
  const done = p.chapters.filter((c) => c.state === 'done').length
  const anyActive = p.queue.running !== null || p.queue.pending.length > 0
  const anyFailed = p.chapters.some((c) => c.state === 'failed')
  const status = anyActive ? 'researching' : anyFailed ? 'partial_failed' : done === p.chapters.length ? 'completed' : 'draft'
  return {
    id: p.id, title: p.title, type: p.type, status,
    chapters_done: done, chapters_total: p.chapters.length,
    tbd_count: p.chapters.reduce((n, c) => n + c.tbds.filter((t) => !t.resolved).length, 0),
    updated_at: p.updated_at,
  }
}

const chapterMeta = (c: MockChapter): ChapterMeta & { tbd_count: number } => ({
  id: c.id, key: c.key, title: c.title, state: c.state, error: c.error,
  tbd_count: c.tbds.filter((t) => !t.resolved).length, version: c.version,
})

export function listProjectsMock(): Promise<ApiResponse<{ items: ProjectSummary[]; total: number }>> {
  return delay(ok({ items: projects.map(summary), total: projects.length }))
}

export function createProjectMock(
  title: string,
  type: ReportType,
): Promise<ApiResponse<{ project: ProjectDetail }>> {
  const t = templates[type]
  if (!t || t.status !== 'ready') return delay(err(2042, '该类型模板未学习，请先到范本库完成学习'))
  const p: MockProject = {
    id: genId(), title, type, status: 'draft',
    chapters_done: 0, chapters_total: t.chapters.length, tbd_count: 0,
    updated_at: nowIso(), checklist: CHECKLIST,
    chapters: t.chapters.map((c) => makeChapter(c.key, c.title)),
    sources: [], feed: [], chat: [], queue: { pending: [], running: null },
  }
  projects.unshift(p)
  return delay(ok({ project: detail(p) }))
}

function detail(p: MockProject): ProjectDetail {
  return { ...summary(p), chapters: p.chapters.map(chapterMeta), sources: p.sources, checklist: p.checklist }
}

function find(id: number): MockProject | undefined {
  return projects.find((x) => x.id === id)
}

export function getProjectMock(id: number): Promise<ApiResponse<{ project: ProjectDetail }>> {
  const p = find(id)
  if (!p) return delay(err(2041, '项目不存在'))
  return delay(ok({ project: detail(p) }))
}

export function deleteProjectMock(id: number): Promise<ApiResponse<null>> {
  const i = projects.findIndex((x) => x.id === id)
  if (i < 0) return delay(err(2041, '项目不存在'))
  projects.splice(i, 1)
  return delay(ok(null))
}

// ---------------- 资料 ----------------

export function listSourcesMock(id: number): Promise<ApiResponse<{ sources: Source[] }>> {
  const p = find(id)
  if (!p) return delay(err(2041, '项目不存在'))
  return delay(ok({ sources: p.sources }))
}

export function uploadSourcesMock(id: number, files: File[]): Promise<ApiResponse<{ sources: Source[] }>> {
  const p = find(id)
  if (!p) return delay(err(2041, '项目不存在'))
  const created = files.map((f) => {
    const low = /\.(png|jpg|jpeg)$/i.test(f.name)
    const s: Source = { id: genId(), kind: 'file', filename: f.name, url: null, parse_state: 'parsing', quality: 'ok', uploaded_at: nowIso() }
    p.sources.push(s)
    setTimeout(() => { s.parse_state = 'ready'; if (low) s.quality = 'low' }, 1500)
    return s
  })
  p.updated_at = nowIso()
  return delay(ok({ sources: created }))
}

export function addUrlSourceMock(id: number, url: string): Promise<ApiResponse<{ source: Source }>> {
  const p = find(id)
  if (!p) return delay(err(2041, '项目不存在'))
  const s: Source = { id: genId(), kind: 'url', filename: null, url, parse_state: 'parsing', quality: 'ok', uploaded_at: nowIso() }
  p.sources.push(s)
  setTimeout(() => { s.parse_state = 'ready' }, 1200)
  return delay(ok({ source: s }))
}

export function deleteSourceMock(id: number, sid: number): Promise<ApiResponse<null>> {
  const p = find(id)
  if (!p) return delay(err(2041, '项目不存在'))
  const i = p.sources.findIndex((s) => s.id === sid)
  if (i < 0) return delay(err(2041, '资料不存在'))
  p.sources.splice(i, 1)
  return delay(ok(null))
}

export function analyzeImpactMock(id: number, sid: number): Promise<ApiResponse<{ affected: ImpactItem[] }>> {
  void sid
  const p = find(id)
  if (!p) return delay(err(2041, '项目不存在'))
  const doneChapters = p.chapters.filter((c) => c.state === 'done').slice(0, 2)
  return delay(
    ok({
      affected: doneChapters.map((c) => ({
        chapter_id: c.id, title: c.title, reason: '新资料包含与本章相关的数据，建议更新',
      })),
    }),
    600,
  )
}

// ---------------- 研究引擎（模拟） ----------------

let feedId = 0

function pushFeed(p: MockProject, chapterId: number, kind: FeedEvent['kind'], text: string, url: string | null = null): void {
  p.feed.push({ id: ++feedId, chapter_id: chapterId, kind, text, ref: url ? { url, source_id: null, page: null } : null, ts: nowIso() })
}

function researchChapter(p: MockProject, c: MockChapter, onDone: () => void): void {
  c.state = c.state === 'stale' ? 'updating' : 'researching'
  c.error = null
  const steps: Array<[FeedEvent['kind'], string, string | null]> = [
    ['search', `检索「${p.title.split(' ')[0]} ${c.title.replace(/^[一二三四五六七八九]、/, '')}」`, null],
    ['read_url', '读取 IDC 行业报告页', 'https://www.idc.com/example'],
    ['read_source', '从「BP_云帆科技.pdf」第 12 页提取关键数据', null],
    ['write', '正在撰写本章初稿…', null],
  ]
  let i = 0
  const tick = () => {
    if (i < steps.length) {
      const [kind, text, url] = steps[i++]
      pushFeed(p, c.id, kind, text, url)
      setTimeout(tick, 900)
      return
    }
    const cite1: Citation = {
      id: genId(), n: 1, source_type: 'web', title: 'IDC · 行业市场跟踪报告',
      url: 'https://www.idc.com/example', source_id: null, page: null,
      quote: '2025 年该市场整体规模达 4,562.1 亿元，同比增长 28.3%。', captured_at: '2026-09',
    }
    const cite2: Citation = {
      id: genId(), n: 2, source_type: 'file', title: 'BP_云帆科技.pdf · 第 12 页',
      url: null, source_id: p.sources[0]?.id ?? null, page: 12,
      quote: '公司 2025 年营业收入 3.2 亿元，同比增长 67%。', captured_at: '2026-11',
    }
    const tbd: Tbd = { id: genId(), reason: '未找到竞对最新估值的可靠来源', value: null, resolved: false }
    c.citations = [cite1, cite2]
    c.tbds = [tbd]
    c.paragraphs = [
      { id: 'p1', text: `${c.title.replace(/^[一二三四五六七八九]、/, '')}方面，市场保持高速增长。2025 年市场规模达 4,562 亿元，同比增长 28.3%⟦c:${cite1.id}⟧，公司所处细分赛道增速显著高于整体水平。` },
      { id: 'p2', text: `公司 2025 年营业收入 3.2 亿元，同比增长 67%⟦c:${cite2.id}⟧，在同类厂商中位居前列，收入结构以订阅为主。` },
      { id: 'p3', text: `主要竞争对手近一年融资估值为⟦tbd:${tbd.id}⟧，与公司当前估值的比较详见结论章。` },
    ]
    c.state = 'done'
    c.version += 1
    pushFeed(p, c.id, 'done', `${c.title} 初稿完成`)
    p.updated_at = nowIso()
    onDone()
  }
  tick()
}

function pump(p: MockProject): void {
  if (p.queue.running !== null || p.queue.pending.length === 0) return
  const cid = p.queue.pending.shift() as number
  const c = p.chapters.find((x) => x.id === cid)
  if (!c) { pump(p); return }
  p.queue.running = cid
  researchChapter(p, c, () => {
    p.queue.running = null
    pump(p)
  })
}

export function researchMock(id: number, chapterIds?: number[]): Promise<ApiResponse<{ enqueued: number[] }>> {
  const p = find(id)
  if (!p) return delay(err(2041, '项目不存在'))
  const targets = (chapterIds?.length
    ? p.chapters.filter((c) => chapterIds.includes(c.id))
    : p.chapters.filter((c) => c.state !== 'done')
  ).filter((c) => c.state !== 'researching' && c.state !== 'updating' && !p.queue.pending.includes(c.id) && p.queue.running !== c.id)
  for (const c of targets) p.queue.pending.push(c.id)
  pump(p)
  return delay(ok({ enqueued: targets.map((c) => c.id) }))
}

export function cancelQueueMock(id: number): Promise<ApiResponse<{ cancelled: number }>> {
  const p = find(id)
  if (!p) return delay(err(2041, '项目不存在'))
  const n = p.queue.pending.length
  p.queue.pending = []
  return delay(ok({ cancelled: n }))
}

export function getStatusMock(id: number, feedAfter = 0): Promise<ApiResponse<ProjectStatusResponse>> {
  const p = find(id)
  if (!p) return delay(err(2041, '项目不存在'))
  const s = summary(p)
  return delay(
    ok({
      status: s.status,
      queue: { pending: p.queue.pending.length, running: p.queue.running !== null ? 1 : 0, paused: false, paused_reason: null },
      chapters: p.chapters.map((c) => ({ id: c.id, state: c.state, tbd_count: c.tbds.filter((t) => !t.resolved).length, version: c.version, error: c.error })),
      tbd_count: s.tbd_count,
      feed: p.feed.filter((e) => e.id > feedAfter).slice(0, 100),
    }),
    120,
  )
}

// ---------------- 章节编辑 ----------------

function findChapter(id: number, cid: number): [MockProject, MockChapter] | null {
  const p = find(id)
  const c = p?.chapters.find((x) => x.id === cid)
  return p && c ? [p, c] : null
}

const toDetail = (c: MockChapter): ChapterDetail => ({
  ...chapterMeta(c), paragraphs: c.paragraphs, citations: c.citations, tbds: c.tbds,
})

export function getChapterMock(id: number, cid: number): Promise<ApiResponse<{ chapter: ChapterDetail }>> {
  const hit = findChapter(id, cid)
  if (!hit) return delay(err(2041, '章节不存在'))
  return delay(ok({ chapter: toDetail(hit[1]) }), 120)
}

export function updateParagraphMock(
  id: number, cid: number, pid: string, text: string,
): Promise<ApiResponse<{ chapter: ChapterDetail }>> {
  const hit = findChapter(id, cid)
  if (!hit) return delay(err(2041, '章节不存在'))
  const [p, c] = hit
  if (c.state === 'researching' || c.state === 'updating') return delay(err(2044, '章节研究中，暂不可编辑'))
  const para = c.paragraphs.find((x) => x.id === pid)
  if (!para) return delay(err(2041, '段落不存在'))
  para.text = text
  c.version += 1
  p.updated_at = nowIso()
  return delay(ok({ chapter: toDetail(c) }))
}

export function rewriteParagraphMock(
  id: number, cid: number, pid: string, instruction: string,
): Promise<ApiResponse<{ chapter: ChapterDetail }>> {
  const hit = findChapter(id, cid)
  if (!hit) return delay(err(2041, '章节不存在'))
  const [p, c] = hit
  if (c.state === 'researching' || c.state === 'updating') return delay(err(2044, '章节研究中，暂不可重写'))
  const para = c.paragraphs.find((x) => x.id === pid)
  if (!para) return delay(err(2041, '段落不存在'))
  const keepMarks = (para.text.match(/⟦[^⟧]+⟧/g) ?? []).join('')
  para.text = `（按指令「${instruction}」重写）${para.text.replace(/⟦[^⟧]+⟧/g, '')}${keepMarks}`
  c.version += 1
  p.updated_at = nowIso()
  return delay(ok({ chapter: toDetail(c) }), 1200)
}

export function resolveTbdMock(
  id: number, tid: number, value: string,
): Promise<ApiResponse<{ chapter: ChapterDetail }>> {
  const p = find(id)
  if (!p) return delay(err(2041, '项目不存在'))
  for (const c of p.chapters) {
    const t = c.tbds.find((x) => x.id === tid)
    if (t) {
      t.value = value
      t.resolved = true
      const cite: Citation = {
        id: genId(), n: c.citations.length + 1, source_type: 'manual',
        title: '人工提供', url: null, source_id: null, page: null, quote: value, captured_at: nowIso().slice(0, 7),
      }
      c.citations.push(cite)
      for (const para of c.paragraphs) {
        para.text = para.text.replace(`⟦tbd:${tid}⟧`, `${value}⟦c:${cite.id}⟧`)
      }
      c.version += 1
      p.updated_at = nowIso()
      return delay(ok({ chapter: toDetail(c) }))
    }
  }
  return delay(err(2041, '待补充项不存在'))
}

// ---------------- 对话 ----------------

export function listChatMock(id: number): Promise<ApiResponse<{ messages: ChatMessage[] }>> {
  const p = find(id)
  if (!p) return delay(err(2041, '项目不存在'))
  return delay(ok({ messages: p.chat }))
}

export function sendChatMock(
  id: number, message: string, chapterId?: number | null,
): Promise<ApiResponse<{ reply: string; updated_chapter_ids: number[] }>> {
  const p = find(id)
  if (!p) return delay(err(2041, '项目不存在'))
  p.chat.push({ id: genId(), role: 'user', content: message, chapter_id: chapterId ?? null, updated_chapter_ids: [], ts: nowIso() })
  const target = chapterId ? p.chapters.find((c) => c.id === chapterId && c.state === 'done') : null
  let reply = '好的，我理解了。这条意见不涉及具体章节改动，如需改稿请指定章节。'
  const updated: number[] = []
  if (target) {
    target.paragraphs.push({ id: `p${target.paragraphs.length + 1}`, text: `（按对话补充）${message.slice(0, 40)}——已补充相应分析。` })
    target.version += 1
    updated.push(target.id)
    reply = `已按你的意见更新「${target.title}」，可在编辑器查看修改。`
  }
  p.chat.push({ id: genId(), role: 'assistant', content: reply, chapter_id: chapterId ?? null, updated_chapter_ids: updated, ts: nowIso() })
  p.updated_at = nowIso()
  return delay(ok({ reply, updated_chapter_ids: updated }), 1000)
}

// ---------------- 导出 ----------------

export function exportMock(id: number): Promise<ApiResponse<{ download_url: string } | { pending: ExportPendingItem[] }>> {
  const p = find(id)
  if (!p) return delay(err(2041, '项目不存在'))
  const pending: ExportPendingItem[] = []
  for (const c of p.chapters) {
    for (const t of c.tbds) if (!t.resolved) pending.push({ tbd_id: t.id, chapter_id: c.id, reason: t.reason })
  }
  if (pending.length > 0) {
    return delay({ code: 2045, data: { pending }, message: '存在未处理的「待补充」，请先补全或确认' } as ApiResponse<{ pending: ExportPendingItem[] }>)
  }
  return delay(ok({ download_url: '#mock-download' }), 900)
}
