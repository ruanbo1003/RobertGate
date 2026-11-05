// AI Videos 内存 mock 后端。VITE_AI_VIDEOS_MOCK=true（默认）时启用。
// 模拟异步生成队列（并发 image:2 / video:1 / audio:2）、过期链、合成校验。

import type { ApiResponse } from '../types/auth'
import type {
  AssetKind,
  AssetState,
  Character,
  CharacterPayload,
  CreateProjectPayload,
  GenerateAllPayload,
  ModelsMap,
  ProjectDetail,
  ProjectListResponse,
  ProjectStatus,
  ProjectStatusResponse,
  ProjectSummary,
  Script,
  Shot,
  ShotPatch,
  StaleItem,
} from '../types/aiVideos'

const nowIso = () => new Date().toISOString()

function ok<T>(data: T): ApiResponse<T> {
  return { code: 0, data, message: 'ok' }
}
function err(code: number, message: string, data: unknown = null): ApiResponse<never> {
  return { code, data: data as never, message }
}
function delay<T>(v: T, ms = 220): Promise<T> {
  return new Promise((r) => setTimeout(() => r(v), ms))
}

// ---------------- 模型 ----------------

const MODELS: ModelsMap = {
  llm: [
    { id: 'google/gemini-3.8-flash', name: 'Gemini 3.8 Flash', default: true },
    { id: 'deepseek/deepseek-v3.2', name: 'DeepSeek V3.2' },
  ],
  t2i: [
    { id: 'google/gemini-3.1-flash-image', name: 'Gemini 3.1 Flash Image', default: true, reference: 'multi' },
    { id: 'google/gemini-3-pro-image', name: 'Gemini 3 Pro Image', reference: 'multi' },
    { id: 'google/gemini-nano-banana-2.1', name: 'Nano Banana 2.1', reference: 'multi' },
  ],
  i2v: [
    { id: 'bytedance/seedance-2.0-fast', name: 'Seedance 2.0 Fast', default: true },
    { id: 'alibaba/wan-3.0', name: 'Wan 3.0' },
    { id: 'kwaivgi/kling-v3.0-std', name: 'Kling 3.0 Std' },
    { id: 'google/veo-3.1-fast', name: 'Veo 3.1 Fast' },
  ],
  tts: [
    {
      id: 'openai/gpt-audio',
      name: 'GPT Audio',
      default: true,
      voices: ['alloy', 'echo', 'fable', 'onyx', 'nova', 'shimmer'],
    },
    {
      id: 'openai/gpt-audio-mini',
      name: 'GPT Audio Mini',
      voices: ['alloy', 'echo', 'fable', 'onyx', 'nova', 'shimmer'],
    },
  ],
}

const SAMPLE_VIDEO = 'https://www.w3schools.com/html/mov_bbb.mp4'
const SAMPLE_AUDIO = 'https://interactive-examples.mdn.mozilla.net/media/cc0-audio/t-rex-roar.mp3'

function imgUrl(bg: string, fg: string, text: string, w = 540, h = 960): string {
  return `https://placehold.co/${w}x${h}/${bg}/${fg}.png?text=${encodeURIComponent(text)}`
}

// ---------------- 数据存储 ----------------

let nextId = 1000
const genId = () => ++nextId

const characters: Character[] = [
  {
    id: 1,
    name: 'Momo',
    appearance_prompt:
      'A cute cartoon fox child, orange fur, big curious eyes, wearing green overalls, children picture book style',
    personality: '好奇心旺盛，喜欢提问，说话节奏快',
    cover_image_url: imgUrl('FED7AA', '9A3412', 'Momo', 400, 500),
    candidate_images: [{ id: 11, url: imgUrl('FED7AA', '9A3412', 'Momo', 400, 500) }],
    used_count: 2,
    created_at: nowIso(),
    updated_at: nowIso(),
  },
  {
    id: 2,
    name: 'Bibi',
    appearance_prompt:
      'A cute shy cartoon bunny child, white fur, pink dress, children picture book style',
    personality: '害羞，说话慢而清晰',
    cover_image_url: imgUrl('BBF7D0', '14532D', 'Bibi', 400, 500),
    candidate_images: [{ id: 21, url: imgUrl('BBF7D0', '14532D', 'Bibi', 400, 500) }],
    used_count: 0,
    created_at: nowIso(),
    updated_at: nowIso(),
  },
  {
    id: 3,
    name: 'Kuku',
    appearance_prompt:
      'A cute clumsy cartoon bear child, brown fur, blue t-shirt, children picture book style',
    personality: '憨厚，Momo 的好朋友',
    cover_image_url: imgUrl('BFDBFE', '1E3A8A', 'Kuku', 400, 500),
    candidate_images: [{ id: 31, url: imgUrl('BFDBFE', '1E3A8A', 'Kuku', 400, 500) }],
    used_count: 2,
    created_at: nowIso(),
    updated_at: nowIso(),
  },
]

