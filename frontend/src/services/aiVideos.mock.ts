// AI Videos 内存 mock 后端。VITE_AI_VIDEOS_MOCK=true（默认）时启用。
// 模拟异步生成队列（并发 image:2 / video:1 / audio:2）、过期链、合成校验。

import type { ApiResponse } from '../types/auth'
import type {
  AssetKind,
  AssetState,
  Character,
  CharacterPayload,
  CreateProjectPayload,
  DialogueLine,
  GenerateAllPayload,
  ModelsMap,
  ProjectDetail,
  ProjectListResponse,
  ProjectStatus,
  ProjectStatusResponse,
  ProjectSummary,
  Script,
  Shot,
  ShotAsset,
  ShotAudioAsset,
  ShotPatch,
  StaleItem,
} from '../types/aiVideos'

/** 按产物类型取对应资产（audio 可能为 null）——统一出入口，避免到处写动态索引。 */
function assetOf(shot: Shot, kind: AssetKind): ShotAsset | ShotAudioAsset | null {
  if (kind === 'image') return shot.image
  if (kind === 'video') return shot.video
  return shot.audio
}

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
    { id: 'gemini-3-8-flash-openai', name: 'Gemini 3.8 Flash', default: true },
  ],
  t2i: [
    { id: 'nano-banana-2', name: 'Nano Banana 2', default: true, reference: 'multi' },
    { id: 'seedream/5-5-text-to-image', name: 'Seedream 5.5（省钱档）', reference: 'none' },
  ],
  i2v: [
    { id: 'bytedance/seedance-2-fast', name: 'Seedance 2 Fast', default: true },
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
  dialogue_video: [
    { id: 'kie:gemini-omni-video', name: 'Gemini Omni (kie.ai)', default: true },
    { id: 'openrouter:bytedance/seedance-2.0-fast', name: 'Seedance 2.0 Fast（兜底）' },
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
    voice_desc: '清脆活泼的小男孩声',
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
    voice_desc: '柔软羞涩的小女孩声',
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
    voice_desc: '温暖憨厚的大男孩声',
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

/** 镜像后端 estimate_dialogue_duration：按台词总词数估算时长，clamp 3-10s。 */
function estimateDialogueDuration(dialogue: DialogueLine[]): number {
  const words = dialogue.reduce((acc, d) => acc + d.en.split(' ').filter(Boolean).length, 0)
  return Math.round(Math.min(10, Math.max(3, words * 0.45 + 1.5)) * 10) / 10
}

function makeShot(
  order: number,
  dialogue: DialogueLine[],
  prompt: string,
  states: [AssetState, AssetState, AssetState],
): Shot {
  const [si, sv, sa] = states
  const hasDialogue = dialogue.length > 0
  const refIds = Array.from(
    new Set(dialogue.map((d) => d.character_id).filter((c): c is number => c != null)),
  )
  return {
    id: genId(),
    order,
    duration_estimate: hasDialogue ? estimateDialogueDuration(dialogue) : 5.0,
    ref_character_ids: refIds,
    image_prompt: prompt,
    video_prompt: '',
    dialogue,
    image: makeAsset(si, 'nano-banana-2', si === 'success' ? imgUrl('BFDBFE', '1E3A8A', `Shot ${order}`) : null),
    video: makeAsset(
      sv,
      hasDialogue ? 'kie:gemini-omni-video' : 'bytedance/seedance-2-fast',
      sv === 'success' ? SAMPLE_VIDEO : null,
    ),
    audio: hasDialogue
      ? null
      : {
          ...makeAsset(sa, 'openai/gpt-audio', sa === 'success' ? SAMPLE_AUDIO : null),
          voice: 'alloy',
          duration: null,
        },
  }
}

const DEFAULT_MODELS = {
  llm: 'gemini-3-8-flash-openai',
  t2i: 'nano-banana-2',
  i2v: 'bytedance/seedance-2-fast',
  tts: 'openai/gpt-audio',
}

// 同场景连续对答合并为一镜（镜像后端 group_script_into_shots）：镜 1 是双人对白镜。
const ep03Lines: Array<[DialogueLine[], string, [AssetState, AssetState, AssetState]]> = [
  [
    [
      { character_id: 1, en: 'Look, Kuku! A supermarket!', zh: '看，Kuku！一家超市！' },
      { character_id: 3, en: "Wow! Let's go inside!", zh: '哇！我们进去吧！' },
    ],
    'Momo the fox and Kuku the bear standing at a small supermarket entrance, children picture book style, soft lighting, vertical 9:16',
    ['success', 'success', 'success'],
  ],
  [
    [{ character_id: 1, en: 'I want to buy apples.', zh: '我想买苹果。' }],
    'Momo the fox pointing at a fruit stand, children picture book style, soft lighting, vertical 9:16',
    ['success', 'pending', 'pending'],
  ],
  [
    [{ character_id: 3, en: 'Apples are red and sweet!', zh: '苹果是红色的，甜甜的！' }],
    'Kuku the bear holding a red apple, children picture book style, soft lighting, vertical 9:16',
    ['success', 'failed', 'success'],
  ],
  [
    [{ character_id: 1, en: 'Where are the apples?', zh: '苹果在哪里呢？' }],
    'Momo the fox looking around the store, children picture book style, soft lighting, vertical 9:16',
    ['success', 'success', 'success'],
  ],
  [
    [{ character_id: 3, en: 'Over there! Follow me!', zh: '在那边！跟我来！' }],
    'Kuku the bear waving and walking ahead, children picture book style, soft lighting, vertical 9:16',
    ['pending', 'pending', 'pending'],
  ],
  // 纯画面镜（无台词）：示范"配音"产物行与空台词态
  [
    [],
    'Wide shot of the supermarket exterior at sunset, quiet establishing shot, children picture book style, vertical 9:16',
    ['pending', 'pending', 'pending'],
  ],
]

const ep03Shots = ep03Lines.map(([dialogue, prompt, states], i) =>
  makeShot(i + 1, dialogue, prompt, states),
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
      makeShot(
        1,
        [{ character_id: 1, en: 'Good morning, sun!', zh: '早上好，太阳！' }],
        'Momo the fox waking up at sunrise, children picture book style',
        ['success', 'success', 'success'],
      ),
      makeShot(
        2,
        [{ character_id: 1, en: 'Time to get up!', zh: '该起床啦！' }],
        'Momo the fox jumping out of bed, children picture book style',
        ['success', 'success', 'success'],
      ),
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
          lines: ep03Lines.flatMap(([dialogue]) =>
            dialogue.map((ln) => ({ ...ln, character_id: ln.character_id as number })),
          ),
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
  const asset = shot && assetOf(shot, task.kind)
  if (!shot || !project || !asset) return
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
      if (shot.dialogue.length > 0) asset.model = 'kie:gemini-omni-video'
    } else if (shot.audio) {
      asset.url = SAMPLE_AUDIO
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
    const asset = assetOf(shot, task.kind)
    if (!asset) {
      queue.splice(i, 1)
      i--
      continue
    }
    queue.splice(i, 1)
    i--
    running.push(task)
    asset.state = 'running'
    asset.error = null
    setTimeout(() => finishTask(task), 1800 + Math.random() * 2500)
  }
  if (queue.length === 0 && running.length === 0 && pumpTimer) {
    clearInterval(pumpTimer)
    pumpTimer = null
  }
}

function enqueue(projectId: number, shotId: number, kind: AssetKind) {
  const shot = findShot(projectId, shotId)
  const asset = shot && assetOf(shot, kind)
  if (!shot || !asset) return
  asset.state = 'pending'
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
  // audio 不参与聚合：对白镜没有独立音频产物（镜像后端 _AGGREGATE_KINDS）
  const assets = p.shots.flatMap((s) => [s.image, s.video])
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
      audio: p.shots.filter((s) => s.audio?.state === 'success').length,
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
      const asset = assetOf(s, kind)
      if (asset?.stale) items.push({ shot_id: s.id, shot_order: s.order, kind })
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
    voice_desc: payload.voice_desc ?? '',
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
  if (payload.voice_desc !== undefined) char.voice_desc = payload.voice_desc
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
  // 同场景连续对答合并为一镜（镜像后端 group_script_into_shots）：≤4 句且预估 ≤10s
  const MAX_LINES = 4
  const MAX_SECONDS = 10
  const shots: Shot[] = []
  let order = 1
  for (const scene of p.script.scenes) {
    let group: DialogueLine[] = []
    const flush = () => {
      if (group.length === 0) return
      const speakerNames = group
        .map((ln) => characters.find((c) => c.id === ln.character_id)?.appearance_prompt)
        .filter((v): v is string => !!v)
      shots.push(
        makeShot(
          order,
          group,
          `${speakerNames[0] ?? 'A cartoon character'}, ${scene.setting}, children picture book style, vertical 9:16`,
          ['pending', 'pending', 'pending'],
        ),
      )
      order += 1
      group = []
    }
    for (const line of scene.lines) {
      const candidate = [...group, line]
      if (group.length > 0 && (candidate.length > MAX_LINES || estimateDialogueDuration(candidate) > MAX_SECONDS)) {
        flush()
      }
      group.push(line)
    }
    flush()
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
  const shot = makeShot(0, [], '', ['pending', 'pending', 'pending'])
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
    (patch.video_prompt !== undefined && patch.video_prompt !== shot.video_prompt) ||
    (patch.dialogue !== undefined && JSON.stringify(patch.dialogue) !== JSON.stringify(shot.dialogue))
  Object.assign(shot, patch)
  if (patch.dialogue !== undefined) {
    // audio 是否存在随 dialogue 动态派生（镜像后端 has_dialogue）：
    // 台词从空变非空 → 退役为 null；从空台词变回空 → 重建可配音产物
    if (shot.dialogue.length > 0) {
      shot.audio = null
      shot.duration_estimate = estimateDialogueDuration(shot.dialogue)
      if (shot.video.model === 'bytedance/seedance-2-fast') shot.video.model = 'kie:gemini-omni-video'
    } else if (!shot.audio) {
      shot.audio = { ...makeAsset('pending', 'openai/gpt-audio', null), voice: 'alloy', duration: null }
      if (shot.video.model === 'kie:gemini-omni-video') shot.video.model = 'bytedance/seedance-2-fast'
    }
  }
  if (visualChanged) {
    if (shot.image.state === 'success') shot.image.stale = true
    if (shot.video.state === 'success') shot.video.stale = true
  }
  if (motionChanged && shot.video.state === 'success') shot.video.stale = true
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
  void voice
  const p = projects.find((x) => x.id === id)
  const shot = p?.shots.find((s) => s.id === shotId)
  if (!p || !shot) return delay(err(2007, '分镜不存在'))
  if (kind === 'audio') {
    // 对白镜无独立配音；纯画面镜没有台词可念——新 UI 不再提供 line_en 输入，
    // 此路径在真实系统里也恒不可达，两种情况都如实返回对应的后端错误码。
    return delay(
      shot.dialogue.length > 0
        ? err(2001, '对白镜无独立配音')
        : err(2003, '请先填写台词'),
    )
  }
  const asset = assetOf(shot, kind)
  if (!asset) return delay(err(2007, '产物不存在'))
  if (isBusy(asset.state, id, shotId, kind)) return delay(err(2006, '该产物正在生成中'))
  if (kind === 'video' && shot.image.state !== 'success') {
    return delay(err(2003, '请先生成分镜图'))
  }
  asset.model = model
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
      if (kind === 'audio' && shot.dialogue.length > 0) continue // 对白镜不排 audio
      const asset = assetOf(shot, kind)
      if (!asset) continue
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
  // audio 不参与合成预检：对白镜没有独立音频，纯画面镜未配音也不阻塞合成
  const missing = p.shots
    .filter((s) => s.video.state !== 'success')
    .map((s) => ({ shot_id: s.id, shot_order: s.order, kind: 'video' as AssetKind }))
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
      audio: { done: p.shots.filter((s) => s.audio?.state === 'success').length, total: p.shots.length },
    },
    stale_count: staleItems(p).length,
    compose: { ...p.compose },
    shots: p.shots.map((s) => ({
      id: s.id,
      image: { state: s.image.state, stale: s.image.stale, url: s.image.url, version: s.image.version, error: s.image.error },
      video: { state: s.video.state, stale: s.video.stale, url: s.video.url, version: s.video.version, error: s.video.error },
      audio: s.audio
        ? {
            state: s.audio.state,
            stale: s.audio.stale,
            url: s.audio.url,
            version: s.audio.version,
            error: s.audio.error,
            duration: s.audio.duration,
          }
        : null,
    })),
  }
  return delay(ok(resp), 120)
}
