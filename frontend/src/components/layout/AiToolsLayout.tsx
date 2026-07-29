import { Outlet, useLocation } from 'react-router-dom'
import { ChevronRight } from 'lucide-react'
import Navbar from './Navbar'
import AiToolsSidebar from './AiToolsSidebar'

const crumbMap: Record<string, string> = {
  '/ai-tools/translate': '翻译 / 英文优化',
  '/ai-tools/hanzi': '汉字学习 › 级别列表',
  '/ai-tools/admin/hanzi': '汉字学习 › 管理 · 级别',
  '/ai-tools/english/themes': '英文启蒙 › 主题列表',
  '/ai-tools/english/quiz': '英文启蒙 › 答题',
  '/ai-tools/text-to-image': '文生图',
}

export default function AiToolsLayout() {
  const location = useLocation()
  let crumb = crumbMap[location.pathname] ?? ''
  if (!crumb && location.pathname.startsWith('/ai-tools/admin/hanzi/levels/')) {
    crumb = '汉字学习 › 管理 · 字条'
  } else if (!crumb && location.pathname.startsWith('/ai-tools/hanzi/levels/')) {
    crumb = '汉字学习 › 字表'
  }

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
