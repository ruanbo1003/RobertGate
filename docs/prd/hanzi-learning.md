# 汉字学习 PRD（Level 化重构 v2）

> 本文档取代 `docs/prd/ai-tools.md` 中 **B. 汉字学习** 章节。翻译 / 英文启蒙 / 文生图 部分保持不变。

## 概述

将汉字学习从「用户各自维护小字库」重构为「admin 定义分级字库 + 普通用户按级别学习」的教学产品。
- **Admin**：CRUD 分级字库（level 定义、字条录入），是内容生产者
- **User**：浏览级别 → 查看字表 → 逐字标记「已学 / 未学」，是内容消费者
- 旧的「从任意文本添加汉字」入口移除

## 目标用户

- **Admin**（站点所有者）：给孩子安排学习进度的家长；懂得哪些字对应哪个阶段
- **User**（家人 / 孩子）：跟着 admin 排好的级别顺序学；不需要自己想学什么字

## 使用场景

1. **Admin 备课**：新学期开始，家长登录后台，新建 `启蒙 · Level 1`（20 字），录入拼音和释义，保存
2. **Admin 迭代**：给已有级别增删字，或新建 `启蒙 · Level 2`（40 字）
3. **孩子学字**：孩子登录 → 汉字学习页看到可选级别 → 进入 Level 1 → 看到字表和进度「已学 3 / 20」→ 点击某字进入逐字学习页看笔顺/拼音/组词/例句 → 点「已学完」→ 回到字表看到绿勾
4. **孩子复习**：进入 Level 1 → 用「句子学习」让 AI 用本级已学的字组句朗读

## 功能需求

### P0（必须实现）

#### 权限模型
- [ ] `users.role` 字段：`user` | `admin`，注册默认 `user`
- [ ] admin 用户由后端脚本 / 直接改 DB 设置（本期无「设为管理员」UI）
- [ ] `admin` 拥有 `user` 全部能力 + 内容管理能力

#### A. Admin 端 · 内容管理（`/admin/hanzi`）

- [ ] A1. **级别列表页**
  - 列表展示所有 level（按 `order_index` 升序）：名称、描述、字数、创建时间
  - 顶部 [+ 新建级别] 按钮
  - 每行操作：[编辑] [删除]
  - 删除级别前若其下还有字，弹确认（会级联报错，需先清空字）
- [ ] A2. **级别编辑弹窗**
  - 字段：名称（必填）、描述（可选）、排序位（数字，默认自增末位）
  - 保存后回到列表
- [ ] A3. **字条列表页**（点击某级别进入）
  - 顶部面包屑：级别名 / 字条管理
  - 网格展示该级别所有字：大字 + 拼音，按 `order_index` 排序
  - 顶部操作：[+ 单条添加] [批量导入]
  - 单字卡片操作：[编辑] [删除]
- [ ] A4. **单条添加/编辑**
  - 字段：字（1 个汉字，必填）、拼音（必填）、释义（可选）、排序位
  - 提交前校验：`char` 全局不重复；已存在则给出该字所在级别信息
- [ ] A5. **批量导入**
  - textarea 粘贴：一行一条 `字 拼音 [释义]`（空格分隔）
  - 或 JSON 数组
  - 提交后返回 { 成功 X 条, 失败 Y 条（含各自原因，如「已在 Level 2」）}
- [ ] A6. **非 admin 访问 `/admin/*` 页面 → 403 引导页**

#### B. 用户端 · 汉字学习（`/ai-tools/hanzi/*`）

- [ ] B1. **级别列表页**（`/ai-tools/hanzi`）
  - 卡片网格：每张卡显示级别名 / 描述 / 进度条「已学 X / 总 Y」/ CTA「继续学习」
  - 按 `order_index` 升序
- [ ] B2. **字表页**（`/ai-tools/hanzi/levels/:levelId`）
  - 顶部面包屑：级别名 / 字表
  - 顶部进度：「已学 X / 总 Y」+ 进度条
  - 方块网格：每字显示大字 + 拼音；已学显示右上角绿勾；未学灰色
  - 点击方块进入逐字学习页
- [ ] B3. **逐字学习页**（`/ai-tools/hanzi/levels/:levelId/characters/:charId`）
  - 保留现有 UI（hanzi-writer 笔顺 + 拼音/组词/例句）
  - 组词/例句仍走 AI 动态生成（`/api/v1/ai/character-info`），不落库
  - 底部 [上一个] [跳过] [已学完 ✓] / [已学 → 标为未学]
  - 「已学完」→ POST progress → 自动跳到本级下一未学字；若全部学完展示完成 toast + 回字表
- [ ] B4. **句子学习页**（`/ai-tools/hanzi/levels/:levelId/sentence`）
  - 逻辑不变：AI 用本级**已学**字组句
  - 已学字 < 5 时提示「先在字表把字学起来」

#### C. 移除项
- [ ] C1. 删除「从文本添加汉字」入口（旧 `字库管理` 顶部 textarea）
- [ ] C2. 删除「用户单个删字」入口（字条归 admin 管）
- [ ] C3. 后端删除 `hanzi_entries` 表 + `add_from_text` / `delete` 接口

