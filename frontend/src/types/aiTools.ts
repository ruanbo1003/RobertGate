// AI Tools 相关类型定义
// 对应 docs/api/ai-tools.md

// --- 翻译 ---
export type TranslateAction = 'translate' | 'grammar' | 'native'

export interface TranslateRequest {
  text: string
  action: TranslateAction
}

export interface TranslateResponse {
  action: TranslateAction
  source_lang: string
  target_lang: string
  result: string
}

// --- 汉字字库 ---
export interface HanziItem {
  char: string
  learned: boolean
  created_at: string
  learned_at: string | null
}

export interface HanziLibraryResponse {
  total: number
  learned: number
  items: HanziItem[]
}

export interface AddHanziResponse {
  added: string[]
  duplicated: string[]
  total: number
}

export interface UpdateHanziResponse {
  char: string
  learned: boolean
  learned_at: string
}

export interface DeleteHanziResponse {
  char: string
  total: number
}

// --- 单字信息 ---
export interface CharacterInfoResponse {
  char: string
  pinyin: string
  words: string[]
  sentence: string
  sentence_pinyin: string
}

// --- 句子学习 ---
export interface SentenceResponse {
  sentence: string
  pinyin: string
  translation: string
  out_of_vocab: string[]
}

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
