import { useEffect, useRef, useState } from 'react'
import { AnimatePresence, motion } from 'framer-motion'
import { BookOpen, X } from 'lucide-react'
import type { Citation, LawArticle } from '../../types/legalConsult'
import { getArticle } from '../../services/legalConsult'

interface LawArticleDrawerProps {
  open: boolean
  citations: Citation[]
  activeNo: number | null
  onClose: () => void
}

type ArticleState =
  | { status: 'loading' }
  | { status: 'loaded'; article: LawArticle }
  | { status: 'error'; message: string }

export default function LawArticleDrawer({
  open,
  citations,
  activeNo,
  onClose,
}: LawArticleDrawerProps) {
  const [articles, setArticles] = useState<Record<number, ArticleState>>({})
  const loadedRef = useRef<Set<number>>(new Set())
  const itemRefs = useRef<Record<number, HTMLDivElement | null>>({})

  useEffect(() => {
    if (!open) return
    const onKey = (e: KeyboardEvent) => {
      if (e.key === 'Escape') onClose()
    }
    window.addEventListener('keydown', onKey)
    return () => window.removeEventListener('keydown', onKey)
  }, [open, onClose])

  useEffect(() => {
    if (!open) return
    let mounted = true
    for (const c of citations) {
      if (loadedRef.current.has(c.article_no)) continue
      getArticle(c.article_no).then((res) => {
        if (!mounted) return
        if (res.code === 0) loadedRef.current.add(c.article_no)
        setArticles((prev) => {
          if (prev[c.article_no]?.status === 'loaded') return prev
          return {
            ...prev,
            [c.article_no]:
              res.code === 0
                ? { status: 'loaded', article: res.data.article }
                : { status: 'error', message: res.message },
          }
        })
      })
    }
    return () => {
      mounted = false
    }
  }, [open, citations])

  useEffect(() => {
    if (!open || activeNo == null) return
    const el = itemRefs.current[activeNo]
    if (el) el.scrollIntoView({ behavior: 'smooth', block: 'nearest' })
  }, [open, activeNo, articles])

  return (
    <AnimatePresence>
      {open && (
        <motion.aside
          initial={{ x: '100%' }}
          animate={{ x: 0 }}
          exit={{ x: '100%' }}
          transition={{ duration: 0.25, ease: 'easeOut' }}
          className="fixed right-0 top-14 bottom-0 w-full sm:w-[420px] bg-card border-l border-border shadow-lg z-30 flex flex-col"
          aria-label="引用条文"
        >
          <div className="flex items-center justify-between px-5 py-4 border-b border-border shrink-0">
            <div className="flex items-center gap-2">
              <BookOpen size={18} className="text-primary" />
              <h3 className="text-[15px] font-semibold text-text-primary">
                引用条文 ·《中华人民共和国民法典》
              </h3>
            </div>
            <button
              onClick={onClose}
              className="w-8 h-8 rounded-[var(--radius-sm)] flex items-center justify-center text-text-muted hover:text-text-primary hover:bg-page transition-colors cursor-pointer"
              aria-label="关闭条文抽屉"
            >
              <X size={16} />
            </button>
          </div>

          <div className="flex-1 overflow-y-auto p-5 flex flex-col gap-3">
            {citations.length === 0 && (
              <p className="text-sm text-text-muted text-center py-10">引用的法条会出现在这里</p>
            )}
            {citations.map((c) => {
              const state = articles[c.article_no]
              const active = c.article_no === activeNo
              return (
                <div
                  key={c.article_no}
                  ref={(el) => {
                    itemRefs.current[c.article_no] = el
                  }}
                  className={`rounded-[var(--radius-sm)] p-4 flex flex-col gap-2 border transition-colors duration-200 ${
                    active
                      ? 'bg-primary-light/60 border-primary border-l-[3px]'
                      : 'bg-card border-border'
                  }`}
                >
                  <div className="flex items-center justify-between">
                    <span
                      className={`text-sm font-bold ${active ? 'text-primary' : 'text-text-primary'}`}
                    >
                      {c.label}
                    </span>
                    {active && (
                      <span className="px-2 py-0.5 rounded bg-primary text-text-on-primary text-[11px]">
                        本次引用
                      </span>
                    )}
                  </div>
                  {(!state || state.status === 'loading') && (
                    <div className="flex flex-col gap-2 animate-pulse" aria-label="加载中">
                      <div className="h-3 bg-page-alt rounded w-full" />
                      <div className="h-3 bg-page-alt rounded w-4/5" />
                    </div>
                  )}
                  {state?.status === 'loaded' && (
                    <p className="text-[13px] leading-[1.8] text-text-primary">
                      {state.article.content}
                    </p>
                  )}
                  {state?.status === 'error' && (
                    <p className="text-[13px] text-error">{state.message}</p>
                  )}
                </div>
              )
            })}
          </div>
        </motion.aside>
      )}
    </AnimatePresence>
  )
}
