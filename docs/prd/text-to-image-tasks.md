# 文生图任务化 (text-to-image-tasks) PRD

## 概述

将现有 `/ai-tools/text-to-image` 页面从"单次生成即忘"改造为**基于模板的任务管理系统**：把提示词按业务场景固化成模板（英文启蒙 / 常规两类），每一组关键字对应一个可持续追踪的"生成任务"，任务下可重试累积多张图，用户可对图片进行标可用/删除等生命周期管理。

## 目标用户

- **用户画像**：站点管理员（本人 / 家长），需要为其他功能（如英文启蒙游戏）预生成大量素材图，或个人创作留存
- **核心诉求**：
  - 让「单词 → 生图」这件事可以稳定地反复重试，直到出到满意为止
  - 让筛选后的图能被下游功能（英文启蒙 quiz）直接消费
  - 未采用的图能一键清掉，采用的图不被误删

## 使用场景

1. 给英文启蒙添加新单词 `apple`：进入「英文启蒙」模板 → 新建任务 `apple` → 反复点"再生成"直到某几张满意 → 标记为可用 → 前台游戏立即能选到这些图。
2. 家长为孩子做识字卡：进入「常规」模板 → 填 subject=`一只戴帽子的小狐狸` / style=`扁平插画` / extra=`白底` → 生成 → 满意的标可用，其他删掉，任务保留供以后再回来补图。
3. 翻旧任务：进入「英文启蒙」的分页任务列表，看到旧的 `dog` 任务只有 1 张可用图，点进去再生几张补齐。

## 功能需求

### P0（必须实现）

#### A. 模板与二级菜单
- [ ] A1. Sidebar 里「🎨 文生图」下新增二级菜单：**英文启蒙** / **常规** / **测试**
- [ ] A2. 原极简文生图页保留在 `/ai-tools/text-to-image/playground`（二级菜单"测试"），用于开发调试与 AI 客户端联调，不参与任务管理
- [ ] A3. 访问 `/ai-tools/text-to-image` 默认重定向到 `/ai-tools/text-to-image/english-primer`
- [ ] A4. 模板硬编码在后端，前端拉列表展示，不做用户自定义模板

#### B. 任务列表页（每个模板一个）
- [ ] B1. 页面顶部：模板名 + 该模板简介 + [+ 新建任务] 按钮（**仅 admin 可见**）
- [ ] B2. 任务卡片瀑布网格（3 列，参考 gallery 的 masonry），每卡片显示：
  - 关键字摘要（如 `apple` 或 `一只小狐狸 · 扁平插画`）
  - 业务状态徽章：`完成` / `未完成`
  - 右上角：生成中时显示 spinner；失败时显示 `error` 色小警告图标
  - 缩略图轮播（最多 4 张，多的显示 `+N`）
  - "可用" 计数（`3/8` 表示 8 张里 3 张已标可用）
- [ ] B3. 分页：每页 20 个任务，按更新时间倒序
- [ ] B4. 空状态：无任务时，中间显示"还没有任务，点右上角新建"
- [ ] B5. 卡片点击 → 进入任务详情

#### C. 新建任务弹窗
- [ ] C1. 「英文启蒙」模板：单字段 `word`（必填，英文，1-30 字符）
- [ ] C2. 「常规」模板：三字段
  - `subject`（必填，主题描述）
  - `style`（可选，风格，如"扁平插画"、"水彩"）
  - `extra`（可选，附加描述）
- [ ] C3. 提交后立刻创建任务并触发第一次生成（异步），弹窗关闭回到列表，任务卡片显示"生成中"
- [ ] C4. 同一模板下不允许重复的关键字组合（后端幂等），命中已有任务时 toast 提示"任务已存在，已为你打开"并跳转到详情

