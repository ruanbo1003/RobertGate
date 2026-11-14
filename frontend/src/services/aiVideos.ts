// AI Videos：API 客户端。
// 对应 docs/api/ai-videos.md
//
// VITE_AI_VIDEOS_MOCK：true → 走 aiVideos.mock.ts；false → 走真实后端。默认 true。

import type { ApiResponse } from '../types/auth'
import type {
  AssetKind,
  Character,
  CharacterPayload,
  CreateProjectPayload,
  GenerateAllPayload,
  ModelsMap,
  ProjectDetail,
  ProjectListResponse,
  ProjectStatusResponse,
  Script,
  Shot,
  ShotPatch,
  UpdateProjectPayload,
} from '../types/aiVideos'
import * as mock from './aiVideos.mock'

const USE_MOCK = (import.meta.env.VITE_AI_VIDEOS_MOCK ?? 'true') !== 'false'
const API_ORIGIN = (import.meta.env.VITE_API_BASE_URL ?? '') as string
const API_BASE = `${API_ORIGIN}/api/v1/ai-videos`

/** 产物相对路径拼上 API_ORIGIN；完整 URL（mock 占位图）原样返回。 */
export function resolveAssetUrl(url: string | null | undefined): string {
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

// ---------------- 模型 ----------------

export function getModels(): Promise<ApiResponse<{ models: ModelsMap }>> {
  if (USE_MOCK) return mock.getModelsMock()
  return request('/models')
}

// ---------------- 角色 ----------------

export function listCharacters(): Promise<ApiResponse<{ characters: Character[] }>> {
  if (USE_MOCK) return mock.listCharactersMock()
  return request('/characters')
}

export function createCharacter(
  payload: CharacterPayload,
): Promise<ApiResponse<{ character: Character } | null>> {
  if (USE_MOCK) return mock.createCharacterMock(payload)
  return request('/characters', { method: 'POST', body: JSON.stringify(payload) })
}

export function updateCharacter(
  id: number,
  payload: Partial<CharacterPayload>,
): Promise<ApiResponse<{ character: Character } | null>> {
  if (USE_MOCK) return mock.updateCharacterMock(id, payload)
  return request(`/characters/${id}`, { method: 'PUT', body: JSON.stringify(payload) })
}

export function deleteCharacter(id: number): Promise<ApiResponse<null>> {
  if (USE_MOCK) return mock.deleteCharacterMock(id)
  return request(`/characters/${id}`, { method: 'DELETE' })
}

export function generateCharacterImage(
  id: number,
  model: string,
  prompt?: string,
): Promise<ApiResponse<{ image: { id: number; url: string } } | null>> {
  if (USE_MOCK) return mock.generateCharacterImageMock(id, model, prompt)
  return request(`/characters/${id}/generate-image`, {
    method: 'POST',
    body: JSON.stringify({ model, prompt }),
  })
}

// ---------------- 项目 ----------------

export function listProjects(
  page = 1,
  pageSize = 20,
): Promise<ApiResponse<ProjectListResponse>> {
  if (USE_MOCK) return mock.listProjectsMock(page, pageSize)
  return request(`/projects?page=${page}&page_size=${pageSize}`)
}

export function createProject(
  payload: CreateProjectPayload,
): Promise<ApiResponse<{ project: ProjectDetail } | null>> {
  if (USE_MOCK) return mock.createProjectMock(payload)
  return request('/projects', { method: 'POST', body: JSON.stringify(payload) })
}

export function getProject(id: number): Promise<ApiResponse<{ project: ProjectDetail } | null>> {
  if (USE_MOCK) return mock.getProjectMock(id)
  return request(`/projects/${id}`)
}

export function updateProject(
  id: number,
  payload: UpdateProjectPayload,
): Promise<ApiResponse<{ project: ProjectDetail } | null>> {
  if (USE_MOCK) return mock.updateProjectMock(id, payload)
  return request(`/projects/${id}`, { method: 'PUT', body: JSON.stringify(payload) })
}

export function deleteProject(id: number): Promise<ApiResponse<null>> {
  if (USE_MOCK) return mock.deleteProjectMock(id)
  return request(`/projects/${id}`, { method: 'DELETE' })
}

// ---------------- 剧本 / 分镜 ----------------

export function generateScript(
  id: number,
  model: string,
): Promise<ApiResponse<{ script: Script } | null>> {
  if (USE_MOCK) return mock.generateScriptMock(id, model)
  return request(`/projects/${id}/script/generate`, {
    method: 'POST',
    body: JSON.stringify({ model }),
  })
}

export function updateScript(
  id: number,
  script: Script,
): Promise<ApiResponse<{ shots_exist: boolean } | null>> {
  if (USE_MOCK) return mock.updateScriptMock(id, script)
  return request(`/projects/${id}/script`, { method: 'PUT', body: JSON.stringify(script) })
}

export function splitShots(
  id: number,
  model: string,
  confirmReplace: boolean,
): Promise<ApiResponse<{ shots: Shot[] } | null>> {
  if (USE_MOCK) return mock.splitShotsMock(id, model, confirmReplace)
  return request(`/projects/${id}/shots/split`, {
    method: 'POST',
    body: JSON.stringify({ model, confirm_replace: confirmReplace }),
  })
}

export function createShot(
  id: number,
  afterShotId: number | null,
): Promise<ApiResponse<{ shot: Shot } | null>> {
  if (USE_MOCK) return mock.createShotMock(id, afterShotId)
  return request(`/projects/${id}/shots`, {
    method: 'POST',
    body: JSON.stringify({ after_shot_id: afterShotId }),
  })
}

export function updateShot(
  id: number,
  shotId: number,
  patch: ShotPatch,
): Promise<ApiResponse<{ shot: Shot } | null>> {
  if (USE_MOCK) return mock.updateShotMock(id, shotId, patch)
  return request(`/projects/${id}/shots/${shotId}`, {
    method: 'PUT',
    body: JSON.stringify(patch),
  })
}

export function deleteShot(id: number, shotId: number): Promise<ApiResponse<null>> {
  if (USE_MOCK) return mock.deleteShotMock(id, shotId)
  return request(`/projects/${id}/shots/${shotId}`, { method: 'DELETE' })
}

export function reorderShots(id: number, shotIds: number[]): Promise<ApiResponse<null>> {
  if (USE_MOCK) return mock.reorderShotsMock(id, shotIds)
  return request(`/projects/${id}/shots/order`, {
    method: 'PUT',
    body: JSON.stringify({ shot_ids: shotIds }),
  })
}

// ---------------- 生成 / 合成 ----------------

export function generateAsset(
  id: number,
  shotId: number,
  kind: AssetKind,
  model: string,
  voice?: string,
): Promise<ApiResponse<null>> {
  if (USE_MOCK) return mock.generateAssetMock(id, shotId, kind, model, voice)
  const body = kind === 'audio' ? { model, voice } : { model }
  return request(`/projects/${id}/shots/${shotId}/${kind}`, {
    method: 'POST',
    body: JSON.stringify(body),
  })
}

export function generateAll(
  id: number,
  payload: GenerateAllPayload,
): Promise<ApiResponse<{ enqueued: Record<AssetKind, number> } | null>> {
  if (USE_MOCK) return mock.generateAllMock(id, payload)
  return request(`/projects/${id}/generate-all`, {
    method: 'POST',
    body: JSON.stringify(payload),
  })
}

export function cancelQueue(id: number): Promise<ApiResponse<null>> {
  if (USE_MOCK) return mock.cancelQueueMock(id)
  return request(`/projects/${id}/queue/cancel`, { method: 'POST' })
}

export function composeProject(id: number, ignoreStale: boolean): Promise<ApiResponse<null>> {
  if (USE_MOCK) return mock.composeMock(id, ignoreStale)
  return request(`/projects/${id}/compose`, {
    method: 'POST',
    body: JSON.stringify({ ignore_stale: ignoreStale }),
  })
}

export function getProjectStatus(
  id: number,
): Promise<ApiResponse<ProjectStatusResponse | null>> {
  if (USE_MOCK) return mock.getStatusMock(id)
  return request(`/projects/${id}/status`)
}

export function downloadUrl(id: number): string {
  if (USE_MOCK) return 'https://www.w3schools.com/html/mov_bbb.mp4'
  return `${API_BASE}/projects/${id}/download`
}