interface MockProject extends Omit<ProjectDetail, 'status' | 'characters'> {
  character_ids: number[]
  updated_at: string
}

function makeAsset(state: AssetState, model: string, url: string | null = null) {
  return { state, url, model, stale: false, error: null as string | null, version: state === 'success' ? 1 : 0 }
}

function makeShot(
  order: number,
  speaker: number,
  en: string,
  zh: string,
  prompt: string,
  states: [AssetState, AssetState, AssetState],
): Shot {
  const [si, sv, sa] = states
  return {
    id: genId(),
    order,
    duration_estimate: Math.min(6, Math.max(3, en.split(' ').length * 0.45 + 1.5)),
    speaker_character_id: speaker,
    ref_character_ids: speaker != null ? [speaker] : [],
    line_en: en,
    line_zh: zh,
    image_prompt: prompt,
    video_prompt: '',
    image: makeAsset(si, 'google/gemini-3.1-flash-image', si === 'success' ? imgUrl('BFDBFE', '1E3A8A', `Shot ${order}`) : null),
    video: makeAsset(sv, 'bytedance/seedance-2.0-fast', sv === 'success' ? SAMPLE_VIDEO : null),
    audio: {
      ...makeAsset(sa, 'openai/gpt-audio', sa === 'success' ? SAMPLE_AUDIO : null),
      voice: 'alloy',
      duration: sa === 'success' ? Math.round((en.split(' ').length * 0.45 + 1.2) * 10) / 10 : null,
    },
  }
}

const DEFAULT_MODELS = {
  llm: 'google/gemini-3.8-flash',
  t2i: 'google/gemini-3.1-flash-image',
  i2v: 'bytedance/seedance-2.0-fast',
  tts: 'openai/gpt-audio',
}

const ep03Lines: Array<[number, string, string, [AssetState, AssetState, AssetState]]> = [
  [1, 'Look, Kuku! A supermarket!', '看，Kuku！一家超市！', ['success', 'success', 'success']],
  [3, "Wow! Let's go inside!", '哇！我们进去吧！', ['success', 'success', 'success']],
  [1, 'I want to buy apples.', '我想买苹果。', ['success', 'pending', 'pending']],
  [3, 'Apples are red and sweet!', '苹果是红色的，甜甜的！', ['success', 'failed', 'success']],
  [1, 'Where are the apples?', '苹果在哪里呢？', ['success', 'success', 'success']],
  [3, 'Over there! Follow me!', '在那边！跟我来！', ['pending', 'pending', 'pending']],
]

const ep03Shots = ep03Lines.map(([speaker, en, zh, states], i) =>
  makeShot(
    i + 1,
    speaker,
    en,
    zh,
    `${speaker === 1 ? 'Momo the fox' : 'Kuku the bear'} in a small supermarket, ${en.toLowerCase()} children picture book style, soft lighting, vertical 9:16`,
    states,
  ),
)
ep03Shots[3].video.error = 'i2v task timeout (504)'
ep03Shots[4].image.stale = true
ep03Shots[4].video.stale = true

