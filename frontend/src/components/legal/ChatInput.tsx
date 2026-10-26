import { useRef, useState } from 'react'
import { Info, Send } from 'lucide-react'

interface ChatInputProps {
  disabled: boolean
  onSend: (content: string) => void
}

const MAX_LEN = 2000

export default function ChatInput({ disabled, onSend }: ChatInputProps) {
  const [value, setValue] = useState('')
  const textareaRef = useRef<HTMLTextAreaElement>(null)

  const trimmed = value.trim()
  const canSend = !disabled && trimmed.length > 0 && trimmed.length <= MAX_LEN

  const submit = () => {
    if (!canSend) return
    onSend(trimmed)
    setValue('')
    if (textareaRef.current) textareaRef.current.style.height = 'auto'
  }

  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === 'Enter' && !e.shiftKey && !e.nativeEvent.isComposing) {
      e.preventDefault()
      submit()
    }
  }

  const handleChange = (e: React.ChangeEvent<HTMLTextAreaElement>) => {
    setValue(e.target.value)
    const el = e.target
    el.style.height = 'auto'
    el.style.height = `${Math.min(el.scrollHeight, 160)}px`
  }

  return (
    <div className="flex flex-col gap-2">
      <div className="flex items-end gap-3 bg-card border border-border rounded-[var(--radius-md)] px-4 py-3 shadow-sm focus-within:ring-2 focus-within:ring-ring/30 focus-within:border-border-focus transition-all duration-150">
        <label htmlFor="legal-chat-input" className="sr-only">
          法律问题
        </label>
        <textarea
          id="legal-chat-input"
          ref={textareaRef}
          value={value}
          onChange={handleChange}
          onKeyDown={handleKeyDown}
          disabled={disabled}
          rows={1}
          maxLength={MAX_LEN}
          placeholder="描述你遇到的法律问题…（Enter 发送，Shift + Enter 换行）"
          className="flex-1 self-center resize-none bg-transparent text-base text-text-primary placeholder:text-text-muted outline-none disabled:opacity-60 leading-relaxed"
        />
        <button
          onClick={submit}
          disabled={!canSend}
          className="shrink-0 w-11 h-11 -m-1 flex items-center justify-center rounded-[var(--radius-sm)] bg-primary text-text-on-primary transition-all duration-150 hover:bg-primary-hover disabled:opacity-40 disabled:cursor-not-allowed cursor-pointer"
          aria-label="发送"
        >
          <Send size={16} />
        </button>
      </div>
      <p className="flex items-center justify-center gap-1.5 text-xs text-text-muted">
        <Info size={12} />
        回答基于《中华人民共和国民法典》生成，仅供参考，不构成正式法律意见
      </p>
    </div>
  )
}
