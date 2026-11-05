import { useState } from 'react'
import { AnimatePresence, motion } from 'framer-motion'
import { Scissors, X } from 'lucide-react'
import type { CharacterRef, Script } from '../../types/aiVideos'

interface ScriptDrawerProps {
  open: boolean
  script: Script | null
  characters: CharacterRef[]
  saving: boolean
  onClose: () => void
  onSave: (script: Script) => void
  onResplit: (script: Script) => void
}

interface DrawerBodyProps extends Omit<ScriptDrawerProps, 'open'> {
  onClose: () => void
}

// 随抽屉打开而挂载，草稿状态在挂载时从 props 初始化
function DrawerBody({ script, characters, saving, onClose, onSave, onResplit }: DrawerBodyProps) {
  const [draft, setDraft] = useState<Script | null>(
    script ? (JSON.parse(JSON.stringify(script)) as Script) : null,
  )
  const [dirty, setDirty] = useState(false)

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
      <div className="flex-1 overflow-y-auto p-5">
        {!draft || draft.scenes.length === 0 ? (
          <p className="text-sm text-text-muted">还没有剧本</p>
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
          disabled={!draft || saving}
          className="flex items-center gap-1.5 h-10 px-4 text-sm font-semibold text-text-primary bg-card border border-border rounded-[var(--radius-sm)] hover:bg-page transition-colors cursor-pointer disabled:opacity-50"
        >
          <Scissors size={13} />
          重新拆分镜
        </button>
        <button
          onClick={() => draft && onSave(draft)}
          disabled={!draft || !dirty || saving}
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

export default function ScriptDrawer({ open, ...bodyProps }: ScriptDrawerProps) {
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
          <DrawerBody {...bodyProps} />
        </motion.div>
      )}
    </AnimatePresence>
  )
}