const projects: MockProject[] = [
  {
    id: 101,
    title: 'EP01 · Good Morning!',
    synopsis: 'Momo 早上起床，和家人问早安，学习打招呼用语',
    target_duration: 45,
    character_ids: [1],
    default_models: { ...DEFAULT_MODELS },
    tts_voice: 'alloy',
    script: {
      scenes: [
        {
          setting: 'In the bedroom at sunrise',
          lines: [
            { character_id: 1, en: 'Good morning, sun!', zh: '早上好，太阳！' },
            { character_id: 1, en: 'Time to get up!', zh: '该起床啦！' },
          ],
        },
      ],
    },
    compose: { state: 'success', video_url: SAMPLE_VIDEO, error: null, stale: false },
    shots: [
      makeShot(1, 1, 'Good morning, sun!', '早上好，太阳！', 'Momo the fox waking up at sunrise, children picture book style', ['success', 'success', 'success']),
      makeShot(2, 1, 'Time to get up!', '该起床啦！', 'Momo the fox jumping out of bed, children picture book style', ['success', 'success', 'success']),
    ],
    updated_at: nowIso(),
  },
  {
    id: 103,
    title: 'EP03 · At the Supermarket',
    synopsis: 'Momo 和 Kuku 去超市买苹果，学习水果和购物用语',
    target_duration: 90,
    character_ids: [1, 3],
    default_models: { ...DEFAULT_MODELS },
    tts_voice: 'alloy',
    script: {
      scenes: [
        {
          setting: 'At the supermarket entrance',
          lines: ep03Lines.map(([speaker, en, zh]) => ({ character_id: speaker, en, zh })),
        },
      ],
    },
    compose: { state: 'none', video_url: null, error: null, stale: false },
    shots: ep03Shots,
    updated_at: nowIso(),
  },
]

// ---------------- 任务队列模拟 ----------------

interface MockTask {
  projectId: number
  shotId: number
  kind: AssetKind
}

const queue: MockTask[] = []
const running: MockTask[] = []
const LIMITS: Record<AssetKind, number> = { image: 2, video: 1, audio: 2 }
let pumpTimer: ReturnType<typeof setInterval> | null = null

function findShot(projectId: number, shotId: number): Shot | undefined {
  return projects.find((p) => p.id === projectId)?.shots.find((s) => s.id === shotId)
}

function finishTask(task: MockTask) {
  const idx = running.indexOf(task)
  if (idx >= 0) running.splice(idx, 1)
  const shot = findShot(task.projectId, task.shotId)
  const project = projects.find((p) => p.id === task.projectId)
  if (!shot || !project) return
  const asset = shot[task.kind]
  // 约 1/8 概率失败，便于联调失败态
  const failed = Math.random() < 0.125
  if (failed) {
    asset.state = 'failed'
    asset.error =
      task.kind === 'video' ? 'i2v task timeout (504)' : 'SiliconFlow upstream error (503)'
  } else {
    asset.state = 'success'
    asset.error = null
    asset.stale = false
    asset.version += 1
    if (task.kind === 'image') {
      asset.url = imgUrl('BFDBFE', '1E3A8A', `Shot ${shot.order} v${asset.version}`)
    } else if (task.kind === 'video') {
      asset.url = SAMPLE_VIDEO
    } else {
      asset.url = SAMPLE_AUDIO
      shot.audio.duration = Math.round((shot.line_en.split(' ').length * 0.45 + 1.2) * 10) / 10
    }
    if (project.compose.state === 'success') project.compose.stale = true
  }
  project.updated_at = nowIso()
}

function pump() {
  for (let i = 0; i < queue.length; i++) {
    const task = queue[i]
    const runningOfKind = running.filter((t) => t.kind === task.kind).length
    if (runningOfKind >= LIMITS[task.kind]) continue
    const shot = findShot(task.projectId, task.shotId)
    if (!shot) {
      queue.splice(i, 1)
      i--
      continue
    }
    if (task.kind === 'video') {
      if (shot.image.state === 'failed') {
        shot.video.state = 'failed'
        shot.video.error = '前置分镜图失败'
        queue.splice(i, 1)
        i--
        continue
      }
      if (shot.image.state !== 'success') continue // 等待图完成
    }
    queue.splice(i, 1)
    i--
    running.push(task)
    shot[task.kind].state = 'running'
    shot[task.kind].error = null
    setTimeout(() => finishTask(task), 1800 + Math.random() * 2500)
  }
  if (queue.length === 0 && running.length === 0 && pumpTimer) {
    clearInterval(pumpTimer)
    pumpTimer = null
  }
}

