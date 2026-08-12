// 文生图任务化 内存 mock 后端。默认关闭（VITE_T2I_MOCK=false），仅供离线开发时启用。

import type { ApiResponse } from '../types/auth'
import type {
  T2ICreateTaskResponse,
  T2ICreateTemplatePayload,
  T2IDeleteImageResponse,
  T2IImage,
  T2IPatchImageResponse,
  T2ITaskDetail,
  T2ITaskListResponse,
  T2ITaskStatus,
  T2ITaskSummary,
  T2ITemplate,
  T2ITemplateCode,
  T2ITemplatesResponse,
  T2IUpdateTemplatePayload,
} from '../types/t2i'

const nowIso = () => new Date().toISOString()
const rid = () => Math.random().toString(36).slice(2, 10)

const templates: T2ITemplate[] = [
  {
    id: 'tpl-english-primer',
    code: 'english-primer',
    name: '英文启蒙',
    description: '给英文单词生成卡通配图',
    prompt:
      'A cute flat cartoon illustration of a {{item}}, kids education style, plain white background, no text.',
    order_index: 0,
    is_builtin: false,
    created_at: nowIso(),
    updated_at: nowIso(),
  },
  {
    id: 'tpl-general',
    code: 'general',
    name: '常规',
    description: '自由文生图',
    prompt: '{{item}}.',
    order_index: 1,
    is_builtin: false,
    created_at: nowIso(),
    updated_at: nowIso(),
  },
]

interface MockImage {
  id: string
  task_id: string
  status: 'generating' | 'succeeded' | 'failed'
  available: boolean
  url: string | null
  created_at: string
}

interface MockTask {
  id: string
  template_code: T2ITemplateCode
  keywords: Record<string, string>
  keywords_hash: string
  status: 'generating' | 'succeeded' | 'failed'
  last_failed: boolean
  created_at: string
  updated_at: string
}

const tasks: MockTask[] = []
const images: MockImage[] = []

function ok<T>(data: T): ApiResponse<T> {
  return { code: 0, data, message: 'ok' }
}
function err(code: number, message: string): ApiResponse<null> {
  return { code, data: null, message }
}
function delay<T>(v: T, ms = 220): Promise<T> {
  return new Promise((r) => setTimeout(() => r(v), ms))
}

function hashKeywords(code: string, kw: Record<string, string>): string {
  const canonical = Object.keys(kw)
    .sort()
    .map((k) => `${k}=${kw[k].trim()}`)
    .join('&')
  return `${code}|${canonical}`
}

function findTask(id: string): MockTask | undefined {
  return tasks.find((t) => t.id === id)
}
function taskImages(id: string): MockImage[] {
  return images
    .filter((img) => img.task_id === id)
    .sort((a, b) => (a.created_at < b.created_at ? 1 : -1))
}

function toTaskSummary(t: MockTask): T2ITaskSummary {
  const imgs = taskImages(t.id)
  const succeeded = imgs.filter((i) => i.status === 'succeeded')
  const available = succeeded.filter((i) => i.available).length
  const hasGenerating = imgs.some((i) => i.status === 'generating')
  const status: T2ITaskStatus = hasGenerating ? 'generating' : t.status
  return {
    id: t.id,
    template_code: t.template_code,
    keywords: t.keywords,
    summary: t.keywords.item ?? '',
    status,
    business_status: available > 0 ? 'done' : 'pending',
    images_total:
      succeeded.length + imgs.filter((i) => i.status === 'generating').length,
    images_available: available,
    last_failed: t.last_failed,
    thumbnails: succeeded.slice(0, 4).map((i) => i.url!).filter(Boolean),
    created_at: t.created_at,
    updated_at: t.updated_at,
  }
}

function scheduleGeneration(taskId: string, imageId: string) {
  const delayMs = 1500 + Math.floor(Math.random() * 1500)
  setTimeout(() => {
    const img = images.find((i) => i.id === imageId)
    const t = findTask(taskId)
    if (!img || !t) return
    const succeed = Math.random() > 0.1
    if (succeed) {
      img.status = 'succeeded'
      img.url = `https://placehold.co/512x512/2563EB/ffffff?text=${encodeURIComponent(t.keywords.item ?? '')}`
      t.status = 'succeeded'
      t.last_failed = false
    } else {
      img.status = 'failed'
      t.status = 'failed'
      t.last_failed = true
    }
    t.updated_at = nowIso()
  }, delayMs)
}

