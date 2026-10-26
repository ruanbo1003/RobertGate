// 法律咨询（RAG 对话）：API 客户端。
// 对应 docs/api/legal-consult.md
//
// VITE_LEGAL_MOCK：true → 走 legalConsult.mock.ts；false → 走真实后端。默认 true。

import type { ApiResponse } from '../types/auth'
import type {
  LawArticleResponse,
  LegalMessagesResponse,
  SendMessageHandlers,
} from '../types/legalConsult'
import * as mock from './legalConsult.mock'

const USE_MOCK = (import.meta.env.VITE_LEGAL_MOCK ?? 'true') !== 'false'
const API_ORIGIN = (import.meta.env.VITE_API_BASE_URL ?? '') as string
const API_BASE = `${API_ORIGIN}/api/v1`

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

export function getMessages(): Promise<ApiResponse<LegalMessagesResponse>> {
  if (USE_MOCK) return mock.getMessagesMock()
  return request('/legal-consult/messages')
}

export function clearMessages(): Promise<ApiResponse<null>> {
  if (USE_MOCK) return mock.clearMessagesMock()
  return request('/legal-consult/messages', { method: 'DELETE' })
}

export function getArticle(articleNo: number): Promise<ApiResponse<LawArticleResponse>> {
  if (USE_MOCK) return mock.getArticleMock(articleNo)
  return request(`/legal-consult/articles/${articleNo}`)
}

/**
 * 发送消息，SSE 流式接收回答。
 * 事件顺序：citations → delta（多次）→ done；任一环节失败触发 onError。
 */
export async function sendMessage(
  content: string,
  handlers: SendMessageHandlers,
): Promise<void> {
  if (USE_MOCK) return mock.sendMessageMock(content, handlers)

  let res: Response
  try {
    res = await fetch(`${API_BASE}/legal-consult/messages`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        Accept: 'text/event-stream',
        ...authHeaders(),
      },
      body: JSON.stringify({ content }),
    })
  } catch {
    handlers.onError(5001, '网络连接失败，请检查网络')
    return
  }

  // 建流前的校验失败走统一 JSON 格式
  const contentType = res.headers.get('content-type') ?? ''
  if (!contentType.includes('text/event-stream')) {
    try {
      const json = (await res.json()) as ApiResponse<null>
      handlers.onError(json.code, json.message)
    } catch {
      handlers.onError(5000, '服务器异常，请稍后重试')
    }
    return
  }

  if (!res.body) {
    handlers.onError(5000, '服务器异常，请稍后重试')
    return
  }

  const reader = res.body.getReader()
  const decoder = new TextDecoder()
  let buffer = ''
  let done = false

  const dispatch = (eventName: string, data: string) => {
    try {
      const payload: unknown = JSON.parse(data)
      switch (eventName) {
        case 'citations': {
          const p = payload as { citations: import('../types/legalConsult').Citation[] }
          handlers.onCitations(p.citations ?? [])
          break
        }
        case 'delta': {
          const p = payload as { text: string }
          handlers.onDelta(p.text ?? '')
          break
        }
        case 'done': {
          const p = payload as { message: import('../types/legalConsult').LegalMessage }
          done = true
          handlers.onDone(p.message)
          break
        }
        case 'error': {
          const p = payload as { code: number; message: string }
          done = true
          handlers.onError(p.code, p.message)
          break
        }
      }
    } catch {
      // 忽略无法解析的事件帧
    }
  }

  const parseBuffer = () => {
    let idx = buffer.indexOf('\n\n')
    while (idx >= 0) {
      const frame = buffer.slice(0, idx)
      buffer = buffer.slice(idx + 2)
      let eventName = 'message'
      const dataLines: string[] = []
      for (const line of frame.split('\n')) {
        if (line.startsWith('event:')) eventName = line.slice(6).trim()
        else if (line.startsWith('data:')) dataLines.push(line.slice(5).trim())
      }
      if (dataLines.length > 0) dispatch(eventName, dataLines.join('\n'))
      idx = buffer.indexOf('\n\n')
    }
  }

  try {
    for (;;) {
      const { value, done: streamEnd } = await reader.read()
      if (streamEnd) break
      buffer += decoder.decode(value, { stream: true })
      parseBuffer()
    }
  } catch {
    if (!done) handlers.onError(5001, '连接中断，请重试')
    return
  }

  if (!done) handlers.onError(5000, '响应异常中断，请重试')
}