function enqueue(projectId: number, shotId: number, kind: AssetKind) {
  const shot = findShot(projectId, shotId)
  if (!shot) return
  shot[kind].state = 'pending'
  queue.push({ projectId, shotId, kind })
  if (!pumpTimer) pumpTimer = setInterval(pump, 500)
}

function isBusy(state: AssetState, projectId: number, shotId: number, kind: AssetKind): boolean {
  return (
    state === 'running' ||
    queue.some((t) => t.projectId === projectId && t.shotId === shotId && t.kind === kind)
  )
}

// ---------------- 派生状态 ----------------

function deriveStatus(p: MockProject): ProjectStatus {
  if (p.shots.length === 0) return 'draft'
  const assets = p.shots.flatMap((s) => [s.image, s.video, s.audio])
  const queued = queue.some((t) => t.projectId === p.id)
  if (queued || assets.some((a) => a.state === 'running')) return 'generating'
  if (assets.some((a) => a.state === 'failed')) return 'partial_failed'
  if (assets.every((a) => a.state === 'success')) return 'completed'
  return 'draft'
}

function toSummary(p: MockProject): ProjectSummary {
  const firstImage = p.shots.find((s) => s.image.url)?.image.url ?? null
  return {
    id: p.id,
    title: p.title,
    status: deriveStatus(p),
    cover_url: firstImage,
    duration_estimate: Math.round(p.shots.reduce((acc, s) => acc + s.duration_estimate, 0)),
    shot_count: p.shots.length,
    progress: {
      image: p.shots.filter((s) => s.image.state === 'success').length,
      video: p.shots.filter((s) => s.video.state === 'success').length,
      audio: p.shots.filter((s) => s.audio.state === 'success').length,
    },
    updated_at: p.updated_at,
  }
}

function toDetail(p: MockProject): ProjectDetail {
  return {
    id: p.id,
    title: p.title,
    synopsis: p.synopsis,
    status: deriveStatus(p),
    target_duration: p.target_duration,
    characters: p.character_ids
      .map((id) => characters.find((c) => c.id === id))
      .filter((c): c is Character => !!c)
      .map((c) => ({ id: c.id, name: c.name, cover_image_url: c.cover_image_url })),
    default_models: { ...p.default_models },
    tts_voice: p.tts_voice,
    script: p.script ? JSON.parse(JSON.stringify(p.script)) : null,
    compose: { ...p.compose },
    shots: JSON.parse(JSON.stringify(p.shots)),
  }
}

function staleItems(p: MockProject): StaleItem[] {
  const items: StaleItem[] = []
  for (const s of p.shots) {
    for (const kind of ['image', 'video', 'audio'] as AssetKind[]) {
      if (s[kind].stale) items.push({ shot_id: s.id, shot_order: s.order, kind })
    }
  }
  return items
}

// ---------------- 模型 / 角色接口 ----------------

export function getModelsMock(): Promise<ApiResponse<{ models: ModelsMap }>> {
  return delay(ok({ models: MODELS }))
}

export function listCharactersMock(): Promise<ApiResponse<{ characters: Character[] }>> {
  return delay(ok({ characters: JSON.parse(JSON.stringify(characters)) }))
}

export function createCharacterMock(
  payload: CharacterPayload,
): Promise<ApiResponse<{ character: Character } | null>> {
  if (characters.some((c) => c.name === payload.name)) {
    return delay(err(2001, '角色名称已存在'))
  }
  const char: Character = {
    id: genId(),
    name: payload.name,
    appearance_prompt: payload.appearance_prompt,
    personality: payload.personality ?? null,
    cover_image_url: null,
    candidate_images: [],
    used_count: 0,
    created_at: nowIso(),
    updated_at: nowIso(),
  }
  characters.push(char)
  return delay(ok({ character: JSON.parse(JSON.stringify(char)) }))
}

