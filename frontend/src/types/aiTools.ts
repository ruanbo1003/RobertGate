// AI Tools 相关类型定义
// 对应 docs/api/ai-tools.md

// --- 翻译 ---
export type TranslateAction = 'translate' | 'grammar' | 'native'

export interface TextRequest {
  text: string
}

export interface TranslateResponse {
  source_lang: string
  target_lang: string
  result: string
}

// --- 汉字学习相关类型已迁移到 types/hanzi.ts（Level 化重构） ---

// --- 英文启蒙 ---
export interface EnglishWord {
  word: string
  translation: string
  image_url: string
}

export interface EnglishTheme {
  id: string
  name_en: string
  name_zh: string
  emoji: string
  ready: boolean
  words: EnglishWord[]
}

export interface EnglishThemesResponse {
  themes: EnglishTheme[]
}

export interface QuizQuestion {
  word: string
  translation: string
  options: string[]
  correct_index: number
}

export interface QuizResponse {
  theme_id: string
  questions: QuizQuestion[]
}

// --- 文生图 ---
export interface Text2ImageResponse {
  prompt: string
  image_url: string
  created_at: string
}
