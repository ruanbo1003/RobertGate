// AI Tools 服务层：调用真实后端接口。
// 对应 docs/api/ai-tools.md

import type { ApiResponse } from '../types/auth'
import type {
  EnglishThemesResponse,
  QuizResponse,
  Text2ImageResponse,
  TranslateAction,
  TranslateResponse,
} from '../types/aiTools'

const API_BASE = `${import.meta.env.VITE_API_BASE_URL ?? ''}/api/v1`

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
  } catch (err) {
    if (err instanceof TypeError) {
      return { code: 5001, data: null as T, message: '网络连接失败，请检查网络' }
    }
    return { code: 5000, data: null as T, message: '请求失败，请稍后重试' }
  }
}

// --- 翻译 / 英文优化 ---
export function translate(
  text: string,
  action: TranslateAction
): Promise<ApiResponse<TranslateResponse>> {
  return request('/ai/translate', {
    method: 'POST',
    body: JSON.stringify({ text, action }),
  })
}

// --- 汉字学习：迁移到 services/hanzi.ts（Level 化重构） ---

// --- 英文启蒙 ---
export function getEnglishThemes(): Promise<ApiResponse<EnglishThemesResponse>> {
  return request('/english/themes')
}

export function getEnglishQuiz(
  themeId: string,
  count = 10
): Promise<ApiResponse<QuizResponse>> {
  return request('/english/quiz', {
    method: 'POST',
    body: JSON.stringify({ theme_id: themeId, count }),
  })
}

// --- 文生图 ---
export function textToImage(prompt: string): Promise<ApiResponse<Text2ImageResponse>> {
  return request('/ai/text-to-image', {
    method: 'POST',
    body: JSON.stringify({ prompt }),
  })
}
