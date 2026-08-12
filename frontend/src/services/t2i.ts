// 文生图任务化：API 客户端。
// 对应 docs/api/text-to-image-tasks.md
//
// VITE_T2I_MOCK：true → 走 t2i.mock.ts；false → 走真实后端。默认 true。

import type { ApiResponse } from '../types/auth'
import type {
  T2ICreateTaskResponse,
  T2ICreateTemplatePayload,
  T2IDeleteImageResponse,
  T2IImage,
  T2IPatchImageResponse,
  T2ITaskDetail,
  T2ITaskListResponse,
  T2ITemplate,
  T2ITemplateCode,
  T2ITemplatesResponse,
  T2IUpdateTemplatePayload,
} from '../types/t2i'
import * as mock from './t2i.mock'

const USE_MOCK = (import.meta.env.VITE_T2I_MOCK ?? 'true') !== 'false'
const API_ORIGIN = (import.meta.env.VITE_API_BASE_URL ?? '') as string
const API_BASE = `${API_ORIGIN}/api/v1`

/**
 * 把后端返回的图片相对路径（形如 "/api/v1/ai/t2i/images/xxx"）拼上 API_ORIGIN。
 * - 未设 VITE_API_BASE_URL 时保持相对，由 Vite dev proxy / nginx 转发；
 * - 设了跨源 base URL 时，强制走同一后端，避免跟 fetch 走两条链路。
 * - 已经是完整 URL 的（mock 用的 placehold.co）原样返回。
 */
export function resolveImageUrl(url: string | null | undefined): string {
  if (!url) return ''
  if (/^https?:\/\//i.test(url)) return url
  if (!API_ORIGIN) return url
  return `${API_ORIGIN}${url}`
}

function authHeaders(): Record<string, string> {
  const token = localStorage.getItem('token')
  return token ? { Authorization: `Bearer ${token}` } : {}
}

async function request<T>(path: string, options?: RequestInit): Promise<ApiResponse<T>> {
  try {
    const res = await fetch(`${API_BASE}${path}`, {
      headers: {
        'Content-Type': 'application/json',
        ...authHeaders(),
        ...(options?.headers ?? {}),
      },
      ...options,
    })
    if (!res.ok && res.status >= 500) {
      return { code: 5000, data: null as T, message: '服务器异常，请稍后重试' }
    }
    return await res.json()
  } catch (e) {
    if (e instanceof TypeError) {
      return { code: 5001, data: null as T, message: '网络连接失败，请检查网络' }
    }
    return { code: 5000, data: null as T, message: '请求失败，请稍后重试' }
  }
}

export function getTemplates(): Promise<ApiResponse<T2ITemplatesResponse>> {
  if (USE_MOCK) return mock.getTemplatesMock()
  return request('/ai/t2i/templates')
}

export function createTemplate(
  payload: T2ICreateTemplatePayload,
): Promise<ApiResponse<T2ITemplate | null>> {
  if (USE_MOCK) return mock.createTemplateMock(payload)
  return request('/ai/t2i/templates', {
    method: 'POST',
    body: JSON.stringify(payload),
  })
}

export function updateTemplate(
  id: string,
  payload: T2IUpdateTemplatePayload,
): Promise<ApiResponse<T2ITemplate | null>> {
  if (USE_MOCK) return mock.updateTemplateMock(id, payload)
  return request(`/ai/t2i/templates/${encodeURIComponent(id)}`, {
    method: 'PUT',
    body: JSON.stringify(payload),
  })
}

export function deleteTemplate(id: string): Promise<ApiResponse<{ id: string } | null>> {
  if (USE_MOCK) return mock.deleteTemplateMock(id)
  return request(`/ai/t2i/templates/${encodeURIComponent(id)}`, { method: 'DELETE' })
}

export function listTasks(
  code: T2ITemplateCode,
  page = 1,
  pageSize = 20,
): Promise<ApiResponse<T2ITaskListResponse | null>> {
  if (USE_MOCK) return mock.listTasksMock(code, page, pageSize)
  const qs = `?page=${page}&page_size=${pageSize}`
  return request(`/ai/t2i/templates/${encodeURIComponent(code)}/tasks${qs}`)
}

export function createTask(
  code: T2ITemplateCode,
  keywords: Record<string, string>,
): Promise<ApiResponse<T2ICreateTaskResponse | null>> {
  if (USE_MOCK) return mock.createTaskMock(code, keywords)
  return request(`/ai/t2i/templates/${encodeURIComponent(code)}/tasks`, {
    method: 'POST',
    body: JSON.stringify(keywords),
  })
}

export function getTask(id: string): Promise<ApiResponse<T2ITaskDetail | null>> {
  if (USE_MOCK) return mock.getTaskMock(id)
  return request(`/ai/t2i/tasks/${encodeURIComponent(id)}`)
}

export function retryTask(id: string): Promise<ApiResponse<{ image: T2IImage } | null>> {
  if (USE_MOCK) return mock.retryTaskMock(id)
  return request(`/ai/t2i/tasks/${encodeURIComponent(id)}/retry`, { method: 'POST' })
}

export function patchImage(
  id: string,
  available: boolean,
): Promise<ApiResponse<T2IPatchImageResponse | null>> {
  if (USE_MOCK) return mock.patchImageMock(id, available)
  return request(`/ai/t2i/images/${encodeURIComponent(id)}`, {
    method: 'PATCH',
    body: JSON.stringify({ available }),
  })
}

export function deleteImage(id: string): Promise<ApiResponse<T2IDeleteImageResponse | null>> {
  if (USE_MOCK) return mock.deleteImageMock(id)
  return request(`/ai/t2i/images/${encodeURIComponent(id)}`, { method: 'DELETE' })
}
