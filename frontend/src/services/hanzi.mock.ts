// 汉字学习：内存 mock 后端。Step 4 用；Step 6 联调时通过 VITE_HANZI_MOCK=false 切换到真实接口。
// 状态在 session 内保留（页面刷新会重置），符合 mock 一次性演示需求。

import type { ApiResponse } from '../types/auth'
import type {
  BatchImportItem,
  BatchImportResult,
  CreateCharacterRequest,
  CreateLevelRequest,
  HanziCharacter,
  HanziCharacterListResponse,
  HanziLevel,
  HanziLevelListResponse,
  UpdateCharacterRequest,
  UpdateLevelRequest,
  UpdateProgressResponse,
} from '../types/hanzi'
import { mockCharacters as seedCharacters, mockLevels as seedLevels } from '../mocks/hanzi'

const HANZI_RE = /^[\u4e00-\u9fa5]$/
const BATCH_LIMIT = 200

// ---------- 内存存储 ----------

const levels: HanziLevel[] = seedLevels.map((l) => ({ ...l }))
const characters: HanziCharacter[] = Object.values(seedCharacters)
  .flat()
  .map((c) => ({ ...c }))
// 用户进度：character_id → learned_at（有记录即已学）
const progress = new Map<string, string>()
// 初始化：seed 里 learned=true 的字条写入 progress
characters.forEach((c) => {
  if (c.learned && c.learned_at) progress.set(c.id, c.learned_at)
})

function nowIso() {
  return new Date().toISOString()
}

function ok<T>(data: T): ApiResponse<T> {
  return { code: 0, data, message: 'ok' }
}

function err(code: number, message: string): ApiResponse<null> {
  return { code, data: null, message }
}

function findLevel(id: string): HanziLevel | undefined {
  return levels.find((l) => l.id === id)
}

function findCharacter(id: string): HanziCharacter | undefined {
  return characters.find((c) => c.id === id)
}

function levelTotal(levelId: string): number {
  return characters.filter((c) => c.level_id === levelId).length
}

function levelLearned(levelId: string): number {
  return characters.filter((c) => c.level_id === levelId && progress.has(c.id)).length
}

function decorateLevel(l: HanziLevel): HanziLevel {
  return { ...l, total: levelTotal(l.id), learned: levelLearned(l.id) }
}

function decorateCharacter(c: HanziCharacter): HanziCharacter {
  const learnedAt = progress.get(c.id) ?? null
  return { ...c, learned: !!learnedAt, learned_at: learnedAt }
}

// 模拟网络延迟
function delay<T>(v: T, ms = 180): Promise<T> {
  return new Promise((resolve) => setTimeout(() => resolve(v), ms))
}

// ---------- 用户接口 ----------

export async function getLevelsMock(): Promise<ApiResponse<HanziLevelListResponse>> {
  const data: HanziLevelListResponse = {
    levels: [...levels]
      .sort((a, b) => a.order_index - b.order_index)
      .map(decorateLevel),
  }
  return delay(ok(data))
}

export async function getLevelCharactersMock(
  levelId: string,
): Promise<ApiResponse<HanziCharacterListResponse | null>> {
  const level = findLevel(levelId)
  if (!level) return delay(err(2010, '级别不存在'))
  const chars = characters
    .filter((c) => c.level_id === levelId)
    .sort((a, b) => a.order_index - b.order_index)
    .map(decorateCharacter)
  return delay(ok<HanziCharacterListResponse>({ level: decorateLevel(level), characters: chars }))
}

export async function updateProgressMock(
  characterId: string,
  learned: boolean,
): Promise<ApiResponse<UpdateProgressResponse | null>> {
  const c = findCharacter(characterId)
  if (!c) return delay(err(2010, '字条不存在'))
  if (learned) {
    if (!progress.has(characterId)) progress.set(characterId, nowIso())
    return delay(
      ok<UpdateProgressResponse>({
        character_id: characterId,
        learned: true,
        learned_at: progress.get(characterId) ?? null,
      }),
    )
  }
  progress.delete(characterId)
  return delay(
    ok<UpdateProgressResponse>({
      character_id: characterId,
      learned: false,
      learned_at: null,
    }),
  )
}

