# PRD: 用户登录与注册

## 概述
实现基于邮箱的用户注册和登录功能。

## 用户故事
- 作为新用户，我希望通过邮箱注册账号并设置用户名，以便拥有个性化身份
- 作为已注册用户，我希望通过邮箱和密码登录系统

---

## 功能需求

### 1. 注册

**输入字段：**
| 字段 | 类型 | 必填 | 校验规则 |
|------|------|------|----------|
| 用户名 | text | 是 | 2-20 字符，支持中英文、数字、下划线；不可与已有用户名重复 |
| 邮箱 | email | 是 | 合法邮箱格式；不可与已有邮箱重复 |
| 密码 | password | 是 | 8-32 字符，至少包含字母和数字 |
| 确认密码 | password | 是 | 必须与密码一致 |

**流程：**
1. 用户填写注册表单
2. 前端实时校验（格式、密码一致性）
3. 提交后端校验（邮箱/用户名唯一性）
4. 校验通过 -> 创建账号 -> 自动登录并跳转首页
5. 校验失败 -> 在对应字段下方显示错误提示

### 2. 登录

**输入字段：**
| 字段 | 类型 | 必填 | 校验规则 |
|------|------|------|----------|
| 邮箱 | email | 是 | 合法邮箱格式 |
| 密码 | password | 是 | 非空 |

**流程：**
1. 用户填写邮箱和密码
2. 提交后端验证
3. 成功 -> 返回 JWT token -> 跳转首页
4. 失败 -> 提示"邮箱或密码错误"（不区分具体原因，防止枚举）

---

## 页面清单

| 页面 | 路由 | 说明 |
|------|------|------|
| 登录页 | `/login` | 邮箱密码登录，含注册入口；支持 `state.from` 回跳 |
| 注册页 | `/register` | 邮箱注册，含登录入口 |

---

## API 清单

| 方法 | 路由 | 说明 |
|------|------|------|
| POST | `/api/v1/auth/register` | 用户注册 |
| POST | `/api/v1/auth/login` | 用户登录 |
| GET  | `/api/v1/auth/me` | 获取当前登录用户信息（需 Bearer Token） |
| GET  | `/api/v1/auth/check-username/:username` | 检查用户名是否可用 |
| GET  | `/api/v1/auth/check-email/:email` | 检查邮箱是否可用 |

### GET /auth/me
- Header：`Authorization: Bearer <token>`
- 成功：`{ code: 0, data: { id, username, email, role, created_at } }`
- token 缺失或无效：`{ code: 1001, message: "未登录" }`

---

## 访问控制

| 路由前缀 | 是否需要登录 | 未登录处理 |
|---------|-------------|-----------|
| `/ai-tools/*` | 是 | 跳转 `/login`，携带 `state.from` 记录原路由；登录成功后回跳原页面 |
| 其余页面（`/`, `/login`, `/register`, `/about`, `/gallery`, `/bookmarks`, `/404`, `/403` 等） | 否 | — |

**前端策略：**
- 用 `<ProtectedRoute>` 包裹 `/ai-tools` 整棵子路由树
- 未登录访问 → `<Navigate to="/login" state={{ from: location }} replace />`
- 登录页在 submit 成功后：`navigate(state.from?.pathname ?? '/', { replace: true })`

**Token 生命周期：**
- 应用启动时若 localStorage 存在 token，自动调用 `GET /auth/me`
  - 成功：刷新本地 user 缓存（保证 role 等字段与后端同步）
  - 失败（1001）：清空 token / user，视作未登录

---

## 用户菜单

**位置**：Navbar 右上（原 Sign In 按钮位置）。

**未登录状态**：显示 `Sign In` 按钮。

**已登录状态**：显示头像圆钮（`username` 首字母，`primary` 底 + 白字），点击展开下拉：

```
┌───────────────────────────┐
│  <username>               │  ← 粗体
│  <email>                  │  ← 小字灰
│  [role 徽章]              │  ← admin: accent 橙 / user: text-muted 灰边
├───────────────────────────┤
│  Logout                   │  ← error 色文字
└───────────────────────────┘
```

**交互**：
- 外部点击 / ESC 关闭
- Logout 点击：清空 token/user，跳转 `/login`

**移动端**：汉堡菜单里，已登录时用同样的信息块 + Logout 按钮替换底部 Sign In 按钮。

---

## 安全要求
- 密码使用 bcrypt 哈希存储，禁止明文
- 所有认证相关接口做频率限制（rate limiting）
- JWT token 有效期 24 小时，支持刷新

## 非功能需求
- 表单提交时显示 loading 状态，防止重复提交
- 所有校验错误实时显示在对应字段下方
- 页面间跳转流畅（登录 <-> 注册）
- 移动端适配