### P1（优先级次之）

- [ ] admin 端「设为管理员」UI（当前手动改 DB）
- [ ] admin 端「跨级别移动字条」
- [ ] 用户端「今日已学」「连续打卡」统计
- [ ] 字条上传 CSV / Excel 导入
- [ ] 拼音 AI 建议（admin 录入字时自动填拼音）
- [ ] 英文启蒙同构改造（另立 PRD）

## 页面布局

### Admin · 级别列表

```
面包屑：内容管理 / 汉字级别

┌───────────────────────────────────────── [+ 新建级别] ─┐
│                                                        │
│  ┌──────────────────────────────────────────────────┐  │
│  │ 启蒙 · Level 1        20 字   2026-01-01  [编辑][删]│  │
│  ├──────────────────────────────────────────────────┤  │
│  │ 启蒙 · Level 2        40 字   2026-02-15  [编辑][删]│  │
│  ├──────────────────────────────────────────────────┤  │
│  │ 进阶 · Level 3        80 字   2026-03-20  [编辑][删]│  │
│  └──────────────────────────────────────────────────┘  │
└────────────────────────────────────────────────────────┘
```

### Admin · 字条管理

```
面包屑：内容管理 / 汉字级别 / 启蒙 · Level 1

  [+ 单条添加]  [批量导入]

  ┌─────┐ ┌─────┐ ┌─────┐ ┌─────┐ ┌─────┐
  │ 人  │ │ 大  │ │ 天  │ │ 上  │ │ 下  │
  │ rén │ │ dà  │ │tiān │ │shàng│ │ xià │
  │[编][删]│[编][删]│[编][删]│[编][删]│[编][删]│
  └─────┘ └─────┘ └─────┘ └─────┘ └─────┘
```

### User · 级别列表（汉字学习首页）

```
页面标题：汉字学习
副标题：按级别循序渐进

┌─────────────────────────────┐  ┌─────────────────────────────┐
│ 启蒙 · Level 1              │  │ 启蒙 · Level 2              │
│ 最基础的常用字               │  │ 巩固扩展                     │
│                              │  │                              │
│ [====        ]  已学 8 / 20 │  │ [                ]  0 / 40   │
│                              │  │                              │
│         [继续学习 →]        │  │        [开始学习 →]         │
└─────────────────────────────┘  └─────────────────────────────┘
```

### User · 字表页（保留旧网格风格）

```
面包屑：汉字学习 / 启蒙 · Level 1

进度：已学 8 / 20     [====        ]

┌───┐┌───┐┌───┐┌───┐┌───┐┌───┐
│人✓││大✓││天 ││上✓││下 ││小 │
│rén││dà ││...││...││...││xiǎo│
└───┘└───┘└───┘└───┘└───┘└───┘
...
```

### User · 逐字 / 句子学习

保持现有 `ai-tools.md` 中的布局。

## 组件规划

| 组件名 | 类型 | 说明 | 是否已有 |
|--------|------|------|---------|
| `AdminGuard` | 新建 | 路由级 admin 守卫，非 admin 跳 403 | 否 |
| `AdminLayout` | 新建 | admin 页面骨架（沿用 Sidebar 但只显示管理菜单） | 否 |
| `LevelListPage` (admin) | 新建 | 级别列表 | 否 |
| `LevelEditModal` | 新建 | 新建 / 编辑级别弹窗 | 否 |
| `CharacterListPage` (admin) | 新建 | 字条网格 + CRUD | 否 |
| `CharacterEditModal` | 新建 | 新建 / 编辑字条弹窗 | 否 |
| `CharacterBatchImportModal` | 新建 | 批量导入弹窗 | 否 |
| `UserLevelListPage` | 新建 | 用户级别卡片列表 | 否（改造现字库管理页） |
| `UserCharacterGridPage` | 新建 | 用户字表网格 | 否（改造现字库管理页） |
| `HanziLearnPage` | 改造 | 移除自加字入口；改按 `characterId` 路由 | 是 |
| `HanziSentencePage` | 改造 | 按级别范围取已学字 | 是 |
| `ProgressBar` | 共享 | 通用进度条 | 待确认 |

## 交互设计

### Admin

- **新建级别**：`order_index` 默认取当前最大值 + 1；重名给红色 inline 错误
- **删除级别**：如果级别下还有字，弹「请先清空本级别字条」不允许删；无字直接删
- **添加字条**：`char` 只允许 1 个汉字（正则 `^[\u4e00-\u9fa5]$`）；已在其他级别弹「该字已在 xxx，请先移除」
- **批量导入**：单条失败不阻断其他条；结果弹窗展示成功/失败明细
- **admin 端使用现有 sidebar**：在底部新增「内容管理」入口，仅 admin 可见

### User

