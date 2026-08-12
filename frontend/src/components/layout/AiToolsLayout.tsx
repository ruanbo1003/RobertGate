import { useEffect, useState } from 'react'
import { Outlet, useLocation } from 'react-router-dom'
import { ChevronRight } from 'lucide-react'
import Navbar from './Navbar'
import AiToolsSidebar from './AiToolsSidebar'
import { getTemplates } from '../../services/t2i'
import type { T2ITemplate } from '../../types/t2i'

const staticCrumbs: Record<string, string> = {
  '/ai-tools/translate': '翻译 / 英文优化',
  '/ai-tools/hanzi': '汉字学习 › 级别列表',
  '/ai-tools/admin/hanzi': '汉字学习 › 管理 · 级别',
  '/ai-tools/english/themes': '英文启蒙 › 主题列表',
  '/ai-tools/english/quiz': '英文启蒙 › 答题',
  '/ai-tools/text-to-image': '文生图',
  '/ai-tools/text-to-image/playground': '文生图 › 测试',
}

function buildCrumb(pathname: string, templates: T2ITemplate[]): string {
  if (staticCrumbs[pathname]) return staticCrumbs[pathname]
  if (pathname.startsWith('/ai-tools/admin/hanzi/levels/')) {
    return '汉字学习 › 管理 · 字条'
  }
  if (pathname.startsWith('/ai-tools/hanzi/levels/')) {
    return '汉字学习 › 字表'
  }
  // /ai-tools/text-to-image/:code[/:taskId]
  const m = pathname.match(/^\/ai-tools\/text-to-image\/([^/]+)(\/[^/]+)?$/)
  if (m) {
    const code = m[1]
    const isDetail = !!m[2]
    if (code === 'playground') return staticCrumbs['/ai-tools/text-to-image/playground']
    const tpl = templates.find((t) => t.code === code)
    const name = tpl?.name ?? code
    return isDetail ? `文生图 › ${name} › 任务详情` : `文生图 › ${name}`
  }
  return ''
}

export default function AiToolsLayout() {
  const location = useLocation()
  const [templates, setTemplates] = useState<T2ITemplate[]>([])

  useEffect(() => {
    let mounted = true
    getTemplates().then((res) => {
      if (!mounted) return
      if (res.code === 0) setTemplates(res.data.templates)
    })
    return () => {
      mounted = false
    }
  }, [])

  const crumb = buildCrumb(location.pathname, templates)

  return (
    <div className="min-h-screen bg-page">
      <Navbar />
      <div className="flex">
        <AiToolsSidebar />
        <main className="flex-1 min-w-0">
          {/* Topbar: 面包屑 */}
          <div className="h-12 border-b border-border bg-card flex items-center px-6">
            <div className="flex items-center gap-1.5 text-sm text-text-muted">
              <span>AI Tools</span>
              {crumb && (
                <>
                  <ChevronRight size={14} />
                  <span className="text-text-primary font-medium">{crumb}</span>
                </>
              )}
            </div>
          </div>

          <div className="p-6 md:p-8">
            <Outlet />
          </div>
        </main>
      </div>
    </div>
  )
}
