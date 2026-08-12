import { useEffect, useState } from 'react'
import { NavLink, useLocation } from 'react-router-dom'
import { Languages, BookOpen, GraduationCap, Palette, ChevronDown, Plus } from 'lucide-react'
import { motion, AnimatePresence } from 'framer-motion'
import type { LucideIcon } from 'lucide-react'
import { createTemplate, getTemplates } from '../../services/t2i'
import type { T2ITemplate } from '../../types/t2i'
import { useAuth } from '../../store/AuthContext'
import T2ITemplateEditModal from '../t2i/T2ITemplateEditModal'

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

export default function AiToolsSidebar() {
  const location = useLocation()
  const { user } = useAuth()
  const isAdmin = user?.role === 'admin'

  const [templates, setTemplates] = useState<T2ITemplate[]>([])
  const [createOpen, setCreateOpen] = useState(false)

  const loadTemplates = () =>
    getTemplates().then((res) => {
      if (res.code === 0) setTemplates(res.data.templates)
    })

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

  const handleCreate = async (payload: {
    code: string
    name: string
    description: string
    prompt: string
    order_index: number
  }) => {
    const res = await createTemplate({
      code: payload.code,
      name: payload.name,
      description: payload.description || null,
      prompt: payload.prompt,
      order_index: payload.order_index,
    })
    if (res.code !== 0) throw new Error(res.message)
    setCreateOpen(false)
    await loadTemplates()
  }

  const t2iChildren: SubItem[] = [
    ...[...templates]
      .sort((a, b) => a.order_index - b.order_index || a.code.localeCompare(b.code))
      .map((t) => ({
        to: `/ai-tools/text-to-image/${t.code}`,
        label: t.name,
      })),
    { to: '/ai-tools/text-to-image/playground', label: '测试' },
  ]

  const menu: MenuItem[] = [
    { to: '/ai-tools/translate', label: '翻译 / 英文优化', icon: Languages },
    { to: '/ai-tools/hanzi', label: '汉字学习', icon: BookOpen },
    {
      label: '英文启蒙',
      icon: GraduationCap,
      children: [
        { to: '/ai-tools/english/themes', label: '主题列表' },
        { to: '/ai-tools/english/quiz', label: '答题' },
      ],
    },
    {
      label: '文生图',
      icon: Palette,
      children: t2iChildren,
    },
  ]

  const [expanded, setExpanded] = useState<Record<string, boolean>>(() => ({
    英文启蒙: location.pathname.startsWith('/ai-tools/english'),
    文生图: location.pathname.startsWith('/ai-tools/text-to-image'),
  }))

  const toggle = (label: string) => {
    setExpanded((p) => ({ ...p, [label]: !p[label] }))
  }

  const nextOrderIndex =
    templates.length > 0 ? Math.max(...templates.map((t) => t.order_index)) + 1 : 0

  return (
    <>
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
              const showAddBtn = isAdmin && item.label === '文生图'
              return (
                <div key={item.label}>
                  <div
                    className={`w-full flex items-center gap-2 px-3 py-2 rounded-[var(--radius-sm)] text-sm font-medium transition-colors ${
                      hasActive
                        ? 'text-primary'
                        : 'text-text-secondary hover:text-text-primary hover:bg-page'
                    }`}
                  >
                    <button
                      onClick={() => toggle(item.label)}
                      className="flex items-center gap-2 flex-1 min-w-0 text-left cursor-pointer"
                    >
                      <Icon size={16} />
                      <span className="flex-1 truncate">{item.label}</span>
                    </button>
                    {showAddBtn && (
                      <button
                        onClick={(e) => {
                          e.stopPropagation()
                          setCreateOpen(true)
                        }}
                        className="w-5 h-5 inline-flex items-center justify-center rounded-full text-text-muted hover:text-primary hover:bg-primary-light transition-colors cursor-pointer"
                        aria-label="新建模板"
                        title="新建模板"
                      >
                        <Plus size={13} />
                      </button>
                    )}
                    <button
                      onClick={() => toggle(item.label)}
                      className="w-5 h-5 inline-flex items-center justify-center cursor-pointer"
                      aria-label={isOpen ? '收起' : '展开'}
                    >
                      <ChevronDown
                        size={14}
                        className={`transition-transform ${isOpen ? 'rotate-0' : '-rotate-90'}`}
                      />
                    </button>
                  </div>
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
                              end
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

    {isAdmin && (
      <T2ITemplateEditModal
        open={createOpen}
        template={null}
        nextOrderIndex={nextOrderIndex}
        onClose={() => setCreateOpen(false)}
        onSubmit={handleCreate}
      />
    )}
    </>
  )
}
