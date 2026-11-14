import { useState } from 'react'
import { AnimatePresence, motion } from 'framer-motion'
import { Scissors, Sparkles, X } from 'lucide-react'
import type { CharacterRef, Script } from '../../types/aiVideos'

interface ScriptDrawerProps {
  open: boolean
  script: Script | null
  characters: CharacterRef[]
  saving: boolean
  /** 项目当前故事梗概（生成剧本的输入） */
  synopsis: string
  /** 剧本生成请求进行中 */
  generating: boolean
  /** 生成失败的错误文案（就近显示，可重试） */
  generateError: string
  /** 生成成功后父组件递增，用于重挂载抽屉主体刷新草稿 */
  scriptVersion: number
  onClose: () => void
  onSave: (script: Script) => void
  onResplit: (script: Script) => void
  onGenerate: (synopsis: string) => void
}

interface DrawerBodyProps extends Omit<ScriptDrawerProps, 'open' | 'scriptVersion'> {
  onClose: () => void
}

// 随抽屉打开而挂载，草稿状态在挂载时从 props 初始化；
// 生成成功后由父组件递增 scriptVersion（key）触发重挂载刷新草稿
function DrawerBody({
  script,
  characters,
  saving,
  synopsis,
  generating,
  generateError,
  onClose,
  onSave,
  onResplit,
  onGenerate,
}: DrawerBodyProps) {
  const [draft, setDraft] = useState<Script | null>(
    script ? (JSON.parse(JSON.stringify(script)) as Script) : null,
  )
  const [dirty, setDirty] = useState(false)
  const [synopsisDraft, setSynopsisDraft] = useState(synopsis)
  const [confirmRegen, setConfirmRegen] = useState(false)

  const hasScript = !!draft && draft.scenes.length > 0

  const handleGenerateClick = () => {
    if (!synopsisDraft.trim() || generating) return
    if (hasScript) {
      setConfirmRegen(true)
      return
    }
    onGenerate(synopsisDraft.trim())
  }

  const charName = (id: number) => characters.find((c) => c.id === id)?.name ?? '?'

  const updateLine = (si: number, li: number, field: 'en' | 'zh', value: string) => {
    setDraft((prev) => {
      if (!prev) return prev
      const next: Script = JSON.parse(JSON.stringify(prev))
      next.scenes[si].lines[li][field] = value
      return next
    })
    setDirty(true)
  }

  return (
    <motion.div
      initial={{ x: 480 }}
      animate={{ x: 0 }}
      exit={{ x: 480 }}
      transition={{ duration: 0.2, ease: 'easeOut' }}
      onClick={(e) => e.stopPropagation()}
      className="absolute right-0 top-0 h-full w-[480px] max-w-full bg-card border-l border-border shadow-lg flex flex-col"
    >
      <div className="flex items-center justify-between px-5 py-4 border-b border-border shrink-0">
        <h3 className="text-base font-bold text-text-primary">剧本</h3>
        <button
          onClick={onClose}
          aria-label="关闭剧本"
          className="w-8 h-8 flex items-center justify-center rounded-[var(--radius-sm)] text-text-muted hover:text-text-primary hover:bg-page transition-colors cursor-pointer"
        >
          <X size={16} />
        </button>
      </div>
      <div className="shrink-0 px-5 pt-4 pb-3 border-b border-border flex flex-col gap-2">
        <label htmlFor="drawer-synopsis" className="text-[13px] font-semibold text-text-primary">
          故事梗概
        </label>
        <textarea
          id="drawer-synopsis"
          value={synopsisDraft}
          onChange={(e) => setSynopsisDraft(e.target.value)}
          maxLength={1000}
          rows={3}
          disabled={generating}
          placeholder="描述这集视频讲什么故事…"
          className="w-full px-3 py-2 text-sm text-text-primary bg-card border border-border rounded-[var(--radius-sm)] focus:outline-none focus:border-primary resize-y disabled:opacity-50 transition-colors"
        />
        {confirmRegen ? (
          <div className="flex items-center gap-2.5">
            <p className="flex-1 text-xs text-text-muted">重新生成会覆盖当前剧本文本（已拆的分镜不受影响）</p>
            <button
              onClick={() => setConfirmRegen(false)}
              className="h-8 px-3 text-xs font-semibold text-text-primary bg-card border border-border rounded-[var(--radius-sm)] hover:bg-page transition-colors cursor-pointer"
            >
              取消
            </button>
            <button
              onClick={() => {
                setConfirmRegen(false)
                onGenerate(synopsisDraft.trim())
              }}
              className="h-8 px-3 text-xs font-semibold text-white bg-accent rounded-[var(--radius-sm)] hover:opacity-90 transition-opacity cursor-pointer"
            >
              覆盖生成
            </button>
          </div>
        ) : (
          <button
            onClick={handleGenerateClick}
            disabled={!synopsisDraft.trim() || generating || saving}
            className="self-start flex items-center gap-1.5 h-9 px-4 text-sm font-semibold text-white bg-primary hover:bg-primary-hover rounded-[var(--radius-sm)] transition-colors cursor-pointer disabled:opacity-50"
          >
            {generating ? (
              <span className="w-3.5 h-3.5 border-2 border-white/30 border-t-white rounded-full animate-spin" />
            ) : (
              <Sparkles size={13} />
            )}
            {generating ? '生成中…' : hasScript ? '重新生成剧本' : '生成剧本'}
          </button>
        )}
        {generateError && (
          <p role="alert" className="text-xs text-error">
            {generateError}
          </p>
        )}
      </div>
      <div className="flex-1 overflow-y-auto p-5">
        {!draft || draft.scenes.length === 0 ? (
          <p className="text-sm text-text-muted">
            还没有剧本 —— 确认上方梗概后点「生成剧本」。
          </p>
        ) : (
          <div className="flex flex-col gap-5">
            {draft.scenes.map((scene, si) => (
              <div key={si} className="flex flex-col gap-3">
                <p className="text-xs italic text-text-muted">
                  [Scene {si + 1} · {scene.setting}]
                </p>
                {scene.lines.map((line, li) => (
                  <div key={li} className="flex gap-3 items-start">
                    <span className="shrink-0 w-14 py-1 text-center text-[11px] font-bold text-accent bg-accent-light rounded-full">
                      {charName(line.character_id)}
                    </span>
                    <div className="flex-1 flex flex-col gap-1 min-w-0">
                      <input
                        value={line.en}
                        onChange={(e) => updateLine(si, li, 'en', e.target.value)}
                        aria-label="英文台词"
                        className="w-full px-2 py-1 text-sm font-semibold text-text-primary bg-transparent border border-transparent hover:border-border focus:border-primary focus:bg-card rounded-[var(--radius-sm)] focus:outline-none transition-colors"
                      />
                      <input
                        value={line.zh}
                        onChange={(e) => updateLine(si, li, 'zh', e.target.value)}
                        aria-label="中文释义"
                        className="w-full px-2 py-0.5 text-xs text-text-muted bg-transparent border border-transparent hover:border-border focus:border-primary focus:bg-card rounded-[var(--radius-sm)] focus:outline-none transition-colors"
                      />
                    </div>
                  </div>
                ))}
              </div>
            ))}
          </div>
        )}
      </div>
      <div className="flex items-center justify-end gap-2.5 px-5 py-4 border-t border-border shrink-0">
        <button
          onClick={() => draft && onResplit(draft)}
          disabled={!draft || saving || generating}
          className="flex items-center gap-1.5 h-10 px-4 text-sm font-semibold text-text-primary bg-card border border-border rounded-[var(--radius-sm)] hover:bg-page transition-colors cursor-pointer disabled:opacity-50"
        >
          <Scissors size={13} />
          重新拆分镜
        </button>
        <button
          onClick={() => draft && onSave(draft)}
          disabled={!draft || !dirty || saving || generating}
          className="h-10 px-5 text-sm font-semibold text-white bg-primary hover:bg-primary-hover rounded-[var(--radius-sm)] transition-colors cursor-pointer disabled:opacity-50 flex items-center gap-2"
        >
          {saving && (
            <span className="w-3.5 h-3.5 border-2 border-white/30 border-t-white rounded-full animate-spin" />
          )}
          保存剧本
        </button>
      </div>
    </motion.div>
  )
}

export default function ScriptDrawer({ open, scriptVersion, ...bodyProps }: ScriptDrawerProps) {
  return (
    <AnimatePresence>
      {open && (
        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          exit={{ opacity: 0 }}
          transition={{ duration: 0.15 }}
          className="fixed inset-0 z-40 bg-black/30"
          onClick={bodyProps.onClose}
        >
          <DrawerBody key={scriptVersion} {...bodyProps} />
        </motion.div>
      )}
    </AnimatePresence>
  )
}