export function updateCharacterMock(
  id: number,
  payload: Partial<CharacterPayload>,
): Promise<ApiResponse<{ character: Character } | null>> {
  const char = characters.find((c) => c.id === id)
  if (!char) return delay(err(2007, '角色不存在'))
  if (payload.name && payload.name !== char.name && characters.some((c) => c.name === payload.name)) {
    return delay(err(2001, '角色名称已存在'))
  }
  if (payload.name) char.name = payload.name
  if (payload.appearance_prompt !== undefined) char.appearance_prompt = payload.appearance_prompt
  if (payload.personality !== undefined) char.personality = payload.personality
  if (payload.cover_image_id !== undefined) {
    const img = char.candidate_images.find((i) => i.id === payload.cover_image_id)
    if (!img) return delay(err(2001, 'cover_image_id 不在候选集内'))
    char.cover_image_url = img.url
  }
  char.updated_at = nowIso()
  return delay(ok({ character: JSON.parse(JSON.stringify(char)) }))
}

export function deleteCharacterMock(id: number): Promise<ApiResponse<null>> {
  const char = characters.find((c) => c.id === id)
  if (!char) return delay(err(2007, '角色不存在'))
  const usedBy = projects
    .filter((p) => p.character_ids.includes(id))
    .map((p) => ({ project_id: p.id, title: p.title }))
  if (usedBy.length > 0) {
    return delay(err(2002, `角色已被 ${usedBy.length} 个视频引用，不能删除`, { used_by: usedBy }))
  }
  characters.splice(characters.indexOf(char), 1)
  return delay(ok(null))
}

const CHAR_COLORS: Array<[string, string]> = [
  ['FED7AA', '9A3412'],
  ['BBF7D0', '14532D'],
  ['BFDBFE', '1E3A8A'],
  ['FDE68A', '92400E'],
  ['E9D5FF', '6B21A8'],
]

export function generateCharacterImageMock(
  id: number,
  model: string,
  prompt?: string,
): Promise<ApiResponse<{ image: { id: number; url: string } } | null>> {
  void model
  void prompt
  const char = characters.find((c) => c.id === id)
  if (!char) return delay(err(2007, '角色不存在'))
  const [bg, fg] = CHAR_COLORS[Math.floor(Math.random() * CHAR_COLORS.length)]
  const image = {
    id: genId(),
    url: imgUrl(bg, fg, `${char.name} v${char.candidate_images.length + 1}`, 400, 500),
  }
  char.candidate_images.push(image)
  if (char.candidate_images.length > 8) char.candidate_images.shift()
  if (!char.cover_image_url) char.cover_image_url = image.url
  char.updated_at = nowIso()
  return delay(ok({ image }), 1600)
}

// ---------------- 项目接口 ----------------

export function listProjectsMock(
  page = 1,
  pageSize = 20,
): Promise<ApiResponse<ProjectListResponse>> {
  const sorted = [...projects].sort((a, b) => b.updated_at.localeCompare(a.updated_at))
  const items = sorted.slice((page - 1) * pageSize, page * pageSize).map(toSummary)
  return delay(ok({ total: projects.length, items }))
}

export function createProjectMock(
  payload: CreateProjectPayload,
): Promise<ApiResponse<{ project: ProjectDetail } | null>> {
  const invalid = payload.character_ids.filter((id) => !characters.some((c) => c.id === id))
  if (invalid.length > 0) return delay(err(2001, '包含不存在的角色'))
  const project: MockProject = {
    id: genId(),
    title: payload.title,
    synopsis: payload.synopsis,
    target_duration: payload.target_duration,
    character_ids: payload.character_ids,
    default_models: { ...DEFAULT_MODELS, ...(payload.default_models ?? {}) },
    tts_voice: payload.tts_voice ?? 'alloy',
    script: null,
    compose: { state: 'none', video_url: null, error: null, stale: false },
    shots: [],
    updated_at: nowIso(),
  }
  projects.push(project)
  for (const cid of payload.character_ids) {
    const c = characters.find((ch) => ch.id === cid)
    if (c) c.used_count += 1
  }
  return delay(ok({ project: toDetail(project) }))
}

