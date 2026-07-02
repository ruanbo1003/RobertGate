import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { motion } from 'framer-motion'
import { Check, X, Plus } from 'lucide-react'
import { addHanzi, deleteHanzi, getHanziLibrary } from '../../services/aiTools'
import type { HanziItem } from '../../types/aiTools'

export default function HanziLibraryPage() {
  const navigate = useNavigate()
  const [items, setItems] = useState<HanziItem[]>([])
  const [total, setTotal] = useState(0)
  const [learned, setLearned] = useState(0)
  const [loading, setLoading] = useState(true)
  const [text, setText] = useState('')
  const [adding, setAdding] = useState(false)
  const [notice, setNotice] = useState<{ added: number; duplicated: number } | null>(null)

  const load = async () => {
    setLoading(true)
    const res = await getHanziLibrary()
    if (res.code === 0) {
      setItems(res.data.items)
      setTotal(res.data.total)
      setLearned(res.data.learned)
    }
    setLoading(false)
  }

  useEffect(() => {
    void load()
  }, [])

  const handleAdd = async () => {
    if (!text.trim()) return
    setAdding(true)
    const res = await addHanzi(text)
    setAdding(false)
    if (res.code === 0) {
      setNotice({ added: res.data.added.length, duplicated: res.data.duplicated.length })
      setText('')
      await load()
      setTimeout(() => setNotice(null), 3000)
    }
  }

  const handleDelete = async (char: string) => {
    if (!confirm(`确认删除「${char}」？不可撤销。`)) return
    const res = await deleteHanzi(char)
    if (res.code === 0) await load()
  }

  return (
    <div className="max-w-4xl mx-auto flex flex-col gap-6">
      {/* 添加区 */}
      <div className="bg-card border border-border rounded-[var(--radius-lg)] p-4 shadow-sm">
        <textarea
          value={text}
          onChange={(e) => setText(e.target.value)}
          placeholder="粘贴或输入含汉字的文本……"
          rows={3}
          className="w-full resize-y font-sans text-base text-text-primary placeholder:text-text-muted bg-transparent focus:outline-none"
        />
        <div className="flex items-center justify-between mt-3 pt-3 border-t border-border">
          {notice ? (
            <span className="text-sm text-success">
              已加入 {notice.added} 字{notice.duplicated > 0 ? `，${notice.duplicated} 字已存在` : ''}
            </span>
          ) : (
            <span className="text-xs text-text-muted">仅提取汉字，自动去重</span>
          )}
          <motion.button
            onClick={handleAdd}
            disabled={!text.trim() || adding}
            whileHover={!text.trim() || adding ? undefined : { scale: 1.01 }}
            whileTap={!text.trim() || adding ? undefined : { scale: 0.98 }}
            className="flex items-center gap-1.5 h-9 px-4 bg-primary text-text-on-primary text-sm font-semibold rounded-[var(--radius-sm)] hover:bg-primary-hover transition-colors disabled:opacity-50 disabled:cursor-not-allowed cursor-pointer"
          >
            {adding ? (
              <div className="w-3.5 h-3.5 border-2 border-white/30 border-t-white rounded-full animate-spin" />
            ) : (
              <Plus size={14} />
            )}
            加入字库
          </motion.button>
        </div>
      </div>

      {/* 进度 */}
      <div className="flex items-center justify-between">
        <div className="text-sm text-text-secondary">
          进度：<span className="font-semibold text-primary">已学 {learned}</span> / 总 {total}
        </div>
        <div className="w-40 h-1.5 bg-border rounded-full overflow-hidden">
          <div
            className="h-full bg-success transition-all"
            style={{ width: total ? `${(learned / total) * 100}%` : '0%' }}
          />
        </div>
      </div>

      {/* 字库网格 */}
      {loading ? (
        <div className="flex justify-center py-12">
          <div className="w-6 h-6 border-2 border-primary/30 border-t-primary rounded-full animate-spin" />
        </div>
      ) : items.length === 0 ? (
        <div className="text-center py-12 text-text-muted text-sm">
          字库还是空的，先在上面输入一些文本吧
        </div>
      ) : (
        <div className="grid grid-cols-6 md:grid-cols-8 lg:grid-cols-10 gap-2">
          {items.map((item) => (
            <div key={item.char} className="relative group">
              <button
                onClick={() => navigate(`/ai-tools/hanzi/learn?char=${encodeURIComponent(item.char)}`)}
                className={`w-full aspect-square rounded-[var(--radius-sm)] border flex items-center justify-center text-2xl font-semibold transition-colors cursor-pointer ${
                  item.learned
                    ? 'bg-success-light border-success text-success'
                    : 'bg-card border-border text-text-primary hover:border-primary hover:bg-primary-light/40'
                }`}
              >
                {item.char}
              </button>
              {item.learned && (
                <div className="absolute top-1 right-1 w-4 h-4 rounded-full bg-success flex items-center justify-center">
                  <Check size={10} className="text-white" />
                </div>
              )}
              <button
                onClick={() => handleDelete(item.char)}
                className="absolute -top-1.5 -right-1.5 w-5 h-5 rounded-full bg-error text-white flex items-center justify-center opacity-0 group-hover:opacity-100 transition-opacity cursor-pointer"
                aria-label="删除"
              >
                <X size={11} />
              </button>
            </div>
          ))}
        </div>
      )}
    </div>
  )
}
