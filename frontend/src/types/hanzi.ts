// 汉字学习（Level 化）相关类型
// 对应 docs/prd/hanzi-learning.md 和后续生成的 docs/api/hanzi-learning.md

// --- 级别 ---
// level 列表接口（用户 / admin）返回完整字段。
export interface HanziLevel {
  id: string
  name: string
  description: string | null
  order_index: number
  total: number
  learned: number // 当前用户已学数量（未登录/admin 视角为 0）
  created_at: string
  updated_at: string
}

// character list 接口内嵌的 level 摘要（不包含 total/learned/时间戳）
export interface HanziLevelSummary {
  id: string
  name: string
  description: string | null
  order_index: number
}

export interface HanziLevelListResponse {
  levels: HanziLevel[]
}

// --- 字条 ---
// 用户端字表接口不返回 level_id/created_at/updated_at；admin 接口才返回。
export interface HanziCharacter {
  id: string
  char: string
  pinyin: string
  example_words: string[]
  order_index: number
  learned?: boolean
  learned_at?: string | null
  level_id?: string
  created_at?: string
  updated_at?: string
}

export interface HanziCharacterListResponse {
  level: HanziLevelSummary
  characters: HanziCharacter[]
}

// --- 用户进度 ---
export interface UpdateProgressRequest {
  learned: boolean
}

export interface UpdateProgressResponse {
  character_id: string
  learned: boolean
  learned_at: string | null
}

// --- Admin：级别 CRUD ---
export interface CreateLevelRequest {
  name: string
  description?: string
  order_index?: number
}

export interface UpdateLevelRequest {
  name?: string
  description?: string
  order_index?: number
}

// --- Admin：字条 CRUD ---
export interface CreateCharacterRequest {
  char: string
  pinyin: string
  example_words?: string[]
  order_index?: number
}

export interface UpdateCharacterRequest {
  char?: string
  pinyin?: string
  example_words?: string[]
  order_index?: number
}

// --- Admin：AI 批量添加 ---
export interface AiAddRequest {
  text: string
}

export interface AiAddedCharacter {
  id: string
  char: string
  pinyin: string
  example_words: string[]
  order_index: number
  level_id?: string
  created_at?: string
  updated_at?: string
}

export interface AiAddResponse {
  ok: number
  added: AiAddedCharacter[]
  skipped: { char: string; reason: string }[]
  failed: { char: string; reason: string }[]
}

// --- 组合练习 ---
export interface PinyinAnnotation {
  char: string
  pinyin: string
}

export interface PracticeTextResponse {
  text: string
  annotations: PinyinAnnotation[]
  new_chars: string[]
}
