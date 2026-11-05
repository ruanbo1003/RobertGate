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
  const [lineEn, setLineEn] = useState(shot.line_en)
  const [lineZh, setLineZh] = useState(shot.line_zh)
  const [prompt, setPrompt] = useState(shot.image_prompt)
  const [imageModel, setImageModel] = useState(shot.image.model)
  const [videoModel, setVideoModel] = useState(shot.video.model)
  const [audioModel, setAudioModel] = useState(shot.audio.model)
  const [voice, setVoice] = useState(shot.audio.voice || defaultVoice)
  const [videoPrompt, setVideoPrompt] = useState(shot.video_prompt)

  const voices = (models.tts ?? []).find((m) => m.id === audioModel)?.voices ?? []
  const effectiveVoice = voices.includes(voice) ? voice : (voices[0] ?? defaultVoice)

  const toggleRefCharacter = (id: number) => {
    const next = shot.ref_character_ids.includes(id)
      ? shot.ref_character_ids.filter((x) => x !== id)
      : [...shot.ref_character_ids, id]
    onPatch({ ref_character_ids: next })
  }
  const errors = (
    [
      ['image', '分镜图', shot.image.error],
      ['video', '视频', shot.video.error],
      ['audio', '配音', shot.audio.error],
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
  }> = [
    {
      kind: 'image',
      label: '分镜图',
      icon: ImageIcon,
      model: imageModel,
      setModel: setImageModel,
      options: models.t2i ?? [],
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
    },
    {
      kind: 'audio',
      label: '配音',
      icon: Volume2,
      model: audioModel,
      setModel: setAudioModel,
      options: models.tts ?? [],
      canGenerate: !!lineEn.trim(),
      blockReason: '需先填写台词',
    },
  ]

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

        {/* 台词 */}
        <div className="flex flex-col gap-1.5">
          <div className="flex items-center justify-between">
            <label htmlFor="shot-line-en" className="text-[13px] font-semibold text-text-primary">
              台词
            </label>
            <div className="flex items-center gap-1.5">
              <span className="text-[11px] text-text-muted">说话角色</span>
              <select
                value={shot.speaker_character_id ?? ''}
                onChange={(e) =>
                  onPatch({ speaker_character_id: e.target.value ? Number(e.target.value) : null })
                }
                aria-label="说话角色"
                className="h-7 px-2 text-xs bg-card border border-border rounded-[var(--radius-sm)] text-text-primary cursor-pointer focus:outline-none focus:ring-2 focus:ring-primary/30"
              >
                <option value="">无</option>
                {characters.map((c) => (
                  <option key={c.id} value={c.id}>
                    {c.name}
                  </option>
                ))}
              </select>
            </div>
          </div>
          <div className="flex flex-col gap-1.5 p-3 bg-card border border-border rounded-[var(--radius-sm)]">
            <input
              id="shot-line-en"
              value={lineEn}
              onChange={(e) => setLineEn(e.target.value)}
              onBlur={() => lineEn !== shot.line_en && onPatch({ line_en: lineEn })}
              placeholder="English line..."
              className="w-full text-base font-semibold text-text-primary bg-transparent focus:outline-none placeholder:text-text-muted placeholder:font-normal"
            />
            <input
              value={lineZh}
              onChange={(e) => setLineZh(e.target.value)}
              onBlur={() => lineZh !== shot.line_zh && onPatch({ line_zh: lineZh })}
              placeholder="中文释义…"
              aria-label="中文释义"
              className="w-full text-xs text-text-muted bg-transparent focus:outline-none placeholder:text-text-muted"
            />
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
                {row.kind === 'audio' && shot.audio.duration != null && (
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
                <ModelSelect compact value={row.model} options={row.options} onChange={row.setModel} />
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
            {shot.audio.url && shot.audio.state === 'success' && (
              <audio controls src={resolveAssetUrl(shot.audio.url)} className="h-9 mt-1">
                <track kind="captions" />
              </audio>
            )}
          </div>
        )}
      </div>
    </section>
  )
}