// ---------- Admin：级别 ----------

export async function adminListLevelsMock(): Promise<ApiResponse<HanziLevelListResponse>> {
  const data: HanziLevelListResponse = {
    levels: [...levels]
      .sort((a, b) => a.order_index - b.order_index)
      .map(decorateLevel),
  }
  return delay(ok(data))
}

export async function adminCreateLevelMock(
  payload: CreateLevelRequest,
): Promise<ApiResponse<HanziLevel | null>> {
  if (!payload.name?.trim()) return delay(err(2001, 'name 不能为空'))
  if (payload.name.length > 64) return delay(err(2003, 'name 超长'))
  if (levels.some((l) => l.name === payload.name)) return delay(err(2011, 'name 已存在'))
  const now = nowIso()
  const orderIndex =
    payload.order_index ??
    (levels.length ? Math.max(...levels.map((l) => l.order_index)) + 1 : 1)
  const created: HanziLevel = {
    id: `lvl-${Date.now()}`,
    name: payload.name.trim(),
    description: payload.description?.trim() || null,
    order_index: orderIndex,
    total: 0,
    learned: 0,
    created_at: now,
    updated_at: now,
  }
  levels.push(created)
  return delay(ok(created))
}

export async function adminUpdateLevelMock(
  id: string,
  payload: UpdateLevelRequest,
): Promise<ApiResponse<HanziLevel | null>> {
  const l = findLevel(id)
  if (!l) return delay(err(2010, '级别不存在'))
  if (payload.name !== undefined) {
    if (!payload.name.trim()) return delay(err(2001, 'name 不能为空'))
    if (payload.name.length > 64) return delay(err(2003, 'name 超长'))
    if (levels.some((x) => x.id !== id && x.name === payload.name))
      return delay(err(2011, 'name 已存在'))
    l.name = payload.name.trim()
  }
  if (payload.description !== undefined) {
    l.description = payload.description?.trim() || null
  }
  if (payload.order_index !== undefined) {
    l.order_index = payload.order_index
  }
  l.updated_at = nowIso()
  return delay(ok(decorateLevel(l)))
}

export async function adminDeleteLevelMock(id: string): Promise<ApiResponse<null>> {
  const l = findLevel(id)
  if (!l) return delay(err(2010, '级别不存在'))
  if (levelTotal(id) > 0) return delay(err(2012, '级别下仍有字条，请先清空'))
  const idx = levels.findIndex((x) => x.id === id)
  levels.splice(idx, 1)
  return delay(ok(null))
}

// ---------- Admin：字条 ----------

export async function adminListCharactersMock(
  levelId: string,
): Promise<ApiResponse<HanziCharacterListResponse | null>> {
  const level = findLevel(levelId)
  if (!level) return delay(err(2010, '级别不存在'))
  const chars = characters
    .filter((c) => c.level_id === levelId)
    .sort((a, b) => a.order_index - b.order_index)
    .map(decorateCharacter)
  return delay(ok<HanziCharacterListResponse>({ level: decorateLevel(level), characters: chars }))
}

