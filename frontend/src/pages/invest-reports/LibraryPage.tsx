// 投资报告 · 范本库：上传历史报告范本，学习生成两类模板。

import { useCallback, useEffect, useRef, useState } from 'react'
import { Link } from 'react-router-dom'
import { ChevronRight, CircleAlert } from 'lucide-react'
import Navbar from '../../components/layout/Navbar'
import TemplateSection from '../../components/invest-reports/TemplateSection'
import type { LibraryResponse, ReportType } from '../../types/investReports'
import { deleteSample, getLibrary, learnTemplate, uploadSamples } from '../../services/investReports'

export default function LibraryPage() {
  const [lib, setLib] = useState<LibraryResponse | null>(null)
  const [error, setError] = useState('')
  const [busy, setBusy] = useState(false)
  const pollRef = useRef<number | null>(null)

  const load = useCallback(async () => {
    const res = await getLibrary()
    if (res.code === 0) {
      setLib(res.data)
      setError('')
      const pending =
        res.data.advice.template?.status === 'learning' ||
        res.data.dd.template?.status === 'learning' ||
        [...res.data.advice.samples, ...res.data.dd.samples].some((s) => s.parse_state === 'parsing')
      if (pending && pollRef.current === null) {
        pollRef.current = window.setInterval(async () => {
          const r = await getLibrary()
          if (r.code === 0) {
            setLib(r.data)
            const still =
              r.data.advice.template?.status === 'learning' ||
              r.data.dd.template?.status === 'learning' ||
              [...r.data.advice.samples, ...r.data.dd.samples].some((s) => s.parse_state === 'parsing')
            if (!still && pollRef.current !== null) {
              window.clearInterval(pollRef.current)
              pollRef.current = null
            }
          }
        }, 1500)
      }
    } else {
      setError(res.message)
    }
  }, [])

  useEffect(() => {
    // 异步取数，setState 发生在 await 之后；规则对此误报
    // eslint-disable-next-line react-hooks/set-state-in-effect
    load()
    return () => {
      if (pollRef.current !== null) window.clearInterval(pollRef.current)
    }
  }, [load])

  const handle = async (fn: () => Promise<{ code: number; message: string }>) => {
    setBusy(true)
    const res = await fn()
    setBusy(false)
    if (res.code !== 0) setError(res.message)
    await load()
  }

  const section = (type: ReportType) =>
    lib && (
      <TemplateSection
        type={type}
        group={type === 'advice' ? lib.advice : lib.dd}
        busy={busy}
        onUpload={(files) => handle(() => uploadSamples(type, files))}
        onDeleteSample={(id) => handle(() => deleteSample(id))}
        onLearn={() => handle(() => learnTemplate(type))}
      />
    )

  const missing = lib && (!lib.advice.template || lib.advice.template.status !== 'ready' || !lib.dd.template || lib.dd.template.status !== 'ready')

  return (
    <div className="min-h-screen bg-page">
      <Navbar />
      <header className="bg-card border-b border-border">
        <div className="max-w-6xl mx-auto px-5 h-14 flex items-center gap-2">
          <Link to="/invest-reports" className="text-[13px] text-text-muted hover:text-primary">投资报告</Link>
          <ChevronRight size={14} className="text-text-muted" />
          <h1 className="text-base font-bold text-text-primary tracking-tight">范本库</h1>
          <div className="flex-1" />
          {missing && (
            <span className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-[var(--radius-sm)] bg-warning-light text-warning text-xs">
              <CircleAlert size={13} />
              模板未学习的类型暂不能创建报告
            </span>
          )}
        </div>
      </header>

      <main className="max-w-6xl mx-auto px-5 py-6">
        {error && (
          <p role="alert" className="mb-4 px-3.5 py-2.5 rounded-[var(--radius-sm)] bg-error-light text-error text-xs">{error}</p>
        )}
        {!lib ? (
          <div className="flex gap-6">
            {[0, 1].map((i) => (
              <div key={i} className="flex-1 h-72 rounded-2xl bg-card border border-border animate-pulse" />
            ))}
          </div>
        ) : (
          <div className="flex gap-6">
            {section('advice')}
            {section('dd')}
          </div>
        )}
      </main>
    </div>
  )
}
