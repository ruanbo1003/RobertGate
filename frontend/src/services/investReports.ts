// 投资报告 Agent：API 客户端，对应 docs/api/invest-reports.md
// VITE_INVEST_REPORTS_MOCK：true → 走 investReports.mock.ts；false → 真实后端。默认 true。

import type { ApiResponse } from '../types/auth'
import type {
  ChapterDetail,
  ChatMessage,
  ExportPendingItem,
  ImpactItem,
  LibraryResponse,
  ProjectDetail,
  ProjectStatusResponse,
  ProjectSummary,
  ReportType,
  Sample,
  Source,
  Template,
  TemplateChapter,
} from '../types/investReports'
import * as mock from './investReports.mock'

const USE_MOCK = (import.meta.env.VITE_INVEST_REPORTS_MOCK ?? 'true') !== 'false'
const API_ORIGIN = (import.meta.env.VITE_API_BASE_URL ?? '') as string
const API_BASE = `${API_ORIGIN}/api/v1/invest-reports`

function authHeaders(): Record<string, string> {
  const token = localStorage.getItem('token')
  return token ? { Authorization: `Bearer ${token}` } : {}
}

async function request<T>(path: string, options?: RequestInit): Promise<ApiResponse<T>> {
  try {
    const res = await fetch(`${API_BASE}${path}`, {
      headers: { 'Content-Type': 'application/json', ...authHeaders(), ...(options?.headers ?? {}) },
      ...options,
    })
    if (!res.ok && res.status >= 500) {
      return { code: 5000, data: null as T, message: '服务器异常，请稍后重试' }
    }
    return await res.json()
  } catch (e) {
    if (e instanceof TypeError) return { code: 5001, data: null as T, message: '网络连接失败，请检查网络' }
    return { code: 5000, data: null as T, message: '请求失败，请稍后重试' }
  }
}

async function upload<T>(path: string, form: FormData): Promise<ApiResponse<T>> {
  try {
    const res = await fetch(`${API_BASE}${path}`, { method: 'POST', headers: authHeaders(), body: form })
    return await res.json()
  } catch {
    return { code: 5001, data: null as T, message: '上传失败，请检查网络' }
  }
}

// ---------------- 范本库与模板 ----------------

export function getLibrary(): Promise<ApiResponse<LibraryResponse>> {
  if (USE_MOCK) return mock.getLibraryMock()
  return request('/library')
}

export function uploadSamples(type: ReportType, files: File[]): Promise<ApiResponse<{ samples: Sample[] }>> {
  if (USE_MOCK) return mock.uploadSamplesMock(type, files)
  const form = new FormData()
  form.append('type', type)
  for (const f of files) form.append('files', f)
  return upload('/samples', form)
}

export function deleteSample(id: number): Promise<ApiResponse<null>> {
  if (USE_MOCK) return mock.deleteSampleMock(id)
  return request(`/samples/${id}`, { method: 'DELETE' })
}

export function learnTemplate(type: ReportType, sampleIds?: number[]): Promise<ApiResponse<null>> {
  if (USE_MOCK) return mock.learnTemplateMock(type)
  return request(`/templates/${type}/learn`, { method: 'POST', body: JSON.stringify({ sample_ids: sampleIds }) })
}

export function updateTemplate(
  type: ReportType,
  payload: { chapters: TemplateChapter[]; style_notes?: string },
): Promise<ApiResponse<{ template: Template }>> {
  if (USE_MOCK) return mock.updateTemplateMock(type, payload)
  return request(`/templates/${type}`, { method: 'PUT', body: JSON.stringify(payload) })
}

// ---------------- 项目 ----------------

export function listProjects(): Promise<ApiResponse<{ items: ProjectSummary[]; total: number }>> {
  if (USE_MOCK) return mock.listProjectsMock()
  return request('/projects?page=1&page_size=50')
}

export function createProject(title: string, type: ReportType): Promise<ApiResponse<{ project: ProjectDetail }>> {
  if (USE_MOCK) return mock.createProjectMock(title, type)
  return request('/projects', { method: 'POST', body: JSON.stringify({ title, type }) })
}

export function getProject(id: number): Promise<ApiResponse<{ project: ProjectDetail }>> {
  if (USE_MOCK) return mock.getProjectMock(id)
  return request(`/projects/${id}`)
}

export function deleteProject(id: number): Promise<ApiResponse<null>> {
  if (USE_MOCK) return mock.deleteProjectMock(id)
  return request(`/projects/${id}`, { method: 'DELETE' })
}

// ---------------- 资料 ----------------

export function listSources(id: number): Promise<ApiResponse<{ sources: Source[] }>> {
  if (USE_MOCK) return mock.listSourcesMock(id)
  return request(`/projects/${id}/sources`)
}

