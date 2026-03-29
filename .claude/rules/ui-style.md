# UI 风格规范

本项目所有页面必须遵循以下设计规范，确保视觉一致性。

## 风格定位

Flat Design + 轻微阴影，干净专业的 SaaS 风格，无重度装饰，字体驱动层次感。

## 配色

| Token | 色值 | 用途 |
|-------|------|------|
| `primary` | `#2563EB` | 按钮、链接、focus 状态、Logo 高亮 |
| `primary-hover` | `#1D4ED8` | 按钮悬停 |
| `accent` | `#EA580C` | CTA 强调、警告图标 |
| `bg` | `#F8FAFC` | 页面底色 |
| `card` | `#FFFFFF` | 卡片表面 |
| `brand-panel` | 中等深度蓝灰（非深 navy） | 左侧品牌面板 |
| `text-primary` | `#1E293B` | 标题、正文 |
| `text-muted` | `#64748B` | 副文案、placeholder |
| `border` | `#E2E8F0` | 输入框边框、分隔线 |
| `error` | `#DC2626` | 校验错误 |
| `success` | `#16A34A` | 检查通过 |

**禁止硬编码颜色值。** 所有颜色必须通过 Tailwind config 中定义的 token 引用。

## 字体

统一使用 **Plus Jakarta Sans**。

| 场景 | 大小 | 字重 | 备注 |
|------|------|------|------|
| 页面标题 | 24px | bold | tracking-tight |
| 副标题 | 14px | regular | text-muted |
| 表单 label | 13px | semibold | |
| 输入框 | 16px | regular | |
| 按钮 | 14px | semibold | |

## 布局

- Split-screen card 布局：左 40% 品牌面板 + 右 60% 内容区
- 卡片最大宽度 `1000px`，桌面固定高度 `660px`，移动端自适应
- 卡片圆角 `16px`
- 卡片阴影：`shadow-sm` + `shadow-[0_8px_32px_rgba(0,0,0,0.08)]`
- 背景纹理：48px 网格线，opacity 0.4
- 页面内容居中，使用 `min-h-screen flex items-center justify-center`

## 交互

- 按钮高度 `44px`（touch target 标准），hover `scale-[1.01]`
- 输入框 focus：蓝色 ring；错误状态：红色 ring
- 动效时长 `150ms ~ 400ms`，缓动函数 `ease-out`
- 表单防抖校验延迟 `500ms`，附带 loading spinner
- 状态反馈使用图标 + 颜色（绿色对勾 = 通过，红色 = 错误）

## 组件复用

新建页面时：
1. 优先复用 `src/components/` 下已有的共享组件
2. 保持与 Login / Register / 404 / Not Implemented 页面一致的视觉风格
3. 新组件必须遵循以上 token，不得引入新的颜色或字体

## 禁止事项

- ❌ 不得硬编码 hex 颜色，必须使用 Tailwind token
- ❌ 不得引入 Plus Jakarta Sans 以外的字体
- ❌ 不得使用与上述阴影/圆角不一致的卡片样式
- ❌ 不得跳过空状态、加载态、错误态的设计
