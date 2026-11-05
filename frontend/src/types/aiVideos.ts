// AI Videos（英语启蒙短视频工作台）类型定义。
// 对应 docs/api/ai-videos.md

export type AssetState = 'pending' | 'running' | 'success' | 'failed'
export type AssetKind = 'image' | 'video' | 'audio'
export type ProjectStatus = 'draft' | 'generating' | 'partial_failed' | 'completed'
export type ComposeState = 'none' | 'running' | 'success' | 'failed'
export type ModelType = 'llm' | 't2i' | 'i2v' | 'tts'

export interface ModelInfo {
  id: string
  name: string
  default?: boolean
  /** t2i 参考图能力档：multi 多参考图 / none 纯 prompt */
  reference?: 'multi' | 'none'
  voices?: string[]
}

export type ModelsMap = Record<ModelType, ModelInfo[]>

export interface CandidateImage {
  id: number
  url: string
}

export interface Character {
  id: number
  name: string
  appearance_prompt: string
  personality: string | null
  cover_image_url: string | null
  candidate_images: CandidateImage[]
  used_count: number
  created_at: string
  updated_at: string
}

export interface CharacterPayload {
  name: string
  appearance_prompt: string
  personality?: string
  cover_image_id?: number
}

export interface CharacterRef {
  id: number
  name: string
  cover_image_url: string | null
}

export interface ScriptLine {
  character_id: number
  en: string
  zh: string
  /** LLM 生成的动作/运镜提示（可选，拆分镜时落入 shot.video_prompt） */
  video_prompt?: string
  /** 该镜出场角色名（可选，拆分镜时解析为 ref_character_ids） */
  characters?: string[]
}

export interface ScriptScene {
  setting: string
  lines: ScriptLine[]
}

export interface Script {
  scenes: ScriptScene[]
}

export interface ShotAsset {
  state: AssetState
  url: string | null
  model: string
  stale: boolean
  error: string | null
  version: number
}

export interface ShotAudioAsset extends ShotAsset {
  voice: string
  duration: number | null
}

export interface Shot {
  id: number
  order: number
  duration_estimate: number
  speaker_character_id: number | null
  ref_character_ids: number[]
  line_en: string
  line_zh: string
  image_prompt: string
  video_prompt: string
  image: ShotAsset
  video: ShotAsset
  audio: ShotAudioAsset
}

export interface ShotPatch {
  line_en?: string
  line_zh?: string
  speaker_character_id?: number | null
  ref_character_ids?: number[]
  image_prompt?: string
  video_prompt?: string
  duration_estimate?: number
}

export interface DefaultModels {
  llm: string
  t2i: string
  i2v: string
  tts: string
}

export interface ComposeInfo {
  state: ComposeState
  video_url: string | null
  error: string | null
  stale: boolean
}

export interface ProjectProgress {
  image: number
  video: number
  audio: number
}

export interface ProjectSummary {
  id: number
  title: string
  status: ProjectStatus
  cover_url: string | null
  duration_estimate: number
  shot_count: number
  progress: ProjectProgress
  updated_at: string
}

export interface ProjectListResponse {
  total: number
  items: ProjectSummary[]
}

export interface ProjectDetail {
  id: number
  title: string
  synopsis: string
  status: ProjectStatus
  target_duration: number
  characters: CharacterRef[]
  default_models: DefaultModels
  tts_voice: string
  script: Script | null
  compose: ComposeInfo
  shots: Shot[]
}

export interface CreateProjectPayload {
  title: string
  synopsis: string
  character_ids: number[]
  target_duration: number
  default_models?: Partial<DefaultModels>
  tts_voice?: string
}

export interface GenerateAllPayload {
  types: AssetKind[]
  scope: 'missing' | 'all'
}

export interface AssetStatusLite {
  state: AssetState
  stale: boolean
  url: string | null
  version: number
  error: string | null
}

export interface ShotStatus {
  id: number
  image: AssetStatusLite
  video: AssetStatusLite
  audio: AssetStatusLite & { duration: number | null }
}

export interface QueueStatus {
  pending: number
  running: number
  paused: boolean
  paused_reason: string | null
}

export interface ProgressDetail {
  done: number
  total: number
}

export interface ProjectStatusResponse {
  status: ProjectStatus
  queue: QueueStatus
  progress: Record<AssetKind, ProgressDetail>
  stale_count: number
  compose: ComposeInfo
  shots: ShotStatus[]
}

export interface StaleItem {
  shot_id: number
  shot_order: number
  kind: AssetKind
}

export interface MissingItem {
  shot_id: number
  shot_order: number
  kind: AssetKind
}