- **点方块进入逐字学习**：URL 携带 `levelId` + `characterId`，逐字页可用来做本级内跳转
- **已学切换**：点「已学完 ✓」→ 请求 progress → 立即更新前端状态 → 400ms 后跳下一字；请求失败回滚 UI
- **切换到未学**：字表页支持长按 / 右键切回未学（P1 可先只在逐字页支持）
- **进度条动画**：`ease-out 300ms`；从旧比例过渡到新比例
- **完成一级**：字表页 100% 时弹一次庆祝 toast（当次会话内只弹一次）

### 动效
沿用 `.claude/rules/ui-style.md` 规范。

## 边界情况

| 情况 | 处理方式 |
|------|---------|
| 用户未登录访问汉字学习 | 匿名可看级别列表和字表；点「已学完」触发登录 modal |
| 用户已登录但没有 admin 建过任何级别 | 级别列表空状态：「暂无学习内容，请联系管理员」 |
| admin 删除某级别时该级别有字 | 弹确认框：「本级别下还有 X 字，需先清空」，禁止删除 |
| 用户已学的字被 admin 从库中删除 | 级联删除该用户的进度（DB `ON DELETE CASCADE`）；用户回到字表看不到该字 |
| admin 把字从 Level 1 移到 Level 2（P1 功能） | 已学进度保留（关联的是 `character_id`） |
| 非 admin 直接访问 `/admin/*` URL | 后端 403；前端在 `AdminGuard` 层显示「无权访问，请联系管理员」 |
| 逐字学习进入时字表为空 | 空状态：「该级别还没有字」+ 返回按钮 |
| 句子学习本级已学字 < 5 | 提示「先把本级几个字学起来再来组句」 |

## 设计约束

引用 `.claude/rules/ui-style.md`（完整规范见文件）：
- 颜色：只用 Tailwind token
- 字体：Plus Jakarta Sans
- 圆角 16px、按钮 44px、shadow-sm + shadow-[0_8px_32px_rgba(0,0,0,0.08)]
- 空 / 加载 / 错误状态齐全

Admin 页面与 user 页面共用视觉规范，区分在于 admin 页 sidebar 高亮 `内容管理` 菜单。

## 技术备注

### 后端接口（详见 `docs/api/hanzi-learning.md`，Step 3 生成）

**用户端**
| 方法 | 路径 | 说明 |
|---|---|---|
| GET | `/api/v1/hanzi/levels` | 级别列表 + 每级 `total / learned`（登录时含 learned） |
| GET | `/api/v1/hanzi/levels/:levelId/characters` | 字表 + 每字 `learned` 状态 |
| PUT | `/api/v1/hanzi/progress/:characterId` | 标记已学/未学（body `{ learned: bool }`） |
| POST | `/api/v1/ai/character-info` | 单字 AI 详情（保留） |
| POST | `/api/v1/ai/sentence` | 已学字组句（保留，参数改用 `levelId` 或 char 列表） |

**admin 端**（全部要求 `role=admin`）
| 方法 | 路径 | 说明 |
|---|---|---|
| GET | `/api/v1/admin/hanzi/levels` | 级别列表（含字数） |
| POST | `/api/v1/admin/hanzi/levels` | 新建级别 |
| PUT | `/api/v1/admin/hanzi/levels/:id` | 编辑级别 |
| DELETE | `/api/v1/admin/hanzi/levels/:id` | 删除级别（有字禁止） |
| GET | `/api/v1/admin/hanzi/levels/:levelId/characters` | 字条列表 |
| POST | `/api/v1/admin/hanzi/levels/:levelId/characters` | 新建字条（单条 or 批量） |
| PUT | `/api/v1/admin/hanzi/characters/:id` | 编辑字条 |
| DELETE | `/api/v1/admin/hanzi/characters/:id` | 删除字条（级联删用户进度） |

**移除**：`GET/POST/PATCH/DELETE /api/v1/hanzi/library`、`add_from_text`

### 数据存储

DB schema 由已批准的 plan 文件承载（`/Users/ruanbo/.claude/plans/greedy-stargazing-beaver.md`）：
- `users` +`role`
- `hanzi_levels` / `hanzi_characters` / `hanzi_user_progress` 三张新表
- drop `hanzi_entries`

### 路由结构

```
/admin/hanzi/levels                     # admin 级别列表
/admin/hanzi/levels/:levelId/characters # admin 字条管理
/ai-tools/hanzi                         # user 级别列表（改造原字库管理）
/ai-tools/hanzi/levels/:levelId         # user 字表页
/ai-tools/hanzi/levels/:levelId/characters/:charId  # 逐字学习
/ai-tools/hanzi/levels/:levelId/sentence            # 句子学习
```

## 验收标准

- Admin 登录 → 内容管理菜单可见 → 建 level → 加字 → 用户端立即看到
- 普通用户登录 → 内容管理菜单不可见；访问 `/admin/*` URL 得 403
- 用户在 Level 1 打勾 → 刷新后仍为已学 → 进度条更新
- 用户在 Level 1 打勾的字不影响 Level 2 的进度
- Admin 删除已被学过的字 → 用户端进度记录同步消失（CASCADE）
- 旧的「从文本添加汉字」入口和接口完全不再存在
