import { useMemo, useState } from 'react'
import { ArrowLeft, ArrowRight, Check, RefreshCw } from 'lucide-react'
import Modal from '../ui/Modal'
import ModelSelect from './ModelSelect'
import type {
  Character,
  DefaultModels,
  ModelsMap,
  Script,
} from '../../types/aiVideos'
import {
  createProject,
  generateScript,
  resolveAssetUrl,
  splitShots,
  updateScript,
} from '../../services/aiVideos'

interface CreateWizardProps {
  open: boolean
  characters: Character[]
  models: ModelsMap
  onClose: () => void
  onDone: (projectId: number) => void
}

const STEPS = ['主题梗概', '角色与设置', '剧本确认']

function pickDefault(models: ModelsMap, type: keyof ModelsMap): string {
  const list = models[type] ?? []
  return list.find((m) => m.default)?.id ?? list[0]?.id ?? ''
}

export default function CreateWizard({
  open,
  characters,
  models,
  onClose,
  onDone,
}: CreateWizardProps) {
  const initialModels = useMemo<DefaultModels>(
    () => ({
      llm: pickDefault(models, 'llm'),
      t2i: pickDefault(models, 't2i'),
      i2v: pickDefault(models, 'i2v'),
      tts: pickDefault(models, 'tts'),
    }),
    [models],
  )

  const [step, setStep] = useState(0)
  const [title, setTitle] = useState('')
  const [synopsis, setSynopsis] = useState('')
  const [charIds, setCharIds] = useState<number[]>([])
  const [duration, setDuration] = useState(60)
  const [defaultModels, setDefaultModels] = useState<DefaultModels>(initialModels)
  const voices = models.tts?.find((m) => m.id === defaultModels.tts)?.voices ?? []
  const [voice, setVoice] = useState(voices[0] ?? 'alloy')
  const [projectId, setProjectId] = useState<number | null>(null)
  const [script, setScript] = useState<Script | null>(null)
  const [busy, setBusy] = useState(false)
  const [splitting, setSplitting] = useState(false)
  const [error, setError] = useState('')

  const reset = () => {
    setStep(0)
    setTitle('')
    setSynopsis('')
    setCharIds([])
    setDuration(60)
    setDefaultModels(initialModels)
    setProjectId(null)
    setScript(null)
    setError('')
  }

  const handleClose = () => {
    reset()
    onClose()
  }

  const toggleChar = (id: number) => {
    setCharIds((prev) =>
      prev.includes(id) ? prev.filter((x) => x !== id) : prev.length < 4 ? [...prev, id] : prev,
    )
  }

  const runGenerateScript = async (pid: number) => {
    setBusy(true)
    setError('')
    const res = await generateScript(pid, defaultModels.llm)
    setBusy(false)
    if (res.code !== 0 || !res.data) {
      setError(res.message)
      return
    }
    setScript(res.data.script)
  }

  const goNext = async () => {
    setError('')
    if (step === 0) {
      if (!title.trim() || !synopsis.trim()) {
        setError('请填写标题和故事梗概')
        return
      }
      setStep(1)
      return
    }
    if (step === 1) {
      if (charIds.length === 0) {
        setError('至少选择一个角色')
        return
      }
      setBusy(true)
      let pid = projectId
      if (pid == null) {
        const res = await createProject({
          title: title.trim(),
          synopsis: synopsis.trim(),
          character_ids: charIds,
          target_duration: duration,
          default_models: defaultModels,
          tts_voice: voice,
        })
        setBusy(false)
        if (res.code !== 0 || !res.data) {
          setError(res.message)
          return
        }
        pid = res.data.project.id
        setProjectId(pid)
      } else {
        setBusy(false)
      }
      setStep(2)
      if (!script) void runGenerateScript(pid)
    }
  }

  const handleConfirm = async () => {
    if (projectId == null || !script) return
    setSplitting(true)
    setError('')
    const saveRes = await updateScript(projectId, script)
    if (saveRes.code !== 0) {
      setSplitting(false)
      setError(saveRes.message)
      return
    }
    const res = await splitShots(projectId, defaultModels.llm, true)
    setSplitting(false)
    if (res.code !== 0) {
      setError(res.message)
      return
    }
    const pid = projectId
    reset()
    onDone(pid)
  }

  const updateLine = (si: number, li: number, patch: Partial<Script['scenes'][0]['lines'][0]>) => {
    setScript((prev) => {
      if (!prev) return prev
      const next: Script = JSON.parse(JSON.stringify(prev))
      Object.assign(next.scenes[si].lines[li], patch)
      return next
    })
  }

  const charName = (id: number) => characters.find((c) => c.id === id)?.name ?? '?'
  const inputCls =
    'w-full px-3 py-2.5 text-base bg-card border border-border rounded-[var(--radius-sm)] text-text-primary placeholder:text-text-muted focus:outline-none focus:ring-2 focus:ring-primary/30 focus:border-primary transition-colors'

  return (
    <Modal
      open={open}
      onClose={handleClose}
      title="新建视频"
      width={760}
      footer={
        <div className="flex items-center justify-between w-full">
          <button
            onClick={() => setStep((s) => Math.max(0, s - 1))}
            disabled={step === 0 || busy || splitting}
            className="flex items-center gap-1.5 h-10 px-4 text-sm font-semibold text-text-primary bg-card border border-border rounded-[var(--radius-sm)] hover:bg-page transition-colors cursor-pointer disabled:opacity-40 disabled:cursor-not-allowed"
          >
            <ArrowLeft size={14} />
            上一步
          </button>
          {step < 2 ? (
            <button
              onClick={goNext}
              disabled={busy}
              className="flex items-center gap-1.5 h-11 px-5 text-sm font-semibold text-white bg-primary hover:bg-primary-hover rounded-[var(--radius-sm)] transition-colors cursor-pointer disabled:opacity-60"
            >
              {busy && (
                <span className="w-3.5 h-3.5 border-2 border-white/30 border-t-white rounded-full animate-spin" />
              )}
              下一步
              <ArrowRight size={14} />
            </button>
          ) : (
            <button
              onClick={handleConfirm}
              disabled={busy || splitting || !script}
              className="flex items-center gap-1.5 h-11 px-5 text-sm font-semibold text-white bg-primary hover:bg-primary-hover rounded-[var(--radius-sm)] transition-colors cursor-pointer disabled:opacity-60"
            >
              {splitting && (
                <span className="w-3.5 h-3.5 border-2 border-white/30 border-t-white rounded-full animate-spin" />
              )}
              确认剧本，拆分镜进入工作台
              <ArrowRight size={14} />
            </button>
          )}
        </div>
      }
    >
      {/* 步骤条 */}
      <div className="flex items-center gap-2 mb-5">
        {STEPS.map((label, i) => (
          <div key={label} className="flex items-center gap-2">
            <div className="flex items-center gap-2">
              <span
                className={`w-6 h-6 flex items-center justify-center rounded-full text-xs font-bold ${
                  i < step
                    ? 'bg-success text-white'
                    : i === step
                      ? 'bg-primary text-white'
                      : 'bg-page-alt text-text-muted'
                }`}
              >
                {i < step ? <Check size={12} /> : i + 1}
              </span>
              <span
                className={`text-[13px] ${i === step ? 'font-bold text-text-primary' : 'font-medium text-text-muted'}`}
              >
                {label}
              </span>
            </div>
            {i < STEPS.length - 1 && <span className="w-10 h-px bg-border" />}
          </div>
        ))}
      </div>

      {step === 0 && (
        <div className="flex flex-col gap-4">
          <div className="flex flex-col gap-1.5">
            <label htmlFor="wz-title" className="text-[13px] font-semibold text-text-primary">
              标题 <span className="text-error">*</span>
            </label>
            <input
              id="wz-title"
              value={title}
              onChange={(e) => setTitle(e.target.value)}
              placeholder="EP05 · At the Zoo"
              maxLength={100}
              className={inputCls}
            />
          </div>
          <div className="flex flex-col gap-1.5">
            <label htmlFor="wz-synopsis" className="text-[13px] font-semibold text-text-primary">
              故事梗概 <span className="text-error">*</span>
            </label>
            <textarea
              id="wz-synopsis"
              value={synopsis}
              onChange={(e) => setSynopsis(e.target.value)}
              placeholder="Momo 和 Kuku 去动物园，认识各种动物，学习动物词汇…"
              rows={5}
              maxLength={1000}
              className={`${inputCls} resize-none leading-relaxed text-sm`}
            />
            <p className="text-xs text-text-muted">用中文描述剧情即可，AI 会生成英文对白剧本</p>
          </div>
        </div>
      )}

      {step === 1 && (
        <div className="flex flex-col gap-5">
          <div className="flex flex-col gap-2">
            <span className="text-[13px] font-semibold text-text-primary">
              出场角色（1-4 个）<span className="text-error">*</span>
            </span>
            {characters.length === 0 ? (
              <p className="text-sm text-text-muted">
                角色库还是空的，先去「角色库」创建角色再来新建视频
              </p>
            ) : (
              <div className="flex flex-wrap gap-2">
                {characters.map((c) => {
                  const selected = charIds.includes(c.id)
                  return (
                    <button
                      key={c.id}
                      onClick={() => toggleChar(c.id)}
                      aria-pressed={selected}
                      className={`flex items-center gap-2 pl-1.5 pr-3 py-1.5 rounded-full border-2 transition-colors cursor-pointer ${
                        selected
                          ? 'border-primary bg-primary-light/60'
                          : 'border-border bg-card hover:border-primary/40'
                      }`}
                    >
                      {c.cover_image_url ? (
                        <img
                          src={resolveAssetUrl(c.cover_image_url)}
                          alt=""
                          className="w-7 h-7 rounded-full object-cover"
                        />
                      ) : (
                        <span className="w-7 h-7 rounded-full bg-page-alt" />
                      )}
                      <span
                        className={`text-sm font-semibold ${selected ? 'text-primary' : 'text-text-primary'}`}
                      >
                        {c.name}
                      </span>
                      {selected && <Check size={13} className="text-primary" />}
                    </button>
                  )
                })}
              </div>
            )}
          </div>
          <div className="flex flex-col gap-1.5">
            <label htmlFor="wz-duration" className="text-[13px] font-semibold text-text-primary">
              目标时长：{duration}s
            </label>
            <input
              id="wz-duration"
              type="range"
              min={30}
              max={120}
              step={5}
              value={duration}
              onChange={(e) => setDuration(Number(e.target.value))}
              className="w-full accent-[var(--rg-color-primary)] cursor-pointer"
            />
            <div className="flex justify-between text-xs text-text-muted">
              <span>30s</span>
              <span>120s</span>
            </div>
          </div>
          <div className="grid grid-cols-2 gap-4">
            <ModelSelect
              label="剧本模型（LLM）"
              value={defaultModels.llm}
              options={models.llm ?? []}
              onChange={(id) => setDefaultModels((m) => ({ ...m, llm: id }))}
            />
            <ModelSelect
              label="文生图模型"
              value={defaultModels.t2i}
              options={models.t2i ?? []}
              onChange={(id) => setDefaultModels((m) => ({ ...m, t2i: id }))}
            />
            <ModelSelect
              label="图生视频模型"
              value={defaultModels.i2v}
              options={models.i2v ?? []}
              onChange={(id) => setDefaultModels((m) => ({ ...m, i2v: id }))}
            />
            <div className="flex flex-col gap-1.5">
              <label htmlFor="wz-voice" className="text-[13px] font-semibold text-text-primary">
                配音音色
              </label>
              <select
                id="wz-voice"
                value={voices.includes(voice) ? voice : (voices[0] ?? voice)}
                onChange={(e) => setVoice(e.target.value)}
                className="h-10 px-2.5 text-sm bg-card border border-border rounded-[var(--radius-sm)] text-text-primary cursor-pointer focus:outline-none focus:ring-2 focus:ring-primary/30 focus:border-primary"
              >
                {(voices.length > 0 ? voices : ['alloy']).map((v) => (
                  <option key={v} value={v}>
                    {v}
                  </option>
                ))}
              </select>
            </div>
          </div>
        </div>
      )}

      {step === 2 && (
        <div className="flex flex-col gap-3">
          <div className="flex items-center justify-between">
            <p className="text-xs text-text-muted">
              目标 {duration}s · 角色：{charIds.map(charName).join('、')} · 对白可直接编辑
            </p>
            <button
              onClick={() => projectId != null && runGenerateScript(projectId)}
              disabled={busy}
              className="flex items-center gap-1.5 h-8 px-3 text-xs font-semibold text-text-primary bg-card border border-border rounded-[var(--radius-sm)] hover:bg-page transition-colors cursor-pointer disabled:opacity-50"
            >
              <RefreshCw size={12} className={busy ? 'animate-spin' : ''} />
              重新生成
            </button>
          </div>
          {busy && !script ? (
            <div className="flex flex-col gap-3 p-4 bg-page rounded-[var(--radius-md)] border border-border">
              {[0, 1, 2, 3].map((i) => (
                <div key={i} className="flex gap-3 animate-pulse">
                  <div className="w-14 h-6 bg-page-alt rounded-full" />
                  <div className="flex-1 flex flex-col gap-1.5">
                    <div className="h-4 bg-page-alt rounded w-3/4" />
                    <div className="h-3 bg-page-alt rounded w-1/2" />
                  </div>
                </div>
              ))}
              <p className="text-xs text-text-muted text-center">AI 正在创作剧本…</p>
            </div>
          ) : script ? (
            <div className="flex flex-col gap-4 p-4 bg-page rounded-[var(--radius-md)] border border-border max-h-[380px] overflow-y-auto">
              {script.scenes.map((scene, si) => (
                <div key={si} className="flex flex-col gap-3">
                  <p className="text-xs italic text-text-muted">[Scene {si + 1} · {scene.setting}]</p>
                  {scene.lines.map((line, li) => (
                    <div key={li} className="flex gap-3 items-start">
                      <span className="shrink-0 w-16 py-1 text-center text-[11px] font-bold text-accent bg-accent-light rounded-full">
                        {charName(line.character_id)}
                      </span>
                      <div className="flex-1 flex flex-col gap-1 min-w-0">
                        <input
                          value={line.en}
                          onChange={(e) => updateLine(si, li, { en: e.target.value })}
                          aria-label={`第 ${li + 1} 句英文台词`}
                          className="w-full px-2 py-1 text-sm font-semibold text-text-primary bg-transparent border border-transparent hover:border-border focus:border-primary focus:bg-card rounded-[var(--radius-sm)] focus:outline-none transition-colors"
                        />
                        <input
                          value={line.zh}
                          onChange={(e) => updateLine(si, li, { zh: e.target.value })}
                          aria-label={`第 ${li + 1} 句中文释义`}
                          className="w-full px-2 py-0.5 text-xs text-text-muted bg-transparent border border-transparent hover:border-border focus:border-primary focus:bg-card rounded-[var(--radius-sm)] focus:outline-none transition-colors"
                        />
                      </div>
                    </div>
                  ))}
                </div>
              ))}
            </div>
          ) : null}
        </div>
      )}

      {error && <p className="mt-3 text-xs text-error">{error}</p>}
    </Modal>
  )
}