export function uploadSources(id: number, files: File[]): Promise<ApiResponse<{ sources: Source[] }>> {
  if (USE_MOCK) return mock.uploadSourcesMock(id, files)
  const form = new FormData()
  for (const f of files) form.append('files', f)
  return upload(`/projects/${id}/sources`, form)
}

export function addUrlSource(id: number, url: string): Promise<ApiResponse<{ source: Source }>> {
  if (USE_MOCK) return mock.addUrlSourceMock(id, url)
  return request(`/projects/${id}/sources/url`, { method: 'POST', body: JSON.stringify({ url }) })
}

export function deleteSource(id: number, sid: number): Promise<ApiResponse<null>> {
  if (USE_MOCK) return mock.deleteSourceMock(id, sid)
  return request(`/projects/${id}/sources/${sid}`, { method: 'DELETE' })
}

export function analyzeImpact(id: number, sid: number): Promise<ApiResponse<{ affected: ImpactItem[] }>> {
  if (USE_MOCK) return mock.analyzeImpactMock(id, sid)
  return request(`/projects/${id}/sources/${sid}/impact`, { method: 'POST' })
}

export function sourceFileUrl(id: number, sid: number): string {
  return `${API_BASE}/projects/${id}/sources/${sid}/file`
}

// ---------------- 研究与状态 ----------------

export function startResearch(id: number, chapterIds?: number[]): Promise<ApiResponse<{ enqueued: number[] }>> {
  if (USE_MOCK) return mock.researchMock(id, chapterIds)
  return request(`/projects/${id}/research`, { method: 'POST', body: JSON.stringify({ chapter_ids: chapterIds }) })
}

export function cancelQueue(id: number): Promise<ApiResponse<{ cancelled: number }>> {
  if (USE_MOCK) return mock.cancelQueueMock(id)
  return request(`/projects/${id}/queue/cancel`, { method: 'POST' })
}

export function getStatus(id: number, feedAfter: number): Promise<ApiResponse<ProjectStatusResponse>> {
  if (USE_MOCK) return mock.getStatusMock(id, feedAfter)
  return request(`/projects/${id}/status?feed_after=${feedAfter}`)
}

// ---------------- 章节编辑 ----------------

export function getChapter(id: number, cid: number): Promise<ApiResponse<{ chapter: ChapterDetail }>> {
  if (USE_MOCK) return mock.getChapterMock(id, cid)
  return request(`/projects/${id}/chapters/${cid}`)
}

export function updateParagraph(
  id: number, cid: number, pid: string, text: string,
): Promise<ApiResponse<{ chapter: ChapterDetail }>> {
  if (USE_MOCK) return mock.updateParagraphMock(id, cid, pid, text)
  return request(`/projects/${id}/chapters/${cid}/paragraphs/${pid}`, { method: 'PUT', body: JSON.stringify({ text }) })
}

export function rewriteParagraph(
  id: number, cid: number, pid: string, instruction: string,
): Promise<ApiResponse<{ chapter: ChapterDetail }>> {
  if (USE_MOCK) return mock.rewriteParagraphMock(id, cid, pid, instruction)
  return request(`/projects/${id}/chapters/${cid}/paragraphs/${pid}/rewrite`, {
    method: 'POST', body: JSON.stringify({ instruction }),
  })
}

export function resolveTbd(id: number, tid: number, value: string): Promise<ApiResponse<{ chapter: ChapterDetail }>> {
  if (USE_MOCK) return mock.resolveTbdMock(id, tid, value)
  return request(`/projects/${id}/tbds/${tid}/resolve`, { method: 'POST', body: JSON.stringify({ value }) })
}

// ---------------- 对话 ----------------

export function listChat(id: number): Promise<ApiResponse<{ messages: ChatMessage[] }>> {
  if (USE_MOCK) return mock.listChatMock(id)
  return request(`/projects/${id}/chat?limit=50`)
}

export function sendChat(
  id: number, message: string, chapterId?: number | null,
): Promise<ApiResponse<{ reply: string; updated_chapter_ids: number[] }>> {
  if (USE_MOCK) return mock.sendChatMock(id, message, chapterId)
  return request(`/projects/${id}/chat`, { method: 'POST', body: JSON.stringify({ message, chapter_id: chapterId ?? null }) })
}

// ---------------- 导出 ----------------

/** 带鉴权下载成稿：download 接口需要 Bearer 头，window.open 会 401。 */
export async function downloadReport(id: number): Promise<boolean> {
  try {
    const res = await fetch(`${API_BASE}/projects/${id}/download`, { headers: authHeaders() })
    if (!res.ok) return false
    const blob = await res.blob()
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = `invest-report-${id}.docx`
    a.click()
    URL.revokeObjectURL(url)
    return true
  } catch {
    return false
  }
}

export function exportReport(
  id: number,
): Promise<ApiResponse<{ download_url: string } | { pending: ExportPendingItem[] }>> {
  if (USE_MOCK) return mock.exportMock(id)
  return request(`/projects/${id}/export`, { method: 'POST' })
}
