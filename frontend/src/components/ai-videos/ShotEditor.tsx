import { useState } from 'react'
import {
  CircleAlert,
  Clapperboard,
  ImageIcon,
  Loader2,
  Play,
  RefreshCw,
  Timer,
  Trash2,
  Volume2,
} from 'lucide-react'
import type {
  AssetKind,
  CharacterRef,
  DialogueLine,
  ModelsMap,
  Shot,
  ShotPatch,
} from '../../types/aiVideos'
import { resolveAssetUrl } from '../../services/aiVideos'
import { StatusChip } from './StatusDot'
import ModelSelect from './ModelSelect'

interface ShotEditorProps {
  shot: Shot
  characters: CharacterRef[]
  models: ModelsMap
  defaultVoice: string
  onPatch: (patch: ShotPatch) => void
  onGenerate: (kind: AssetKind, model: string, voice?: string) => void
  onDelete: () => void
}

// 调用方须传 key={shot.id}，切镜时整体重挂载以重置编辑态
export default function ShotEditor({
  shot,
  characters,
  models,
  defaultVoice,
  onPatch,
  onGenerate,
  onDelete,
}: ShotEditorProps) {
  const MAX_DIALOGUE_LINES = 4
  const hasDialogue = shot.dialogue.length > 0
  const [dialogue, setDialogue] = useState<DialogueLine[]>(shot.dialogue)
  const [prompt, setPrompt] = useState(shot.image_prompt)
  const [imageModel, setImageModel] = useState(shot.image.model)
  const [videoModel, setVideoModel] = useState(shot.video.model)
  const [audioModel, setAudioModel] = useState(shot.audio?.model ?? '')
  const [voice, setVoice] = useState(shot.audio?.voice || defaultVoice)
  const [videoPrompt, setVideoPrompt] = useState(shot.video_prompt)

  const voices = (models.tts ?? []).find((m) => m.id === audioModel)?.voices ?? []
  const effectiveVoice = voices.includes(voice) ? voice : (voices[0] ?? defaultVoice)

  const toggleRefCharacter = (id: number) => {
    const next = shot.ref_character_ids.includes(id)
      ? shot.ref_character_ids.filter((x) => x !== id)
      : [...shot.ref_character_ids, id]
    onPatch({ ref_character_ids: next })
  }

  const commitDialogue = (next: DialogueLine[]) => {
    setDialogue(next)
    onPatch({ dialogue: next })
  }
  const updateLineField = (index: number, field: 'en' | 'zh', value: string) => {
    setDialogue((prev) => prev.map((ln, i) => (i === index ? { ...ln, [field]: value } : ln)))
  }
  const commitLineFieldIfChanged = (index: number, field: 'en' | 'zh') => {
    const original = shot.dialogue[index]?.[field] ?? ''
    if (dialogue[index]?.[field] !== original) onPatch({ dialogue })
  }
  const setLineSpeaker = (index: number, characterId: number | null) => {
    commitDialogue(
      dialogue.map((ln, i) => (i === index ? { ...ln, character_id: characterId } : ln)),
    )
  }
  const addDialogueLine = () => {
    if (dialogue.length >= MAX_DIALOGUE_LINES) return
    commitDialogue([...dialogue, { character_id: null, en: '', zh: '' }])
  }
  const removeDialogueLine = (index: number) => {
    commitDialogue(dialogue.filter((_, i) => i !== index))
  }

  const errors = (
    [
      ['image', '分镜图', shot.image.error],
      ['video', '视频', shot.video.error],
      ['audio', '配音', shot.audio?.error ?? null],
    ] as const
  ).filter(([, , e]) => !!e)

  const inputCls =
    'w-full px-3 py-2 bg-card border border-border rounded-[var(--radius-sm)] text-text-primary placeholder:text-text-muted focus:outline-none focus:ring-2 focus:ring-primary/30 focus:border-primary transition-colors'

  const productRows: Array<{
    kind: AssetKind
    label: string
    icon: typeof ImageIcon
    model: string
    setModel: (v: string) => void
    options: ModelsMap['t2i']
    canGenerate: boolean
    blockReason?: string
    readOnlyModel?: boolean
  }> = [
    {
      kind: 'image',
      label: '分镜图',
      icon: ImageIcon,
      model: imageModel,
      setModel: setImageModel,
      // 分镜图只能用带参考图的模型：none 档会丢角色一致性（后端同规则回退兜底）
      options: (models.t2i ?? []).filter((m) => m.reference === 'multi'),
      canGenerate: true,
    },
    {
      kind: 'video',
      label: '视频',
      icon: Clapperboard,
      model: videoModel,
      setModel: setVideoModel,
      options: models.i2v ?? [],
      canGenerate: shot.image.state === 'success',
      blockReason: '需先生成分镜图',
      readOnlyModel: hasDialogue,
    },
  ]
  if (shot.audio) {
    productRows.push({
      kind: 'audio',
      label: '配音',
      icon: Volume2,
      model: audioModel,
      setModel: setAudioModel,
      options: models.tts ?? [],
      canGenerate: true,
    })
  }

  return (
    <section className="flex-1 min-w-0 h-full overflow-y-auto">
      <div className="flex flex-col gap-4 p-6">
        <div className="flex items-center justify-between">
          <h2 className="text-base font-bold text-text-primary">镜 {shot.order}</h2>
          <div className="flex items-center gap-2.5">
            <span className="flex items-center gap-1 px-2.5 py-1 bg-page-alt rounded-full text-[11px] font-semibold text-text-muted">
              <Timer size={11} />
              {shot.duration_estimate.toFixed(1)}s
            </span>
            <button
              onClick={onDelete}
              aria-label="删除分镜"
              className="w-8 h-8 flex items-center justify-center rounded-[var(--radius-sm)] text-text-muted hover:text-error hover:bg-error-light transition-colors cursor-pointer"
            >
              <Trash2 size={15} />
            </button>
          </div>
        </div>

        {/* 台词（可多句，每句一个说话角色；空 = 纯画面镜） */}
        <div className="flex flex-col gap-1.5">
          <div className="flex items-center justify-between">
            <span className="text-[13px] font-semibold text-text-primary">台词</span>
            {dialogue.length < MAX_DIALOGUE_LINES && (
              <button
                type="button"
                onClick={addDialogueLine}
                className="text-[11px] font-semibold text-primary hover:text-primary-hover transition-colors cursor-pointer"
              >
                + 添加台词
              </button>
            )}
          </div>
          <div className="flex flex-col gap-2">
            {dialogue.length === 0 && (
              <p className="text-xs text-text-muted px-3 py-2">这是一个纯画面镜，没有台词</p>
            )}
            {dialogue.map((line, index) => (
              <div
                key={index}
                className="flex flex-col gap-1.5 p-3 bg-card border border-border rounded-[var(--radius-sm)]"
              >
                <div className="flex items-center justify-between gap-2">
                  <select
                    value={line.character_id ?? ''}
                    onChange={(e) =>
                      setLineSpeaker(index, e.target.value ? Number(e.target.value) : null)
                    }
                    aria-label={`第 ${index + 1} 句说话角色`}
                    className="h-7 px-2 text-xs bg-page border border-border rounded-[var(--radius-sm)] text-text-primary cursor-pointer focus:outline-none focus:ring-2 focus:ring-primary/30"
                  >
                    <option value="">旁白</option>
                    {characters.map((c) => (
                      <option key={c.id} value={c.id}>
                        {c.name}
                      </option>
                    ))}
                  </select>
                  <button
                    type="button"
                    onClick={() => removeDialogueLine(index)}
                    aria-label={`删除第 ${index + 1} 句台词`}
                    className="w-6 h-6 flex items-center justify-center rounded-[var(--radius-sm)] text-text-muted hover:text-error hover:bg-error-light transition-colors cursor-pointer"
                  >
                    <Trash2 size={13} />
                  </button>
                </div>
                <input
                  value={line.en}
                  onChange={(e) => updateLineField(index, 'en', e.target.value)}
                  onBlur={() => commitLineFieldIfChanged(index, 'en')}
                  placeholder="English line..."
                  aria-label={`第 ${index + 1} 句英文台词`}
                  className="w-full text-sm font-semibold text-text-primary bg-transparent focus:outline-none placeholder:text-text-muted placeholder:font-normal"
                />
                <input
                  value={line.zh}
                  onChange={(e) => updateLineField(index, 'zh', e.target.value)}
                  onBlur={() => commitLineFieldIfChanged(index, 'zh')}
                  placeholder="中文释义…"
                  aria-label={`第 ${index + 1} 句中文释义`}
                  className="w-full text-xs text-text-muted bg-transparent focus:outline-none placeholder:text-text-muted"
                />
              </div>
            ))}
          </div>
        </div>

        {/* 画面 Prompt */}
        <div className="flex flex-col gap-1.5">
          <div className="flex items-center justify-between">
            <label htmlFor="shot-prompt" className="text-[13px] font-semibold text-text-primary">
              画面 Prompt
            </label>
            <div className="flex items-center gap-1.5 flex-wrap justify-end">
              <span className="text-[11px] text-text-muted">出场角色</span>
              {characters.map((c) => {
                const selected = shot.ref_character_ids.includes(c.id)
                return (
                  <button
                    key={c.id}
                    type="button"
                    onClick={() => toggleRefCharacter(c.id)}
                    aria-pressed={selected}
                    aria-label={`出场角色 ${c.name}`}
                    className={`flex items-center gap-1 h-7 px-2 text-xs font-semibold rounded-full border transition-colors cursor-pointer focus:outline-none focus:ring-2 focus:ring-primary/30 ${
                      selected
                        ? 'bg-primary text-white border-primary'
                        : 'bg-card text-text-muted border-border hover:text-text-primary'
                    }`}
                  >
                    {c.cover_image_url && (
                      <img
                        src={resolveAssetUrl(c.cover_image_url)}
                        alt=""
                        className="w-4 h-4 rounded-full object-cover"
                      />
                    )}
                    {c.name}
                  </button>
                )
              })}
            </div>
          </div>
          <textarea
            id="shot-prompt"
            value={prompt}
            onChange={(e) => setPrompt(e.target.value)}
            onBlur={() => prompt !== shot.image_prompt && onPatch({ image_prompt: prompt })}
            rows={3}
            placeholder="Describe the scene in English..."
            className={`${inputCls} resize-none text-sm leading-relaxed`}
          />
        </div>

        {/* 视频动作 / 运镜 */}
        <div className="flex flex-col gap-1.5">
          <label htmlFor="shot-video-prompt" className="text-[13px] font-semibold text-text-primary">
            视频动作 / 运镜
          </label>
          <textarea
            id="shot-video-prompt"
            value={videoPrompt}
            onChange={(e) => setVideoPrompt(e.target.value)}
            onBlur={() => videoPrompt !== shot.video_prompt && onPatch({ video_prompt: videoPrompt })}
            rows={2}
            placeholder="Action + camera move, e.g. the fox waves, slow push-in..."
            className={`${inputCls} resize-none text-sm leading-relaxed`}
          />
        </div>

        {/* 产物 */}
        <span className="text-[13px] font-semibold text-text-primary">产物</span>
        <div className="flex flex-col gap-2.5 -mt-1.5">
          {productRows.map((row) => {
            const asset = shot[row.kind]
            if (!asset) return null
            const busy = asset.state === 'running'
            const Icon = row.icon
            const actionLabel = busy
              ? '生成中…'
              : asset.state === 'success' || asset.state === 'failed'
                ? '重新生成'
                : '生成'
            return (
              <div
                key={row.kind}
                className="flex items-center gap-3 px-3.5 py-3 bg-card border border-border rounded-[var(--radius-md)]"
              >
                <Icon size={16} className="text-text-primary shrink-0" />
                <span className="text-[13px] font-bold text-text-primary w-12 shrink-0">
                  {row.label}
                </span>
                <StatusChip state={asset.state} stale={asset.stale} />
                {row.kind === 'audio' && shot.audio?.duration != null && (
                  <span className="text-[11px] text-text-muted">{shot.audio.duration}s</span>
                )}
                <div className="flex-1" />
                {row.kind === 'audio' && voices.length > 0 && (
                  <select
                    value={effectiveVoice}
                    onChange={(e) => setVoice(e.target.value)}
                    aria-label="配音音色"
                    className="h-8 px-2 text-xs bg-card border border-border rounded-[var(--radius-sm)] text-text-primary cursor-pointer focus:outline-none focus:ring-2 focus:ring-primary/30"
                  >
                    {voices.map((v) => (
                      <option key={v} value={v}>
                        {v}
                      </option>
                    ))}
                  </select>
                )}
                {row.readOnlyModel ? (
                  <span className="h-8 px-2 flex items-center text-[11px] font-mono text-text-muted">
                    {shot.video.model || '（待生成，固定走对白镜路由）'}
                  </span>
                ) : (
                  <ModelSelect compact value={row.model} options={row.options} onChange={row.setModel} />
                )}
                <button
                  onClick={() =>
                    onGenerate(row.kind, row.model, row.kind === 'audio' ? effectiveVoice : undefined)
                  }
                  disabled={busy || !row.canGenerate}
                  title={!row.canGenerate ? row.blockReason : undefined}
                  className={`flex items-center gap-1.5 h-8 px-3 text-xs font-semibold rounded-[var(--radius-sm)] transition-colors cursor-pointer disabled:cursor-not-allowed ${
                    busy
                      ? 'bg-page-alt text-text-muted'
                      : asset.state === 'pending'
                        ? 'bg-primary text-white hover:bg-primary-hover disabled:opacity-50'
                        : 'bg-card border border-border text-text-primary hover:bg-page disabled:opacity-50'
                  }`}
                >
                  {busy ? (
                    <Loader2 size={12} className="animate-spin" />
                  ) : asset.state === 'pending' ? (
                    <Play size={12} />
                  ) : (
                    <RefreshCw size={12} />
                  )}
                  {actionLabel}
                </button>
              </div>
            )
          })}
        </div>

        {/* 错误信息 */}
        {errors.map(([kind, label, message]) => (
          <div
            key={kind}
            className="flex items-start gap-2 px-3.5 py-2.5 bg-error-light rounded-[var(--radius-sm)]"
          >
            <CircleAlert size={14} className="text-error shrink-0 mt-0.5" />
            <p className="text-xs text-error leading-relaxed">
              {label}生成失败：{message}
            </p>
          </div>
        ))}

        {/* 产物预览（图 / 音频；视频预览在右栏） */}
        {shot.image.url && (
          <div className="flex items-start gap-4">
            <img
              src={`${resolveAssetUrl(shot.image.url)}${shot.image.url.includes('?') ? '&' : '?'}v=${shot.image.version}`}
              alt={`镜 ${shot.order} 分镜图`}
              className="w-[140px] aspect-[9/16] object-cover rounded-[var(--radius-md)] border border-border"
            />
            {shot.audio?.url && shot.audio.state === 'success' && (
              <audio
                key={shot.audio.version}
                controls
                src={`${resolveAssetUrl(shot.audio.url)}${shot.audio.url.includes('?') ? '&' : '?'}v=${shot.audio.version}`}
                className="h-9 mt-1"
              >
                <track kind="captions" />
              </audio>
            )}
          </div>
        )}
      </div>
    </section>
  )
}
