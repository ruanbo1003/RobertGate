# 首页 PRD

## 概述
RobertGate 的公开首页，向访客介绍产品定位（开发者工具集 + 网站收藏），提供核心功能入口和登录注册入口。

## 目标用户
- 开发者、技术爱好者
- 核心诉求：快速了解 RobertGate 是什么，直接进入感兴趣的功能模块

## 使用场景
1. 新访客首次打开网站，了解产品后注册或直接使用公开功能
2. 老用户未登录状态下，通过首页进入 AI Tools 或收藏导航
3. 已登录用户访问首页，直接跳转 dashboard

## 功能需求

### P0（必须实现）
- [ ] 顶部导航栏：Logo + AI Tools / 导航收藏 / 个人简介 链接 + Sign In 按钮
- [ ] 移动端导航栏：Logo + 汉堡菜单（收起三个功能链接 + Sign In）
- [ ] Hero 区域：大标题 + 副标题（一句话介绍）+ Sign In / Register 两个 CTA 按钮
- [ ] 功能卡片区：三列卡片（AI Tools、导航收藏、个人简介），每个含图标 + 标题 + 描述，点击跳转对应路由
- [ ] Footer：版权信息 + GitHub 链接
- [ ] 登录状态分流：已登录用户访问 `/` 直接跳转 `/dashboard`

### P1（优先级次之）
- [ ] 技术栈/特色展示区域：体现开发者调性
- [ ] 导航栏已登录状态：Sign In 按钮替换为头像/用户名

## 页面布局

采用经典垂直流布局（方案 A）：

```
┌──────────────────────────────────────┐
│  Navbar（sticky）                      │
│  Logo | AI Tools | 导航 | 简介 | [Sign In] │
├──────────────────────────────────────┤
│  Hero                                 │
│  大标题：RobertGate                    │
│  副标题：开发者工具集 & 网站收藏        │
│  [Sign In]  [Register]               │
├──────────────────────────────────────┤
│  Features（三列等宽卡片）              │
│  ┌──────┐  ┌──────┐  ┌──────┐       │
│  │AI Tools│  │ 导航  │  │ 简介  │     │
│  └──────┘  └──────┘  └──────┘       │
├──────────────────────────────────────┤
│  Footer                              │
│  © 2026 RobertGate · GitHub          │
└──────────────────────────────────────┘
```

移动端：卡片堆叠为单列，Navbar 使用汉堡菜单。

## 组件规划

| 组件名 | 类型 | 说明 | 是否已有 |
|--------|------|------|---------|
| Navbar | 新建 | 顶部导航，含 logo、链接、CTA、汉堡菜单 | 否 |
| HeroSection | 新建 | 大标题 + 副标题 + 双按钮 | 否 |
| FeatureCard | 新建 | 图标 + 标题 + 描述，可点击跳转 | 否 |
| Footer | 新建 | 版权 + 外链 | 否 |
| Button | 共享 | 复用现有主按钮组件 | 是 |

## 交互设计

- **页面加载**：Navbar 即时显示，Hero 和卡片 stagger 进入（framer-motion，延迟 100-200ms 递增）
- **Navbar**：sticky 固定顶部，滚动时保持可见
- **功能卡片 hover**：轻微上浮 + 阴影加深（transition 150ms）
- **CTA 按钮**：Sign In 主按钮（蓝色实心），Register 次按钮（边框样式）
- **汉堡菜单**：点击展开/收起，带滑入动画

## 边界情况

- 已登录用户访问 `/`：直接跳转 `/dashboard`（dashboard 未实现前跳 `/not-implemented`）
- AI Tools / 导航收藏 / 个人简介未实现：各自独立路由占位（`/ai-tools`、`/bookmarks`、`/about`），暂时显示 Not Implemented 页面
- 移动端横屏：卡片保持单列，不做特殊处理

## 设计约束

沿用现有设计系统（`src/styles/design-tokens.css`）：
- 字体：Plus Jakarta Sans
- 主色：#2563EB（蓝）
- CTA 强调色：#EA580C（橙，可用于 Register 按钮 hover 或卡片图标）
- 背景：#F8FAFC + 网格线纹理
- 卡片：白色圆角 16px + shadow-md
- 间距：8px 递增体系

## 技术备注

### 路由
| 路由 | 页面 | 说明 |
|------|------|------|
| `/` | HomePage | 未登录显示 landing，已登录跳 dashboard |
| `/dashboard` | DashboardPage | 暂时跳 not-implemented |
| `/ai-tools` | AIToolsPage | 占位 |
| `/bookmarks` | BookmarksPage | 占位 |
| `/about` | AboutPage | 占位 |

### 接口依赖
- 无新接口，仅依赖 AuthContext 判断登录状态
