import { useEffect, useState } from 'react'
import Modal from '../ui/Modal'
import type { HanziCharacter } from '../../types/hanzi'

interface Props {
  open: boolean
  onClose: () => void
  onSubmit: (payload: { char: string; pinyin: string; example_words: string[]; order_index: number }) => void
  character: HanziCharacter | null
  nextOrderIndex: number
  submitting?: boolean
}

const HANZI_RE = /^[\u4e00-\u9fa5]$/
const MAX_WORDS = 20
const MAX_WORD_LEN = 16

function parseWords(text: string): string[] {
  return text
    .split(/[\n,，、\s]+/)
    .map((w) => w.trim())
    .filter(Boolean)
}

export default function CharacterEditModal({ open, onClose, onSubmit, character, nextOrderIndex, submitting }: Props) {
  const [char, setChar] = useState('')
  const [pinyin, setPinyin] = useState('')
  const [wordsText, setWordsText] = useState('')
  const [orderIndex, setOrderIndex] = useState(0)
  const [errors, setErrors] = useState<{ char?: string; pinyin?: string; words?: string }>({})

  useEffect(() => {
    if (!open) return
    setChar(character?.char ?? '')
    setPinyin(character?.pinyin ?? '')
    setWordsText((character?.example_words ?? []).join('、'))
    setOrderIndex(character?.order_index ?? nextOrderIndex)
    setErrors({})
  }, [open, character, nextOrderIndex])

  const validate = () => {
    const next: typeof errors = {}
    if (!char.trim()) next.char = '必填'
    else if (!HANZI_RE.test(char.trim())) next.char = '必须是 1 个汉字'
    if (!pinyin.trim()) next.pinyin = '必填'
    const words = parseWords(wordsText)
    if (words.some((w) => w.length > MAX_WORD_LEN)) next.words = `单个例词不超过 ${MAX_WORD_LEN} 字符`
    else if (words.length > MAX_WORDS) next.words = `例词最多 ${MAX_WORDS} 条`
    setErrors(next)
    return Object.keys(next).length === 0
  }

  const handleSubmit = () => {
    if (!validate()) return
    onSubmit({
      char: char.trim(),
      pinyin: pinyin.trim(),
      example_words: parseWords(wordsText),
      order_index: orderIndex,
    })
  }

  return (
    <Modal
      open={open}
      onClose={onClose}
      title={character ? '编辑字条' : '添加字条'}
      subtitle={character ? `修改「${character.char}」` : '录入一个新的汉字'}
      width={520}
      footer={
        <>
          <button
            onClick={onClose}
            className="h-9 px-4 rounded-[var(--radius-sm)] text-sm font-semibold text-text-secondary hover:bg-page cursor-pointer transition-colors"
          >
            取消
          </button>
          <button
            onClick={handleSubmit}
            disabled={submitting}
            className="h-9 px-4 rounded-[var(--radius-sm)] text-sm font-semibold bg-primary text-text-on-primary hover:bg-primary-hover cursor-pointer transition-colors disabled:opacity-50 disabled:cursor-not-allowed flex items-center gap-2"
          >
            {submitting && (
              <div className="w-3.5 h-3.5 border-2 border-white/30 border-t-white rounded-full animate-spin" />
            )}
            保存
          </button>
        </>
      }
    >
      <div className="flex flex-col gap-4">
        <div className="flex gap-4">
          <div className="flex-shrink-0" style={{ width: 120 }}>
            <label className="block text-[13px] font-semibold text-text-primary mb-1.5">
              字 <span className="text-error">*</span>
            </label>
            <input
              type="text"
              value={char}
              maxLength={1}
              onChange={(e) => {
                setChar(e.target.value)
                if (errors.char) setErrors({ ...errors, char: undefined })
              }}
              placeholder="人"
              className={`w-full h-11 px-3 text-2xl text-center font-semibold bg-card border rounded-[var(--radius-sm)] focus:outline-none transition-shadow ${
                errors.char
                  ? 'border-error focus:ring-2 focus:ring-error/30'
                  : 'border-border focus:ring-2 focus:ring-primary/30 focus:border-primary'
              }`}
            />
            {errors.char && <p className="text-xs text-error mt-1.5">{errors.char}</p>}
          </div>

          <div className="flex-1">
            <label className="block text-[13px] font-semibold text-text-primary mb-1.5">
              拼音 <span className="text-error">*</span>
            </label>
            <input
              type="text"
              value={pinyin}
              onChange={(e) => {
                setPinyin(e.target.value)
                if (errors.pinyin) setErrors({ ...errors, pinyin: undefined })
              }}
              placeholder="rén"
              className={`w-full h-11 px-3 text-base bg-card border rounded-[var(--radius-sm)] focus:outline-none transition-shadow ${
                errors.pinyin
                  ? 'border-error focus:ring-2 focus:ring-error/30'
                  : 'border-border focus:ring-2 focus:ring-primary/30 focus:border-primary'
              }`}
            />
            {errors.pinyin && <p className="text-xs text-error mt-1.5">{errors.pinyin}</p>}
          </div>
        </div>

        <div>
          <label className="block text-[13px] font-semibold text-text-primary mb-1.5">
            例词
            <span className="ml-2 text-xs text-text-muted font-normal">
              选填 · 用中英文逗号 / 顿号 / 空格 / 换行分隔
            </span>
          </label>
          <textarea
            value={wordsText}
            onChange={(e) => {
              setWordsText(e.target.value)
              if (errors.words) setErrors({ ...errors, words: undefined })
            }}
            placeholder="人类、大人、人口、人们"
            rows={2}
            className={`w-full px-3 py-2 text-base bg-card border rounded-[var(--radius-sm)] focus:outline-none transition-shadow resize-none ${
              errors.words
                ? 'border-error focus:ring-2 focus:ring-error/30'
                : 'border-border focus:ring-2 focus:ring-primary/30 focus:border-primary'
            }`}
          />
          {errors.words && <p className="text-xs text-error mt-1.5">{errors.words}</p>}
        </div>

        <div>
          <label className="block text-[13px] font-semibold text-text-primary mb-1.5">排序位</label>
          <input
            type="number"
            value={orderIndex}
            onChange={(e) => setOrderIndex(Number(e.target.value))}
            className="w-32 h-11 px-3 text-base bg-card border border-border rounded-[var(--radius-sm)] focus:outline-none focus:ring-2 focus:ring-primary/30 focus:border-primary transition-shadow"
          />
        </div>
      </div>
    </Modal>
  )
}