export function getProjectMock(id: number): Promise<ApiResponse<{ project: ProjectDetail } | null>> {
  const p = projects.find((x) => x.id === id)
  if (!p) return delay(err(2007, '项目不存在'))
  return delay(ok({ project: toDetail(p) }))
}

export function deleteProjectMock(id: number): Promise<ApiResponse<null>> {
  const idx = projects.findIndex((x) => x.id === id)
  if (idx < 0) return delay(err(2007, '项目不存在'))
  for (const cid of projects[idx].character_ids) {
    const c = characters.find((ch) => ch.id === cid)
    if (c && c.used_count > 0) c.used_count -= 1
  }
  for (let i = queue.length - 1; i >= 0; i--) {
    if (queue[i].projectId === id) queue.splice(i, 1)
  }
  projects.splice(idx, 1)
  return delay(ok(null))
}

// ---------------- 剧本 / 分镜 ----------------

export function generateScriptMock(
  id: number,
  model: string,
): Promise<ApiResponse<{ script: Script } | null>> {
  void model
  const p = projects.find((x) => x.id === id)
  if (!p) return delay(err(2007, '项目不存在'))
  const chars = p.character_ids
    .map((cid) => characters.find((c) => c.id === cid))
    .filter((c): c is Character => !!c)
  const a = chars[0]
  const b = chars[1] ?? chars[0]
  const script: Script = {
    scenes: [
      {
        setting: `About: ${p.synopsis.slice(0, 30)}`,
        lines: [
          { character_id: a.id, en: `Hi ${b.name}! What a nice day!`, zh: `嗨 ${b.name}！天气真好！` },
          { character_id: b.id, en: "Yes! Let's play together!", zh: '是呀！我们一起玩吧！' },
          { character_id: a.id, en: 'Look at this! So cool!', zh: '看这个！好酷！' },
          { character_id: b.id, en: 'Wow, I like it!', zh: '哇，我喜欢！' },
          { character_id: a.id, en: 'Do you want to try?', zh: '你想试试吗？' },
          { character_id: b.id, en: 'Yes, please!', zh: '好的，请让我试试！' },
        ],
      },
    ],
  }
  p.script = script
  p.updated_at = nowIso()
  return delay(ok({ script: JSON.parse(JSON.stringify(script)) }), 1800)
}

export function updateScriptMock(
  id: number,
  script: Script,
): Promise<ApiResponse<{ shots_exist: boolean } | null>> {
  const p = projects.find((x) => x.id === id)
  if (!p) return delay(err(2007, '项目不存在'))
  p.script = JSON.parse(JSON.stringify(script))
  p.updated_at = nowIso()
  return delay(ok({ shots_exist: p.shots.length > 0 }))
}

export function splitShotsMock(
  id: number,
  model: string,
  confirmReplace: boolean,
): Promise<ApiResponse<{ shots: Shot[] } | null>> {
  void model
  const p = projects.find((x) => x.id === id)
  if (!p) return delay(err(2007, '项目不存在'))
  if (!p.script || p.script.scenes.length === 0) return delay(err(2003, '请先生成剧本'))
  if (p.shots.length > 0 && !confirmReplace) {
    return delay(err(2005, '已存在分镜，重拆将删除全部产物', { existing_shot_count: p.shots.length }))
  }
  for (let i = queue.length - 1; i >= 0; i--) {
    if (queue[i].projectId === id) queue.splice(i, 1)
  }
  const shots: Shot[] = []
  let order = 1
  for (const scene of p.script.scenes) {
    for (const line of scene.lines) {
      const char = characters.find((c) => c.id === line.character_id)
      shots.push(
        makeShot(
          order,
          line.character_id,
          line.en,
          line.zh,
          `${char?.appearance_prompt ?? 'A cartoon character'}, ${scene.setting}, ${line.en.toLowerCase()} children picture book style, vertical 9:16`,
          ['pending', 'pending', 'pending'],
        ),
      )
      order += 1
    }
  }
  p.shots = shots
  p.compose = { state: 'none', video_url: null, error: null, stale: false }
  p.updated_at = nowIso()
  return delay(ok({ shots: JSON.parse(JSON.stringify(shots)) }), 1500)
}