#### D. 任务详情页
- [ ] D1. 顶部：面包屑（文生图 / 模板 / 任务）+ 关键字回显 + 业务状态徽章 + [🔁 再生成] 按钮（**仅 admin 可见**）
- [ ] D2. 中部：图片网格，每张图带：
  - 状态角标（`✓ 可用` / 无角标）
  - 悬停操作（**匿名/user 只显示 👁 放大；admin 三个都显示**）：
    - [👁 放大] 所有人可见
    - [★ 标记可用/取消] 仅 admin
    - [🗑 删除] 仅 admin
- [ ] D3. 图片按创建时间倒序，最新在前
- [ ] D4. 单击图片打开 Lightbox（复用 gallery 的 Lightbox 组件），键盘 ← → 切换
- [ ] D5. 「再生成」按钮：状态为"生成中"时禁用；产生新一张异步生图，完成后前置到列表；失败在图片位置显示"失败，可再试"占位
- [ ] D6. 已标记可用的图 [🗑 删除] 按钮置灰不可点，hover tooltip："取消可用后才能删除"
- [ ] D7. 底部：任务元信息（创建时间、总图片数、可用数、失败次数）

#### E. 状态语义
- [ ] E1. **任务底层状态**（数据库字段，用于内部逻辑，不直接在徽章展示）：
  - `generating`：至少一次生图请求正在跑
  - `succeeded`：最近一次生成成功（有至少一张图）
  - `failed`：最近一次生成失败
- [ ] E2. **卡片徽章只显示业务状态**：
  - `完成`：任务下已有 ≥1 张标为可用的图
  - `未完成`：尚无标可用的图
- [ ] E3. **技术状态用其他视觉线索表达**（不占徽章位）：
  - `generating`：卡片右上角一个小 spinner + 缩略图位半透明 skeleton
  - `failed`：最近一次生成失败时，卡片底部一行 `error` 色小字："上次生成失败，可再试"（不覆盖徽章）

#### F. 图片可用性管理
- [ ] F1. 图片有 `available` 布尔字段
- [ ] F2. 「英文启蒙」模板下 `available=true` 的图会**自动进入** `/api/v1/english/quiz` 的候选池（后续联动，另建 issue，本次仅打通字段）
- [ ] F3. 「常规」模板下 `available=true` 仅保护不被删除，不参与其他业务
- [ ] F4. `available=true` → 删除按钮禁用；用户必须先取消可用再删

### P1（优先级次之）
- [ ] 批量操作：任务详情页多选图 → 批量删/批量标可用
- [ ] 任务复制：以某任务的关键字为初始值新建
- [ ] 生成进度实时推送（SSE 或轮询降级）
- [ ] 英文启蒙可用图 → quiz 自动使用（需修改 quiz 后端）
- [ ] 权限：区分家长/管理员

## 页面布局

### 二级菜单变动（对照现有 ai-tools sidebar）
```
🎨 文生图 ▼
   英文启蒙
   常规
```

### 任务列表页
```
面包屑：文生图 / 英文启蒙

┌────────────────────────────────────────┐
│ 英文启蒙                    [+ 新建任务]│
│ 给英文单词批量生成配图                    │
└────────────────────────────────────────┘

┌────────┐  ┌────────┐  ┌────────┐
│ apple  │  │ dog    │  │ shape  │
│ ●完成   │  │生成中… │  │ ●未完成 │
│ [图][图]│  │ [占位]  │  │ [图]   │
│ +2      │  │        │  │        │
│ 可用 3/5│  │        │  │ 可用 0/1│
└────────┘  └────────┘  └────────┘

    ← 1  2  3  →
```

### 任务详情页
```
面包屑：文生图 / 英文启蒙 / apple

关键字：apple                状态：●完成      [🔁 再生成]

┌────┐ ┌────┐ ┌────┐ ┌────┐
│图 ✓│ │图  │ │图 ✓│ │图  │
└────┘ └────┘ └────┘ └────┘
┌────┐ ┌────┐ ┌────┐ ┌────┐
│图 ✓│ │失败│ │图  │ │图  │
└────┘ └────┘ └────┘ └────┘

创建于 2026-08-10 · 共 8 张 · 可用 3 · 失败 1
```

