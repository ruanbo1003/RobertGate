import { useState } from 'react'
import { NavLink, useLocation } from 'react-router-dom'
import { Languages, BookOpen, GraduationCap, Palette, ChevronDown } from 'lucide-react'
import { motion, AnimatePresence } from 'framer-motion'
import type { LucideIcon } from 'lucide-react'

interface SubItem {
  to: string
  label: string
}

interface MenuItem {
  to?: string
  label: string
  icon: LucideIcon
  children?: SubItem[]
}

const menu: MenuItem[] = [
  { to: '/ai-tools/translate', label: '翻译 / 英文优化', icon: Languages },
  {
    label: '汉字学习',
    icon: BookOpen,
    children: [
      { to: '/ai-tools/hanzi/library', label: '字库管理' },
      { to: '/ai-tools/hanzi/learn', label: '逐字学习' },
      { to: '/ai-tools/hanzi/sentence', label: '句子学习' },
    ],
  },
  {
    label: '英文启蒙',
    icon: GraduationCap,
    children: [
      { to: '/ai-tools/english/themes', label: '主题列表' },
      { to: '/ai-tools/english/quiz', label: '答题' },
    ],
  },
  { to: '/ai-tools/text-to-image', label: '文生图', icon: Palette },
]

export default function AiToolsSidebar() {
  const location = useLocation()
  // 展开状态：默认展开「汉字学习」；其他收起
  const [expanded, setExpanded] = useState<Record<string, boolean>>(() => {
    const init: Record<string, boolean> = {
      汉字学习: location.pathname.startsWith('/ai-tools/hanzi') || true,
      英文启蒙: location.pathname.startsWith('/ai-tools/english'),
    }
    return init
  })

  const toggle = (label: string) => {
    setExpanded((p) => ({ ...p, [label]: !p[label] }))
  }

  return (
    <aside className="w-[260px] shrink-0 bg-card border-r border-border h-[calc(100vh-3.5rem)] sticky top-14 overflow-y-auto">
      <div className="p-4">
        <div className="text-xs font-semibold text-text-muted uppercase tracking-wider mb-3 px-2">
          AI Tools
        </div>
        <nav className="flex flex-col gap-0.5">
          {menu.map((item) => {
            const Icon = item.icon
            if (item.children) {
              const isOpen = expanded[item.label]
              const hasActive = item.children.some((c) => location.pathname.startsWith(c.to))
              return (
                <div key={item.label}>
                  <button
                    onClick={() => toggle(item.label)}
                    className={`w-full flex items-center gap-2 px-3 py-2 rounded-[var(--radius-sm)] text-sm font-medium transition-colors cursor-pointer ${
                      hasActive
                        ? 'text-primary'
                        : 'text-text-secondary hover:text-text-primary hover:bg-page'
                    }`}
                  >
                    <Icon size={16} />
                    <span className="flex-1 text-left">{item.label}</span>
                    <ChevronDown
                      size={14}
                      className={`transition-transform ${isOpen ? 'rotate-0' : '-rotate-90'}`}
                    />
                  </button>
                  <AnimatePresence initial={false}>
                    {isOpen && (
                      <motion.div
                        initial={{ height: 0, opacity: 0 }}
                        animate={{ height: 'auto', opacity: 1 }}
                        exit={{ height: 0, opacity: 0 }}
                        transition={{ duration: 0.18, ease: 'easeOut' }}
                        className="overflow-hidden"
                      >
                        <div className="ml-6 border-l border-border pl-2 py-0.5 flex flex-col gap-0.5">
                          {item.children.map((sub) => (
                            <NavLink
                              key={sub.to}
                              to={sub.to}
                              className={({ isActive }) =>
                                `flex items-center px-3 py-1.5 rounded-[var(--radius-sm)] text-sm transition-colors ${
                                  isActive
                                    ? 'bg-primary-light text-primary font-semibold'
                                    : 'text-text-secondary hover:text-text-primary hover:bg-page'
                                }`
                              }
                            >
                              {sub.label}
                            </NavLink>
                          ))}
                        </div>
                      </motion.div>
                    )}
                  </AnimatePresence>
                </div>
              )
            }
            return (
              <NavLink
                key={item.to}
                to={item.to!}
                className={({ isActive }) =>
                  `flex items-center gap-2 px-3 py-2 rounded-[var(--radius-sm)] text-sm font-medium transition-colors ${
                    isActive
                      ? 'bg-primary-light text-primary'
                      : 'text-text-secondary hover:text-text-primary hover:bg-page'
                  }`
                }
              >
                <Icon size={16} />
                <span>{item.label}</span>
              </NavLink>
            )
          })}
        </nav>
      </div>
    </aside>
  )
}