export function createShotMock(
  id: number,
  afterShotId: number | null,
): Promise<ApiResponse<{ shot: Shot } | null>> {
  const p = projects.find((x) => x.id === id)
  if (!p) return delay(err(2007, '项目不存在'))
  const shot = makeShot(0, p.character_ids[0], '', '', '', ['pending', 'pending', 'pending'])
  const idx = afterShotId == null ? 0 : p.shots.findIndex((s) => s.id === afterShotId) + 1
  p.shots.splice(idx, 0, shot)
  p.shots.forEach((s, i) => (s.order = i + 1))
  p.updated_at = nowIso()
  return delay(ok({ shot: JSON.parse(JSON.stringify(shot)) }))
}

export function updateShotMock(
  id: number,
  shotId: number,
  patch: ShotPatch,
): Promise<ApiResponse<{ shot: Shot } | null>> {
  const p = projects.find((x) => x.id === id)
  const shot = p?.shots.find((s) => s.id === shotId)
  if (!p || !shot) return delay(err(2007, '分镜不存在'))
  const visualChanged =
    (patch.image_prompt !== undefined && patch.image_prompt !== shot.image_prompt) ||
    (patch.ref_character_ids !== undefined &&
      JSON.stringify(patch.ref_character_ids) !== JSON.stringify(shot.ref_character_ids))
  const motionChanged =
    patch.video_prompt !== undefined && patch.video_prompt !== shot.video_prompt
  const lineChanged =
    (patch.line_en !== undefined && patch.line_en !== shot.line_en) ||
    (patch.speaker_character_id !== undefined &&
      patch.speaker_character_id !== shot.speaker_character_id)
  Object.assign(shot, patch)
  if (visualChanged) {
    if (shot.image.state === 'success') shot.image.stale = true
    if (shot.video.state === 'success') shot.video.stale = true
  }
  if (motionChanged && shot.video.state === 'success') shot.video.stale = true
  if (lineChanged && shot.audio.state === 'success') shot.audio.stale = true
  p.updated_at = nowIso()
  return delay(ok({ shot: JSON.parse(JSON.stringify(shot)) }))
}

export function deleteShotMock(id: number, shotId: number): Promise<ApiResponse<null>> {
  const p = projects.find((x) => x.id === id)
  if (!p) return delay(err(2007, '项目不存在'))
  const idx = p.shots.findIndex((s) => s.id === shotId)
  if (idx < 0) return delay(err(2007, '分镜不存在'))
  p.shots.splice(idx, 1)
  p.shots.forEach((s, i) => (s.order = i + 1))
  if (p.compose.state === 'success') p.compose.stale = true
  p.updated_at = nowIso()
  return delay(ok(null))
}

export function reorderShotsMock(id: number, shotIds: number[]): Promise<ApiResponse<null>> {
  const p = projects.find((x) => x.id === id)
  if (!p) return delay(err(2007, '项目不存在'))
  const current = p.shots.map((s) => s.id).sort((a, b) => a - b)
  const given = [...shotIds].sort((a, b) => a - b)
  if (current.length !== given.length || current.some((v, i) => v !== given[i])) {
    return delay(err(2001, 'shot_ids 必须恰好覆盖全部分镜'))
  }
  p.shots.sort((a, b) => shotIds.indexOf(a.id) - shotIds.indexOf(b.id))
  p.shots.forEach((s, i) => (s.order = i + 1))
  if (p.compose.state === 'success') p.compose.stale = true
  p.updated_at = nowIso()
  return delay(ok(null))
}

// ---------------- 生成 / 合成 ----------------

export function generateAssetMock(
  id: number,
  shotId: number,
  kind: AssetKind,
  model: string,
  voice?: string,
): Promise<ApiResponse<null>> {
  const p = projects.find((x) => x.id === id)
  const shot = p?.shots.find((s) => s.id === shotId)
  if (!p || !shot) return delay(err(2007, '分镜不存在'))
  if (isBusy(shot[kind].state, id, shotId, kind)) return delay(err(2006, '该产物正在生成中'))
  if (kind === 'video' && shot.image.state !== 'success') {
    return delay(err(2003, '请先生成分镜图'))
  }
  shot[kind].model = model
  if (kind === 'audio' && voice) shot.audio.voice = voice
  enqueue(id, shotId, kind)
  return delay(ok(null))
}

