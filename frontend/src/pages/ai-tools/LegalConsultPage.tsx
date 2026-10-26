import { useCallback, useEffect, useRef, useState } from 'react'
import { Trash2 } from 'lucide-react'
import type { Citation, LegalMessage } from '../../types/legalConsult'
import { clearMessages, getMessages, sendMessage } from '../../services/legalConsult'
import ChatMessage, { ErrorMessage, StreamingMessage } from '../../components/legal/ChatMessage'
import ChatInput from '../../components/legal/ChatInput'
import ExampleQuestions from '../../components/legal/ExampleQuestions'
import LawArticleDrawer from '../../components/legal/LawArticleDrawer'
import Modal from '../../components/ui/Modal'
import Button from '../../components/ui/Button'

interface StreamingState {
  text: string
  citations: Citation[]
}

interface SendErrorState {
  message: string
  lastContent: string
}

interface DrawerState {
  open: boolean
  citations: Citation[]
  activeNo: number | null
}

const tempId = () => `temp-${Math.random().toString(36).slice(2, 10)}`

export default function LegalConsultPage() {
  const [historyLoading, setHistoryLoading] = useState(true)
  const [historyError, setHistoryError] = useState<string | null>(null)
  const [messages, setMessages] = useState<LegalMessage[]>([])
  const [streaming, setStreaming] = useState<StreamingState | null>(null)
  const [sendError, setSendError] = useState<SendErrorState | null>(null)
  const [sending, setSending] = useState(false)
  const [drawer, setDrawer] = useState<DrawerState>({ open: false, citations: [], activeNo: null })
  const [clearOpen, setClearOpen] = useState(false)
  const [clearing, setClearing] = useState(false)
  const bottomRef = useRef<HTMLDivElement>(null)

  const fetchHistory = useCallback(() => {
    getMessages().then((res) => {
      setHistoryLoading(false)
      if (res.code === 0) setMessages(res.data.messages)
      else setHistoryError(res.message)
    })
  }, [])

  useEffect(() => {
    fetchHistory()
  }, [fetchHistory])

  const retryHistory = useCallback(() => {
    setHistoryLoading(true)
    setHistoryError(null)
    fetchHistory()
  }, [fetchHistory])

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth', block: 'end' })
  }, [messages, streaming?.text, streaming?.citations.length, sendError])

  const doSend = useCallback((content: string, appendUser: boolean) => {
    setSending(true)
    setSendError(null)
    setStreaming({ text: '', citations: [] })
    if (appendUser) {
      setMessages((prev) => [
        ...prev,
        {
          id: tempId(),
          role: 'user',
          content,
          citations: [],
          created_at: new Date().toISOString(),
        },
      ])
    }
    void sendMessage(content, {
      onCitations: (citations) => setStreaming((s) => (s ? { ...s, citations } : s)),
      onDelta: (text) => setStreaming((s) => (s ? { ...s, text: s.text + text } : s)),
      onDone: (message) => {
        setMessages((prev) => [...prev, message])
        setStreaming(null)
        setSending(false)
      },
      onError: (_code, message) => {
        setStreaming(null)
        setSendError({ message, lastContent: content })
        setSending(false)
      },
    })
  }, [])

  const handleSend = useCallback((content: string) => doSend(content, true), [doSend])
  const handleRetry = useCallback(() => {
    if (sendError) doSend(sendError.lastContent, false)
  }, [sendError, doSend])

  const handleCitationClick = useCallback((citation: Citation, citations: Citation[]) => {
    setDrawer({ open: true, citations, activeNo: citation.article_no })
  }, [])

  const handleClear = async () => {
    setClearing(true)
    const res = await clearMessages()
    setClearing(false)
    if (res.code === 0) {
      setMessages([])
      setSendError(null)
      setClearOpen(false)
    }
  }

  const isEmpty = !historyLoading && !historyError && messages.length === 0 && !streaming && !sendError

  return (
    <div className="h-[calc(100dvh-9.5rem)] md:h-[calc(100dvh-10.5rem)] flex flex-col max-w-3xl mx-auto w-full">
      {messages.length > 0 && (
        <div className="flex justify-end pb-2 shrink-0">
          <button
            onClick={() => setClearOpen(true)}
            disabled={sending}
            className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-[var(--radius-sm)] text-xs font-medium text-text-muted hover:text-error hover:bg-error-light transition-colors duration-150 disabled:opacity-50 cursor-pointer"
          >
            <Trash2 size={13} />
            清空对话
          </button>
        </div>
      )}

      <div className="flex-1 overflow-y-auto flex flex-col gap-5 pr-1">
        {historyLoading && (
          <div className="flex items-center justify-center h-full gap-2 text-sm text-text-muted">
            <span className="w-4 h-4 border-2 border-primary/30 border-t-primary rounded-full animate-spin" />
            加载对话历史…
          </div>
        )}

        {historyError && (
          <div className="flex flex-col items-center justify-center h-full gap-3">
            <p className="text-sm text-error">{historyError}</p>
            <button
              onClick={retryHistory}
              className="px-4 py-2 rounded-[var(--radius-sm)] bg-card border border-border text-sm font-semibold text-text-primary hover:border-border-focus transition-colors cursor-pointer"
            >
              重新加载
            </button>
          </div>
        )}

        {isEmpty && <ExampleQuestions onSelect={handleSend} disabled={sending} />}

        {messages.map((m) => (
          <ChatMessage key={m.id} message={m} onCitationClick={handleCitationClick} />
        ))}

        {streaming && (
          <StreamingMessage
            text={streaming.text}
            citations={streaming.citations}
            onCitationClick={handleCitationClick}
          />
        )}

        {sendError && (
          <ErrorMessage message={sendError.message} onRetry={handleRetry} retrying={sending} />
        )}

        <div ref={bottomRef} />
      </div>

      <div className="pt-3 shrink-0">
        <ChatInput disabled={sending || historyLoading} onSend={handleSend} />
      </div>

      <LawArticleDrawer
        open={drawer.open}
        citations={drawer.citations}
        activeNo={drawer.activeNo}
        onClose={() => setDrawer((d) => ({ ...d, open: false }))}
      />

      <Modal
        open={clearOpen}
        onClose={() => setClearOpen(false)}
        title="清空对话"
        subtitle="清空后历史记录不可恢复"
        footer={
          <div className="flex items-center gap-2">
            <button
              onClick={() => setClearOpen(false)}
              className="px-4 h-11 rounded-[var(--radius-sm)] border border-border text-sm font-semibold text-text-primary hover:bg-page transition-colors cursor-pointer"
            >
              取消
            </button>
            <div className="w-32">
              <Button onClick={handleClear} loading={clearing}>
                确认清空
              </Button>
            </div>
          </div>
        }
      >
        <p className="text-sm text-text-secondary">
          确定要清空全部对话记录吗？清空后将回到初始状态，此操作不可撤销。
        </p>
      </Modal>
    </div>
  )
}