### 新建任务弹窗（常规模板示例）
```
┌────── 新建任务 · 常规 ────────────┐
│                                   │
│  主题 *                            │
│  [ 一只戴帽子的小狐狸           ] │
│                                   │
│  风格                              │
│  [ 扁平插画                    ]  │
│                                   │
│  附加描述                          │
│  [ 白底,可爱                   ]  │
│                                   │
│           [取消]    [创建]         │
└───────────────────────────────────┘
```

## 组件规划

| 组件名 | 类型 | 说明 | 是否已有 |
|---|---|---|---|
| `Text2ImageLayoutPage` | 页面 | 二级菜单容器（旧 Text2ImagePage 拆分） | 否 |
| `T2ITaskListPage` | 页面 | 任务列表 + 分页 + 新建入口 | 否 |
| `T2ITaskDetailPage` | 页面 | 任务详情，图片网格 + 操作 | 否 |
| `T2ITaskCard` | 组件 | 列表用卡片 | 否 |
| `T2ITaskCreateModal` | 组件 | 新建任务弹窗，支持两种模板字段 | 否 |
| `T2IImageTile` | 组件 | 详情页图片格，含可用/删除/放大操作 | 否 |
| `StatusBadge` | 组件 | 生成中/完成/失败/未完成通用状态徽章 | 否 |
| `Lightbox` | 共享 | 已在 gallery 有，复用 | 是 |
| `Pagination` | 共享 | 上下页 + 页码 | 待确认 |
| `ConfirmDialog` | 共享 | 删除确认（可用图取消可用不弹） | 待确认 |

## 交互设计

- **新建任务后立即触发首次生成**：不等用户第二步操作，减少路径
- **生成中的乐观反馈**：卡片/图片位显示 skeleton + "生成中" 徽章；后端完成后 UI 通过轮询更新（P1 换 SSE）
- **失败态可点击重试**：失败图占位保留在网格里 24 小时便于调试；到期自动清理（后端 cron 或懒清）
- **删除按钮的两态**：`available` 时置灰 + tooltip；非 `available` 时红色 hover
- **重复关键字幂等**：同一模板下相同关键字命中已存任务，不新建；返回已有 task_id + 提示信息
- **英文启蒙 word 归一**：后端存储时统一小写去空格，避免 `Apple`/`apple` 重复

## 边界情况

| 情况 | 处理方式 |
|---|---|
| AI 服务失败 | 该次生成记为 `failed`，任务下产生一条 failed 记录（不产图），可再试 |
| 生成超时（如 > 60s） | 后端记 `failed`，前端超时兜底显示"生成失败" |
| 未登录访问 | 弹登录 modal，登录后继续（同 ai-tools 现有策略） |
| 图片删除时正在被 quiz 使用 | 数据库外键约束或后端逻辑校验，禁止直接硬删可用图；本 PRD 已通过 `available` 字段防呆 |
| 数据库 blob 越来越大 | 见"技术备注 → 图片存储"，分表 + 缓存策略 |
| 分页参数越界 | 后端返回空列表 + total，前端跳回第 1 页 |
| 关键字过长 | 前端限制字段最大长度，超长切割显示 tooltip 全文 |

## 设计约束

引用 `.claude/rules/ui-style.md`：
- 配色仅用 token（`primary`/`accent`/`bg`/`card`/`text-primary`/`text-muted`/`border`/`success`/`error`）
- 卡片圆角 16px，图片格 8px（视觉层次）
- 状态徽章：
  - `generating` → `text-muted` 底 + spinner
  - `succeeded/完成` → `success` 底 8% 透明 + 文字 `success`
  - `failed` → `error` 底 8% 透明 + 文字 `error`
  - `未完成` → `border` 底 + 文字 `text-muted`

## 技术备注