export function generateAllMock(
  id: number,
  payload: GenerateAllPayload,
): Promise<ApiResponse<{ enqueued: Record<AssetKind, number> } | null>> {
  const p = projects.find((x) => x.id === id)
  if (!p) return delay(err(2007, '项目不存在'))
  const enqueued: Record<AssetKind, number> = { image: 0, video: 0, audio: 0 }
  for (const shot of p.shots) {
    for (const kind of payload.types) {
      const asset = shot[kind]
      if (isBusy(asset.state, id, shot.id, kind)) continue
      const needs =
        payload.scope === 'all' ||
        asset.state === 'pending' ||
        asset.state === 'failed' ||
        asset.stale
      if (!needs) continue
      enqueue(id, shot.id, kind)
      enqueued[kind] += 1
    }
  }
  p.updated_at = nowIso()
  return delay(ok({ enqueued }))
}

export function cancelQueueMock(id: number): Promise<ApiResponse<null>> {
  for (let i = queue.length - 1; i >= 0; i--) {
    if (queue[i].projectId === id) queue.splice(i, 1)
  }
  return delay(ok(null))
}

export function composeMock(
  id: number,
  ignoreStale: boolean,
): Promise<ApiResponse<null>> {
  const p = projects.find((x) => x.id === id)
  if (!p) return delay(err(2007, '项目不存在'))
  if (p.shots.length === 0) return delay(err(2003, '还没有分镜'))
  const missing = p.shots
    .flatMap((s) =>
      (['video', 'audio'] as AssetKind[])
        .filter((k) => s[k].state !== 'success')
        .map((k) => ({ shot_id: s.id, shot_order: s.order, kind: k })),
    )
  if (missing.length > 0) {
    return delay(err(2003, `还有 ${missing.length} 项产物未就绪`, { missing }))
  }
  const stale = staleItems(p)
  if (stale.length > 0 && !ignoreStale) {
    return delay(err(2004, `存在 ${stale.length} 项过期产物`, { stale_items: stale }))
  }
  p.compose = { state: 'running', video_url: null, error: null, stale: false }
  p.updated_at = nowIso()
  setTimeout(() => {
    p.compose = { state: 'success', video_url: SAMPLE_VIDEO, error: null, stale: false }
    p.updated_at = nowIso()
  }, 3200)
  return delay(ok(null))
}

export function getStatusMock(id: number): Promise<ApiResponse<ProjectStatusResponse | null>> {
  const p = projects.find((x) => x.id === id)
  if (!p) return delay(err(2007, '项目不存在'))
  const myQueue = queue.filter((t) => t.projectId === id)
  const myRunning = running.filter((t) => t.projectId === id)
  const resp: ProjectStatusResponse = {
    status: deriveStatus(p),
    queue: {
      pending: myQueue.length,
      running: myRunning.length,
      paused: false,
      paused_reason: null,
    },
    progress: {
      image: { done: p.shots.filter((s) => s.image.state === 'success').length, total: p.shots.length },
      video: { done: p.shots.filter((s) => s.video.state === 'success').length, total: p.shots.length },
      audio: { done: p.shots.filter((s) => s.audio.state === 'success').length, total: p.shots.length },
    },
    stale_count: staleItems(p).length,
    compose: { ...p.compose },
    shots: p.shots.map((s) => ({
      id: s.id,
      image: { state: s.image.state, stale: s.image.stale, url: s.image.url, version: s.image.version, error: s.image.error },
      video: { state: s.video.state, stale: s.video.stale, url: s.video.url, version: s.video.version, error: s.video.error },
      audio: {
        state: s.audio.state,
        stale: s.audio.stale,
        url: s.audio.url,
        version: s.audio.version,
        error: s.audio.error,
        duration: s.audio.duration,
      },
    })),
  }
  return delay(ok(resp), 120)
}
