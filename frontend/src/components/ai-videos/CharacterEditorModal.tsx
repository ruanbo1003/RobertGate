import { useMemo, useState } from 'react'
import { Check, Sparkles } from 'lucide-react'
import Modal from '../ui/Modal'
import ModelSelect from './ModelSelect'
import type { Character, ModelInfo } from '../../types/aiVideos'
import {
  createCharacter,
  generateCharacterImage,
  resolveAssetUrl,
  updateCharacter,
} from '../../services/aiVideos'

interface CharacterEditorModalProps {
  open: boolean
  character: Character | null // null = 新建
  t2iModels: ModelInfo[]
  onClose: () => void
  onSaved: () => void
}

// 调用方须在每次打开时用 key 重挂载（key 变化 = 重置表单状态）
export default function CharacterEditorModal({
  open,
  character,
  t2iModels,
  onClose,
  onSaved,
}: CharacterEditorModalProps) {
  const defaultModel = useMemo(
    () => t2iModels.find((m) => m.default)?.id ?? t2iModels[0]?.id ?? '',
    [t2iModels],
  )
  const [draft, setDraft] = useState<Character | null>(character)
  const [name, setName] = useState(character?.name ?? '')
  const [appearance, setAppearance] = useState(character?.appearance_prompt ?? '')
  const [personality, setPersonality] = useState(character?.personality ?? '')
  const [modelChoice, setModelChoice] = useState('')
  const [coverId, setCoverId] = useState<number | null>(null)
  const [generating, setGenerating] = useState(false)
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState('')
  const model = modelChoice || defaultModel

  const candidates = draft?.candidate_images ?? []
  const effectiveCoverId =
    coverId ?? candidates.find((c) => c.url === draft?.cover_image_url)?.id ?? null

  // 新建模式下先落库拿到 id，再生成设定图
  const ensureDraft = async (): Promise<Character | null> => {
    if (draft) return draft
    const res = await createCharacter({
      name: name.trim(),
      appearance_prompt: appearance.trim(),
      personality: personality.trim() || undefined,
    })
    if (res.code !== 0 || !res.data) {
      setError(res.message)
      return null
    }
    setDraft(res.data.character)
    return res.data.character
  }

  const handleGenerate = async () => {
    setError('')
    if (!name.trim() || !appearance.trim()) {
      setError('请先填写角色名称和外形描述')
      return
    }
    setGenerating(true)
    const target = await ensureDraft()
    if (!target) {
      setGenerating(false)
      return
    }
    const res = await generateCharacterImage(target.id, model, appearance.trim())
    if (res.code !== 0 || !res.data) {
      setError(res.message)
    } else {
      const image = res.data.image
      setDraft((prev) =>
        prev ? { ...prev, candidate_images: [...prev.candidate_images, image].slice(-8) } : prev,
      )
      setCoverId(image.id)
    }
    setGenerating(false)
  }

  const handleSave = async () => {
    setError('')
    if (!name.trim() || !appearance.trim()) {
      setError('请先填写角色名称和外形描述')
      return
    }
    setSaving(true)
    const target = await ensureDraft()
    if (!target) {
      setSaving(false)
      return
    }
    const res = await updateCharacter(target.id, {
      name: name.trim(),
      appearance_prompt: appearance.trim(),
      personality: personality.trim() || undefined,
      ...(effectiveCoverId != null ? { cover_image_id: effectiveCoverId } : {}),
    })
    setSaving(false)
    if (res.code !== 0) {
      setError(res.message)
      return
    }
    onSaved()
    onClose()
  }

  const inputCls =
    'w-full px-3 py-2.5 text-base bg-card border border-border rounded-[var(--radius-sm)] text-text-primary placeholder:text-text-muted focus:outline-none focus:ring-2 focus:ring-primary/30 focus:border-primary transition-colors'

  return (
    <Modal
      open={open}
      onClose={onClose}
      title={character ? '编辑角色' : '新建角色'}
      width={880}
      footer={
        <>
          <button
            onClick={onClose}
            className="h-10 px-4 text-sm font-semibold text-text-primary bg-card border border-border rounded-[var(--radius-sm)] hover:bg-page transition-colors cursor-pointer"
          >
            取消
          </button>
          <button
            onClick={handleSave}
            disabled={saving}
            className="h-10 px-5 text-sm font-semibold text-white bg-primary hover:bg-primary-hover rounded-[var(--radius-sm)] transition-colors cursor-pointer disabled:opacity-50 flex items-center gap-2"
          >
            {saving && (
              <span className="w-3.5 h-3.5 border-2 border-white/30 border-t-white rounded-full animate-spin" />
            )}
            保存角色
          </button>
        </>
      }
    >
      <div className="flex flex-col md:flex-row gap-6">
        <div className="flex flex-col gap-4 md:w-[340px] shrink-0">
          <div className="flex flex-col gap-1.5">
            <label htmlFor="char-name" className="text-[13px] font-semibold text-text-primary">
              角色名称 <span className="text-error">*</span>
            </label>
            <input
              id="char-name"
              value={name}
              onChange={(e) => setName(e.target.value)}
              placeholder="Momo"
              maxLength={50}
              className={inputCls}
            />
          </div>
          <div className="flex flex-col gap-1.5">
            <label htmlFor="char-appearance" className="text-[13px] font-semibold text-text-primary">
              外形描述（英文 Prompt）<span className="text-error">*</span>
            </label>
            <textarea
              id="char-appearance"
              value={appearance}
              onChange={(e) => setAppearance(e.target.value)}
              placeholder="A cute cartoon fox child, orange fur, big curious eyes..."
              rows={4}
              maxLength={1000}
              className={`${inputCls} resize-none leading-relaxed text-sm`}
            />
          </div>
          <div className="flex flex-col gap-1.5">
            <label htmlFor="char-personality" className="text-[13px] font-semibold text-text-primary">
              性格设定
            </label>
            <textarea
              id="char-personality"
              value={personality}
              onChange={(e) => setPersonality(e.target.value)}
              placeholder="好奇心旺盛，喜欢提问"
              rows={2}
              maxLength={500}
              className={`${inputCls} resize-none leading-relaxed text-sm`}
            />
          </div>
          <ModelSelect label="文生图模型" value={model} options={t2iModels} onChange={setModelChoice} />
          <button
            onClick={handleGenerate}
            disabled={generating}
            className="flex items-center justify-center gap-2 h-11 bg-primary hover:bg-primary-hover text-white text-sm font-semibold rounded-[var(--radius-sm)] transition-colors cursor-pointer disabled:opacity-60 disabled:cursor-not-allowed"
          >
            {generating ? (
              <span className="w-4 h-4 border-2 border-white/30 border-t-white rounded-full animate-spin" />
            ) : (
              <Sparkles size={15} />
            )}
            {generating ? '生成中…' : '生成设定图'}
          </button>
          {error && <p className="text-xs text-error">{error}</p>}
        </div>

        <div className="flex-1 flex flex-col gap-3 min-w-0">
          <p className="text-[13px] font-semibold text-text-primary">
            生成结果 · 点选一张作为设定图
          </p>
          {candidates.length === 0 ? (
            <div className="flex-1 min-h-[280px] flex flex-col items-center justify-center gap-2 bg-page rounded-[var(--radius-md)] border border-dashed border-border">
              <Sparkles size={22} className="text-text-muted/50" />
              <p className="text-xs text-text-muted">还没有生成结果，填写左侧信息后点「生成设定图」</p>
            </div>
          ) : (
            <div className="grid grid-cols-2 gap-3">
              {candidates.map((img) => {
                const selected = img.id === effectiveCoverId
                return (
                  <button
                    key={img.id}
                    onClick={() => setCoverId(img.id)}
                    aria-label={selected ? '当前设定图' : '设为设定图'}
                    className={`relative aspect-[9/16] rounded-[var(--radius-md)] overflow-hidden border-2 transition-colors cursor-pointer focus:outline-none focus:ring-2 focus:ring-primary/30 ${
                      selected ? 'border-primary' : 'border-border hover:border-primary/40'
                    }`}
                  >
                    <img
                      src={resolveAssetUrl(img.url)}
                      alt="候选设定图"
                      className="w-full h-full object-cover"
                    />
                    {selected && (
                      <span className="absolute top-2 left-2 w-6 h-6 flex items-center justify-center bg-primary rounded-full">
                        <Check size={13} className="text-white" />
                      </span>
                    )}
                  </button>
                )
              })}
            </div>
          )}
        </div>
      </div>
    </Modal>
  )
}