// ---------- Templates ----------

export async function getTemplatesMock(): Promise<ApiResponse<T2ITemplatesResponse>> {
  const sorted = [...templates].sort((a, b) => a.order_index - b.order_index)
  return delay(ok({ templates: sorted }))
}

export async function createTemplateMock(
  payload: T2ICreateTemplatePayload,
): Promise<ApiResponse<T2ITemplate | null>> {
  const code = payload.code.trim().toLowerCase()
  if (!/^[a-z][a-z0-9-]{1,63}$/.test(code)) {
    return delay(err(2030, 'code 只允许小写字母/数字/连字符'))
  }
  if (!payload.name.trim()) return delay(err(2031, 'name 不能为空'))
  if (!payload.prompt.includes('{{item}}')) {
    return delay(err(2032, 'prompt 必须包含占位符 {{item}}'))
  }
  if (templates.some((t) => t.code === code)) {
    return delay(err(2033, 'code 已存在'))
  }
  const now = nowIso()
  const tpl: T2ITemplate = {
    id: `tpl-${rid()}`,
    code,
    name: payload.name.trim(),
    description: (payload.description ?? '').trim() || null,
    prompt: payload.prompt.trim(),
    order_index: payload.order_index ?? 0,
    is_builtin: false,
    created_at: now,
    updated_at: now,
  }
  templates.push(tpl)
  return delay(ok(tpl))
}

export async function updateTemplateMock(
  id: string,
  payload: T2IUpdateTemplatePayload,
): Promise<ApiResponse<T2ITemplate | null>> {
  const tpl = templates.find((t) => t.id === id)
  if (!tpl) return delay(err(2034, '模板不存在'))
  if (tpl.is_builtin) return delay(err(2035, '内置模板不可修改'))
  if (!payload.name.trim()) return delay(err(2031, 'name 不能为空'))
  if (!payload.prompt.includes('{{item}}')) {
    return delay(err(2032, 'prompt 必须包含占位符 {{item}}'))
  }
  tpl.name = payload.name.trim()
  tpl.description = (payload.description ?? '').trim() || null
  tpl.prompt = payload.prompt.trim()
  if (payload.order_index !== undefined) tpl.order_index = payload.order_index
  tpl.updated_at = nowIso()
  return delay(ok(tpl))
}

export async function deleteTemplateMock(
  id: string,
): Promise<ApiResponse<{ id: string } | null>> {
  const idx = templates.findIndex((t) => t.id === id)
  if (idx < 0) return delay(err(2034, '模板不存在'))
  const tpl = templates[idx]
  if (tpl.is_builtin) return delay(err(2035, '内置模板不可删除'))
  const used = tasks.filter((t) => t.template_code === tpl.code).length
  if (used > 0) {
    return delay(err(2036, `该模板下已有 ${used} 个任务`))
  }
  templates.splice(idx, 1)
  return delay(ok({ id }))
}

// ---------- Tasks ----------

export async function listTasksMock(
  code: T2ITemplateCode,
  page = 1,
  pageSize = 20,
): Promise<ApiResponse<T2ITaskListResponse | null>> {
  const tpl = templates.find((t) => t.code === code)
  if (!tpl) return delay(err(2020, 'template_code 不存在'))
  if (page < 1 || pageSize < 1 || pageSize > 50) {
    return delay(err(2021, '分页参数非法'))
  }
  const filtered = tasks
    .filter((t) => t.template_code === code)
    .sort((a, b) => (a.updated_at < b.updated_at ? 1 : -1))
  const start = (page - 1) * pageSize
  const items = filtered.slice(start, start + pageSize).map(toTaskSummary)
  return delay(
    ok({
      template: { code: tpl.code, name: tpl.name },
      page,
      page_size: pageSize,
      total: filtered.length,
      items,
    }),
  )
}

