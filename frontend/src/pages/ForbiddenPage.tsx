import { Link } from 'react-router-dom'
import { ShieldOff } from 'lucide-react'

export default function ForbiddenPage() {
  return (
    <div className="min-h-screen bg-page flex items-center justify-center px-6">
      <div className="max-w-md w-full bg-card border border-border rounded-[var(--radius-lg)] shadow-sm p-10 text-center flex flex-col items-center gap-4">
        <div className="w-14 h-14 rounded-full bg-error-light flex items-center justify-center">
          <ShieldOff size={28} className="text-error" />
        </div>
        <div>
          <h1 className="text-3xl font-bold text-text-primary tracking-tight">403</h1>
          <p className="text-sm text-text-muted mt-1">你没有访问该页面的权限</p>
        </div>
        <p className="text-sm text-text-secondary">
          此页面仅对 <span className="font-semibold text-primary">管理员</span> 开放。
          如果你觉得这是个误会，请联系管理员开通权限。
        </p>
        <div className="flex items-center gap-3 mt-2">
          <Link
            to="/ai-tools/hanzi"
            className="h-11 px-5 inline-flex items-center rounded-[var(--radius-sm)] bg-primary text-text-on-primary text-sm font-semibold hover:bg-primary-hover transition-colors cursor-pointer"
          >
            去汉字学习
          </Link>
          <Link
            to="/"
            className="h-11 px-5 inline-flex items-center rounded-[var(--radius-sm)] bg-card border border-border text-text-primary text-sm font-semibold hover:border-primary hover:text-primary transition-colors cursor-pointer"
          >
            回首页
          </Link>
        </div>
      </div>
    </div>
  )
}