export async function adminCreateCharacterMock(
  levelId: string,
  payload: CreateCharacterRequest,
): Promise<ApiResponse<HanziCharacter | null>> {
  const level = findLevel(levelId)
  if (!level) return delay(err(2010, '级别不存在'))
  if (!payload.char) return delay(err(2001, 'char 不能为空'))
  if (!HANZI_RE.test(payload.char)) return delay(err(2002, 'char 必须是 1 个汉字'))
  if (!payload.pinyin?.trim()) return delay(err(2001, 'pinyin 不能为空'))
  if (payload.pinyin.length > 32) return delay(err(2003, 'pinyin 超长'))
  if (characters.some((c) => c.char === payload.char))
    return delay(err(2011, '字已存在于其他级别（全局唯一）'))
  const now = nowIso()
  const orderIndex =
    payload.order_index ??
    (characters.filter((c) => c.level_id === levelId).length
      ? Math.max(
          ...characters.filter((c) => c.level_id === levelId).map((c) => c.order_index),
        ) + 1
      : 0)
  const created: HanziCharacter = {
    id: `char-${Date.now()}`,
    level_id: levelId,
    char: payload.char,
    pinyin: payload.pinyin.trim(),
    meaning: payload.meaning?.trim() || null,
    order_index: orderIndex,
    learned: false,
    learned_at: null,
    created_at: now,
    updated_at: now,
  }
  characters.push(created)
  return delay(ok(created))
}

export async function adminBatchImportMock(
  levelId: string,
  items: BatchImportItem[],
): Promise<ApiResponse<BatchImportResult | null>> {
  const level = findLevel(levelId)
  if (!level) return delay(err(2010, '级别不存在'))
  if (!items.length) return delay(err(2001, 'items 不能为空'))
  if (items.length > BATCH_LIMIT) return delay(err(2003, `items 超过上限 ${BATCH_LIMIT}`))
  const failed: { char: string; reason: string }[] = []
  let base =
    characters.filter((c) => c.level_id === levelId).length
      ? Math.max(
          ...characters.filter((c) => c.level_id === levelId).map((c) => c.order_index),
        ) + 1
      : 0
  const now = nowIso()
  let okCount = 0
  for (const item of items) {
    if (!item.char || !HANZI_RE.test(item.char)) {
      failed.push({ char: item.char, reason: '不是单个汉字' })
      continue
    }
    if (!item.pinyin?.trim()) {
      failed.push({ char: item.char, reason: 'pinyin 缺失' })
      continue
    }
    if (characters.some((c) => c.char === item.char)) {
      failed.push({ char: item.char, reason: '已存在（全局唯一）' })
      continue
    }
    characters.push({
      id: `char-${Date.now()}-${base}`,
      level_id: levelId,
      char: item.char,
      pinyin: item.pinyin.trim(),
      meaning: item.meaning?.trim() || null,
      order_index: base++,
      learned: false,
      learned_at: null,
      created_at: now,
      updated_at: now,
    })
    okCount++
  }
  return delay(ok<BatchImportResult>({ ok: okCount, failed }), 300)
}

export async function adminUpdateCharacterMock(
  id: string,
  payload: UpdateCharacterRequest,
): Promise<ApiResponse<HanziCharacter | null>> {
  const c = findCharacter(id)
  if (!c) return delay(err(2010, '字条不存在'))
  if (payload.char !== undefined) {
    if (!HANZI_RE.test(payload.char)) return delay(err(2002, 'char 必须是 1 个汉字'))
    if (characters.some((x) => x.id !== id && x.char === payload.char))
      return delay(err(2011, '字已存在（全局唯一）'))
    c.char = payload.char
  }
  if (payload.pinyin !== undefined) {
    if (!payload.pinyin.trim()) return delay(err(2001, 'pinyin 不能为空'))
    if (payload.pinyin.length > 32) return delay(err(2003, 'pinyin 超长'))
    c.pinyin = payload.pinyin.trim()
  }
  if (payload.meaning !== undefined) {
    c.meaning = payload.meaning?.trim() || null
  }
  if (payload.order_index !== undefined) {
    c.order_index = payload.order_index
  }
  c.updated_at = nowIso()
  return delay(ok(decorateCharacter(c)))
}

export async function adminDeleteCharacterMock(id: string): Promise<ApiResponse<null>> {
  const c = findCharacter(id)
  if (!c) return delay(err(2010, '字条不存在'))
  const idx = characters.findIndex((x) => x.id === id)
  characters.splice(idx, 1)
  progress.delete(id) // 级联清理进度
  return delay(ok(null))
}