export async function createTaskMock(
  code: T2ITemplateCode,
  keywords: Record<string, string>,
): Promise<ApiResponse<T2ICreateTaskResponse | null>> {
  const tpl = templates.find((t) => t.code === code)
  if (!tpl) return delay(err(2020, 'template_code 不存在'))
  const item = (keywords.item ?? '').trim()
  if (!item) return delay(err(2022, 'item 不能为空'))
  if (item.length > 100) return delay(err(2022, 'item 超长'))

  const normalized = { item }
  const hash = hashKeywords(code, normalized)
  const dup = tasks.find((t) => t.keywords_hash === hash)
  if (dup) {
    dup.updated_at = nowIso()
    return delay(ok({ existing: true, task: toTaskSummary(dup) }))
  }
  const now = nowIso()
  const id = `task-${rid()}`
  const task: MockTask = {
    id,
    template_code: code,
    keywords: normalized,
    keywords_hash: hash,
    status: 'generating',
    last_failed: false,
    created_at: now,
    updated_at: now,
  }
  tasks.push(task)
  const imgId = `${id}-img-1`
  images.push({
    id: imgId,
    task_id: id,
    status: 'generating',
    available: false,
    url: null,
    created_at: now,
  })
  scheduleGeneration(id, imgId)
  return delay(ok({ existing: false, task: toTaskSummary(task) }))
}

export async function getTaskMock(
  id: string,
): Promise<ApiResponse<T2ITaskDetail | null>> {
  const t = findTask(id)
  if (!t) return delay(err(2023, '任务不存在'))
  const imgs = taskImages(id)
  const failedCount = imgs.filter((i) => i.status === 'failed').length
  return delay(
    ok({
      task: { ...toTaskSummary(t), images_failed: failedCount },
      images: imgs.map((i) => ({
        id: i.id,
        status: i.status,
        available: i.available,
        url: i.url,
        created_at: i.created_at,
      })),
    }),
  )
}

export async function retryTaskMock(
  id: string,
): Promise<ApiResponse<{ image: T2IImage } | null>> {
  const t = findTask(id)
  if (!t) return delay(err(2023, '任务不存在'))
  if (taskImages(id).some((i) => i.status === 'generating')) {
    return delay(err(2024, '已有正在生成的图片，请稍候'))
  }
  const now = nowIso()
  const imgId = `${id}-img-${rid()}`
  images.push({
    id: imgId,
    task_id: id,
    status: 'generating',
    available: false,
    url: null,
    created_at: now,
  })
  t.status = 'generating'
  t.updated_at = now
  scheduleGeneration(id, imgId)
  return delay(
    ok({
      image: {
        id: imgId,
        status: 'generating',
        available: false,
        url: null,
        created_at: now,
      },
    }),
  )
}

export async function patchImageMock(
  id: string,
  available: boolean,
): Promise<ApiResponse<T2IPatchImageResponse | null>> {
  const img = images.find((i) => i.id === id)
  if (!img) return delay(err(2025, '图片不存在'))
  if (img.status !== 'succeeded') {
    return delay(err(2026, '只有已生成的图片可以标记'))
  }
  img.available = available
  const t = findTask(img.task_id)!
  t.updated_at = nowIso()
  const anyAvailable = taskImages(t.id).some((i) => i.available)
  return delay(
    ok({
      id: img.id,
      available: img.available,
      task_id: t.id,
      task_business_status: anyAvailable ? 'done' : 'pending',
    }),
  )
}

export async function deleteImageMock(
  id: string,
): Promise<ApiResponse<T2IDeleteImageResponse | null>> {
  const idx = images.findIndex((i) => i.id === id)
  if (idx < 0) return delay(err(2025, '图片不存在'))
  const img = images[idx]
  if (img.available) return delay(err(2027, '可用图片不可删除，请先取消可用'))
  const taskId = img.task_id
  images.splice(idx, 1)
  const t = findTask(taskId)!
  t.updated_at = nowIso()
  const remaining = taskImages(taskId)
  const availableLeft = remaining.filter((i) => i.available).length
  return delay(
    ok({
      id,
      task_id: taskId,
      images_total: remaining.length,
      images_available: availableLeft,
      task_business_status: availableLeft > 0 ? 'done' : 'pending',
    }),
  )
}
