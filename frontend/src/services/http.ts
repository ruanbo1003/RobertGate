// 全局未登录处理：业务 API 返回 code 1001(未登录/token 失效)时清会话并跳登录页。
//
// 设计(Robert 2026-11-24 拍板):
// - 只在"访问业务 API 且未登录"时跳转;不发请求的页面永不触发。
// - 不挂 auth.ts:登录接口输错密码同样返回 1001("邮箱或密码错误"),
//   由登录/注册页自行展示;AuthContext 的 getMe 兜底(logout 清幽灵用户)保留。
// - 整页跳转(window.location.assign)而非路由跳转:顺带重置全部内存态,
//   登录页读 ?redirect= 回跳原页面。

let redirecting = false

export function handleUnauthorized(): void {
  if (redirecting) return
  if (window.location.pathname === '/login') return
  redirecting = true
  localStorage.removeItem('token')
  localStorage.removeItem('user')
  const here = window.location.pathname + window.location.search
  window.location.assign(`/login?redirect=${encodeURIComponent(here)}`)
}

/** 包在业务 request 的 res.json() 外:1001 触发登录跳转,其余原样透传。 */
export function checkUnauthorized<T extends { code: number }>(body: T): T {
  if (body.code === 1001) handleUnauthorized()
  return body
}
