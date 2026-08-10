// 汉字学习：API 客户端。
// 对应 docs/api/hanzi-learning.md
//
// 通过 VITE_HANZI_MOCK 切换：
//   true  → 走 hanzi.mock.ts 的内存实现（Step 4 前端联调用）
//   false → 走真实后端（Step 6 联调切换）
// 默认 true，直到后端接口上线。

import type { ApiResponse } from '../types/auth'
import type {
  AiAddResponse,
  CreateCharacterRequest,
  CreateLevelRequest,
  HanziCharacter,
  HanziCharacterListResponse,
  HanziLevel,
  HanziLevelListResponse,
  PracticeTextResponse,
  UpdateCharacterRequest,
  UpdateLevelRequest,
  UpdateProgressResponse,
} from '../types/hanzi'
import * as mock from './hanzi.mock'

const USE_MOCK = (import.meta.env.VITE_HANZI_MOCK ?? 'true') !== 'false'
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
  } catch (e) {
    if (e instanceof TypeError) {
      return { code: 5001, data: null as T, message: '网络连接失败，请检查网络' }
    }
    return { code: 5000, data: null as T, message: '请求失败，请稍后重试' }
  }
}

// ---------- 用户接口 ----------

export function getLevels(): Promise<ApiResponse<HanziLevelListResponse>> {
  if (USE_MOCK) return mock.getLevelsMock()
  return request('/hanzi/levels')
}

export function getLevelCharacters(
  levelId: string,
): Promise<ApiResponse<HanziCharacterListResponse | null>> {
  if (USE_MOCK) return mock.getLevelCharactersMock(levelId)
  return request(`/hanzi/levels/${encodeURIComponent(levelId)}/characters`)
}

export function updateProgress(
  characterId: string,
  learned: boolean,
): Promise<ApiResponse<UpdateProgressResponse | null>> {
  if (USE_MOCK) return mock.updateProgressMock(characterId, learned)
  return request(`/hanzi/progress/${encodeURIComponent(characterId)}`, {
    method: 'PUT',
    body: JSON.stringify({ learned }),
  })
}

export function getPracticeText(
  levelId: string,
): Promise<ApiResponse<PracticeTextResponse | null>> {
  if (USE_MOCK) return mock.getPracticeTextMock(levelId)
  return request('/hanzi/practice-text', {
    method: 'POST',
    body: JSON.stringify({ level_id: levelId }),
  })
}

// ---------- Admin：级别 ----------

export function adminListLevels(): Promise<ApiResponse<HanziLevelListResponse>> {
  if (USE_MOCK) return mock.adminListLevelsMock()
  return request('/admin/hanzi/levels')
}

export function adminCreateLevel(
  payload: CreateLevelRequest,
): Promise<ApiResponse<HanziLevel | null>> {
  if (USE_MOCK) return mock.adminCreateLevelMock(payload)
  return request('/admin/hanzi/levels', {
    method: 'POST',
    body: JSON.stringify(payload),
  })
}

export function adminUpdateLevel(
  id: string,
  payload: UpdateLevelRequest,
): Promise<ApiResponse<HanziLevel | null>> {
  if (USE_MOCK) return mock.adminUpdateLevelMock(id, payload)
  return request(`/admin/hanzi/levels/${encodeURIComponent(id)}`, {
    method: 'PUT',
    body: JSON.stringify(payload),
  })
}

export function adminDeleteLevel(id: string): Promise<ApiResponse<null>> {
  if (USE_MOCK) return mock.adminDeleteLevelMock(id)
  return request(`/admin/hanzi/levels/${encodeURIComponent(id)}`, {
    method: 'DELETE',
  })
}

// ---------- Admin：字条 ----------

export function adminListCharacters(
  levelId: string,
): Promise<ApiResponse<HanziCharacterListResponse | null>> {
  if (USE_MOCK) return mock.adminListCharactersMock(levelId)
  return request(`/admin/hanzi/levels/${encodeURIComponent(levelId)}/characters`)
}

export function adminCreateCharacter(
  levelId: string,
  payload: CreateCharacterRequest,
): Promise<ApiResponse<HanziCharacter | null>> {
  if (USE_MOCK) return mock.adminCreateCharacterMock(levelId, payload)
  return request(`/admin/hanzi/levels/${encodeURIComponent(levelId)}/characters`, {
    method: 'POST',
    body: JSON.stringify(payload),
  })
}

export function adminAiAddCharacters(
  levelId: string,
  text: string,
): Promise<ApiResponse<AiAddResponse | null>> {
  if (USE_MOCK) return mock.adminAiAddCharactersMock(levelId, text)
  return request(`/admin/hanzi/levels/${encodeURIComponent(levelId)}/characters/ai-add`, {
    method: 'POST',
    body: JSON.stringify({ text }),
  })
}

export function adminUpdateCharacter(
  id: string,
  payload: UpdateCharacterRequest,
): Promise<ApiResponse<HanziCharacter | null>> {
  if (USE_MOCK) return mock.adminUpdateCharacterMock(id, payload)
  return request(`/admin/hanzi/characters/${encodeURIComponent(id)}`, {
    method: 'PUT',
    body: JSON.stringify(payload),
  })
}

export function adminDeleteCharacter(id: string): Promise<ApiResponse<null>> {
  if (USE_MOCK) return mock.adminDeleteCharacterMock(id)
  return request(`/admin/hanzi/characters/${encodeURIComponent(id)}`, {
    method: 'DELETE',
  })
}
