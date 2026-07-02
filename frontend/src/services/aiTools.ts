// AI Tools 服务层：调用真实后端接口。
// 对应 docs/api/ai-tools.md

import type { ApiResponse } from '../types/auth'
import type {
  AddHanziResponse,
  CharacterInfoResponse,
  DeleteHanziResponse,
  EnglishThemesResponse,
  HanziLibraryResponse,
  QuizResponse,
  SentenceResponse,
  Text2ImageResponse,
  TranslateAction,
  TranslateResponse,
  UpdateHanziResponse,
} from '../types/aiTools'

const API_BASE = '/api/v1'

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

// --- 汉字字库 ---
export function getHanziLibrary(): Promise<ApiResponse<HanziLibraryResponse>> {
  return request('/hanzi/library')
}

export function addHanzi(text: string): Promise<ApiResponse<AddHanziResponse>> {
  return request('/hanzi/library', {
    method: 'POST',
    body: JSON.stringify({ text }),
  })
}

export function updateHanzi(
  char: string,
  learned: boolean
): Promise<ApiResponse<UpdateHanziResponse>> {
  return request(`/hanzi/library/${encodeURIComponent(char)}`, {
    method: 'PATCH',
    body: JSON.stringify({ learned }),
  })
}

export function deleteHanzi(char: string): Promise<ApiResponse<DeleteHanziResponse>> {
  return request(`/hanzi/library/${encodeURIComponent(char)}`, {
    method: 'DELETE',
  })
}

// --- 单字信息 ---
export function getCharacterInfo(char: string): Promise<ApiResponse<CharacterInfoResponse>> {
  return request('/ai/character-info', {
    method: 'POST',
    body: JSON.stringify({ char }),
  })
}

// --- 句子学习 ---
export function getSentence(knownChars: string[]): Promise<ApiResponse<SentenceResponse>> {
  return request('/ai/sentence', {
    method: 'POST',
    body: JSON.stringify({ known_chars: knownChars }),
  })
}

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
