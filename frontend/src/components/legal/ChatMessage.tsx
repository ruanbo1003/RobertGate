import { useState } from 'react'
import { AlertCircle, Check, Copy, RotateCcw } from 'lucide-react'
import type { Citation, LegalMessage } from '../../types/legalConsult'
import CitationBadge from './CitationBadge'

interface ChatMessageProps {
  message: LegalMessage
  onCitationClick: (citation: Citation, citations: Citation[]) => void
}

function Paragraphs({ content }: { content: string }) {
  return (
    <div className="flex flex-col gap-3">
      {content
        .split(/\n{2,}/)
        .filter((p) => p.trim())
        .map((p, i) => (
          <p key={i} className="text-[15px] leading-[1.7] text-text-primary whitespace-pre-wrap">
            {p}
          </p>
        ))}
    </div>
  )
}

export default function ChatMessage({ message, onCitationClick }: ChatMessageProps) {
  const [copied, setCopied] = useState(false)

  if (message.role === 'user') {
    return (
      <div className="flex justify-end">
        <div className="max-w-[80%] bg-primary text-text-on-primary rounded-[16px] rounded-br-[4px] px-4 py-3">
          <p className="text-[15px] leading-[1.6] whitespace-pre-wrap">{message.content}</p>
        </div>
      </div>
    )
  }

  const handleCopy = async () => {
    try {
      await navigator.clipboard.writeText(message.content)
      setCopied(true)
      setTimeout(() => setCopied(false), 2000)
    } catch {
      // 剪贴板不可用时静默失败
    }
  }

  return (
    <div className="flex justify-start">
      <div className="max-w-[85%] bg-card border border-border rounded-[16px] rounded-tl-[4px] px-5 py-4 flex flex-col gap-3 shadow-sm">
        <Paragraphs content={message.content} />
        <div className="flex items-center justify-between gap-3 pt-2 border-t border-border flex-wrap">
          <div className="flex items-center gap-2 flex-wrap">
            {message.citations.length > 0 && (
              <>
                <span className="text-xs text-text-muted">引用条文</span>
                {message.citations.map((c) => (
                  <CitationBadge
                    key={c.article_no}
                    citation={c}
                    onClick={(citation) => onCitationClick(citation, message.citations)}
                  />
                ))}
              </>
            )}
          </div>
          <button
            onClick={handleCopy}
            className="inline-flex items-center gap-1 text-xs text-text-muted hover:text-text-primary transition-colors duration-150 cursor-pointer"
            aria-label="复制回答"
          >
            {copied ? (
              <>
                <Check size={13} className="text-success" />
                <span className="text-success">已复制</span>
              </>
            ) : (
              <>
                <Copy size={13} />
                复制
              </>
            )}
          </button>
        </div>
      </div>
    </div>
  )
}

interface StreamingMessageProps {
  text: string
  citations: Citation[]
  onCitationClick: (citation: Citation, citations: Citation[]) => void
}

/** 流式输出中的 AI 消息：先显示检索占位，有增量后渲染正文。 */
export function StreamingMessage({ text, citations, onCitationClick }: StreamingMessageProps) {
  return (
    <div className="flex justify-start">
      <div className="max-w-[85%] bg-card border border-border rounded-[16px] rounded-tl-[4px] px-5 py-4 flex flex-col gap-3 shadow-sm">
        {text ? (
          <Paragraphs content={text} />
        ) : (
          <div className="flex items-center gap-2 text-sm text-text-muted">
            <span className="w-4 h-4 border-2 border-primary/30 border-t-primary rounded-full animate-spin" />
            检索相关条文中…
          </div>
        )}
        {citations.length > 0 && (
          <div className="flex items-center gap-2 flex-wrap pt-2 border-t border-border">
            <span className="text-xs text-text-muted">引用条文</span>
            {citations.map((c) => (
              <CitationBadge
                key={c.article_no}
                citation={c}
                onClick={(citation) => onCitationClick(citation, citations)}
              />
            ))}
          </div>
        )}
      </div>
    </div>
  )
}

interface ErrorMessageProps {
  message: string
  onRetry: () => void
  retrying: boolean
}

/** 发送失败的错误消息，带重试按钮。 */
export function ErrorMessage({ message, onRetry, retrying }: ErrorMessageProps) {
  return (
    <div className="flex justify-start">
      <div className="max-w-[85%] bg-error-light border border-error/30 rounded-[16px] rounded-tl-[4px] px-5 py-4 flex items-center gap-3">
        <AlertCircle size={16} className="text-error shrink-0" />
        <p className="text-sm text-error">{message}</p>
        <button
          onClick={onRetry}
          disabled={retrying}
          className="inline-flex items-center gap-1 shrink-0 px-3 py-1.5 rounded-[var(--radius-sm)] bg-card border border-border text-xs font-semibold text-text-primary hover:border-border-focus transition-colors duration-150 disabled:opacity-50 cursor-pointer"
        >
          <RotateCcw size={12} />
          重试
        </button>
      </div>
    </div>
  )
}