### 后端接口（**Step 3 详细定义**，此处仅列骨架）
| 方法 | 路径 | 说明 |
|---|---|---|
| GET | `/api/v1/ai/t2i/templates` | 列表模板（写死两条：english-primer / general） |
| GET | `/api/v1/ai/t2i/templates/:code/tasks?page=&page_size=` | 分页列任务 |
| POST | `/api/v1/ai/t2i/templates/:code/tasks` | 新建任务（幂等，body: 关键字字段） |
| GET | `/api/v1/ai/t2i/tasks/:id` | 任务详情（含图片列表） |
| POST | `/api/v1/ai/t2i/tasks/:id/retry` | 再生成一张 |
| GET | `/api/v1/ai/t2i/images/:id` | 下发图片二进制流 |
| PATCH | `/api/v1/ai/t2i/images/:id` | body: `{available: true/false}` |
| DELETE | `/api/v1/ai/t2i/images/:id` | 删除图片，`available=true` 时返回 4xx |

### 数据模型
```
t2i_template (硬编码，可只作枚举，不落表)
  code: str  # english-primer / general
  name: str
  prompt_template: str  # 含占位符 {word} 或 {subject}/{style}/{extra}
  fields: list[FieldDef]

t2i_task
  id: uuid
  template_code: str
  keywords: jsonb  # 例：{"word":"apple"} 或 {"subject":"...","style":"...","extra":"..."}
  status: enum[generating|succeeded|failed]
  keywords_hash: str  # (template_code, keywords) 的稳定 hash，唯一索引，实现幂等
  created_at, updated_at

t2i_image
  id: uuid
  task_id: uuid (fk)
  status: enum[generating|succeeded|failed]
  available: bool default false
  mime: str
  created_at
  -- blob 拆到子表避免列表查询把大字段拉出来

t2i_image_blob
  image_id: uuid (fk pk)
  bytes: bytea
```

### 图片存储
- 主存储：`t2i_image_blob.bytes`（Postgres `bytea`）
- 列表接口**永远不返回** blob，只返回 `GET /images/:id` 的 URL；前端 `<img src="/api/v1/ai/t2i/images/:id">`
- 大小上限：单图 < 5MB，前端 lazy load + IntersectionObserver
- 未来若磁盘更划算，改为写文件 + 存 `path`，接口保持不变

### 提示词拼接（后端）
- `english-primer`: `"A cute flat cartoon illustration of a {word}, simple design, kids education style, plain white background, no text."`
- `general`: `"{subject}, style: {style}, {extra}."`（缺失字段自动省略段）
- 前端只提交结构化字段，后端拼 prompt 后调 `AIClient.generate_image`

### AI 客户端
- 复用 `app.service.ai_client.AIClient.generate_image`
- 若接了新的图片生成 API（如 DALL-E / SD / 阶跃 / 智谱），在 `ai_client` 层封装，router 不感知
- MockAIClient 保留占位图 URL 兜底，方便本地开发

### 路由结构
```
/ai-tools/text-to-image                      → redirect to english-primer
/ai-tools/text-to-image/english-primer       任务列表
/ai-tools/text-to-image/english-primer/:id   任务详情
/ai-tools/text-to-image/general              任务列表
/ai-tools/text-to-image/general/:id          任务详情
/ai-tools/text-to-image/playground           旧的极简一次性生成页（测试用）
```

### 权限
- **匿名/未登录**：可访问任务列表页 + 任务详情页（只读），可放大查看图，不可新建/重试/删除/标可用
- **登录 user 角色**：同匿名，只读
- **登录 admin 角色**：可新建任务、重试生成、标可用/取消可用、删除图片
- 前端根据 `useAuth().user.role === 'admin'` 控制按钮显隐；后端接口再做一层 role 校验，未授权返回 `1002`

## 决策记录

1. 徽章只显示业务状态 `完成`/`未完成`；生成中/失败通过 spinner + inline 小字文案表达
2. 旧极简页保留为 `/ai-tools/text-to-image/playground`（二级菜单"测试"），供调试
3. 权限分层：匿名 + user 只读；admin 可新建/重试/标可用/删除
4. 图片删除采用**硬删除**：直接 `DELETE` 掉 `t2i_image` 与 `t2i_image_blob` 记录，`available=true` 时后端返回错误禁止删除
