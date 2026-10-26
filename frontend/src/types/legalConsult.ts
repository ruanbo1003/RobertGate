// 法律咨询（RAG 对话）类型定义。
// 对应 docs/api/legal-consult.md

export interface Citation {
  article_no: number
  label: string
}

export type LegalRole = 'user' | 'assistant'

export interface LegalMessage {
  id: string
  role: LegalRole
  content: string
  citations: Citation[]
  created_at: string
}

export interface LegalMessagesResponse {
  messages: LegalMessage[]
}

export interface LawArticle {
  article_no: number
  label: string
  content: string
}

export interface LawArticleResponse {
  article: LawArticle
}

/** SSE 流式回调。事件顺序：citations → delta（多次）→ done；失败时 error。 */
export interface SendMessageHandlers {
  onCitations: (citations: Citation[]) => void
  onDelta: (text: string) => void
  onDone: (message: LegalMessage) => void
  onError: (code: number, message: string) => void
}
