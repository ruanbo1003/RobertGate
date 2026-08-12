# API: 文生图任务化 (text-to-image-tasks)

基础路径：`/api/v1`

对应 PRD：`docs/prd/text-to-image-tasks.md`

## 认证约定

| 操作 | 认证 |
|------|------|
| 读接口（列模板 / 列任务 / 任务详情 / 图片二进制） | 匿名可用 |
| 写接口（新建任务 / 重试 / 标可用 / 删除） | 需登录 + `role=admin` |

未登录访问写接口 → `1001, "未登录"`；已登录但非 admin → `1002, "无权限"`。

## 统一响应

沿用项目约定（`.claude/rules/api.md`），成功 `code=0`，失败 `code≠0`。图片二进制接口除外（直接返回二进制流）。

---

## 一、模板

### 1.1 列出模板

**GET** `/api/v1/ai/t2i/templates`

匿名可用。返回硬编码模板列表，供前端渲染二级菜单和新建任务表单。

#### 响应

```json
{
  "code": 0,
  "data": {
    "templates": [
      {
        "code": "english-primer",
        "name": "英文启蒙",
        "description": "给英文单词批量生成配图",
        "fields": [
          { "key": "word", "label": "单词", "required": true, "max_length": 30, "placeholder": "apple" }
        ]
      },
      {
        "code": "general",
        "name": "常规",
        "description": "自由文生图，用于素材保存",
        "fields": [
          { "key": "subject", "label": "主题", "required": true, "max_length": 200, "placeholder": "一只戴帽子的小狐狸" },
          { "key": "style",   "label": "风格", "required": false, "max_length": 60,  "placeholder": "扁平插画" },
          { "key": "extra",   "label": "附加描述", "required": false, "max_length": 200, "placeholder": "白底" }
        ]
      }
    ]
  },
  "message": "ok"
}
```

---

## 二、任务

### 2.1 分页列任务

**GET** `/api/v1/ai/t2i/templates/{code}/tasks`

匿名可用。按 `updated_at DESC` 分页。

#### Query

| 名称 | 类型 | 默认 | 说明 |
|------|------|------|------|
| `page` | int | 1 | 页码，从 1 开始 |
| `page_size` | int | 20 | 1-50 |

#### 响应

```json
{
  "code": 0,
  "data": {
    "template": { "code": "english-primer", "name": "英文启蒙" },
    "page": 1,
    "page_size": 20,
    "total": 42,
    "items": [
      {
        "id": "b7b9-...-uuid",
        "template_code": "english-primer",
        "keywords": { "word": "apple" },
        "summary": "apple",
        "status": "succeeded",
        "business_status": "done",
        "images_total": 8,
        "images_available": 3,
        "last_failed": false,
        "thumbnails": [
          "/api/v1/ai/t2i/images/img-1",
          "/api/v1/ai/t2i/images/img-2",
          "/api/v1/ai/t2i/images/img-3",
          "/api/v1/ai/t2i/images/img-4"
        ],
        "created_at": "2026-08-10T08:00:00Z",
        "updated_at": "2026-08-10T08:10:00Z"
      }
    ]
  },
  "message": "ok"
}
```

字段说明：
- `status`：底层技术状态，取值 `generating` / `succeeded` / `failed`。
- `business_status`：卡片徽章用，取值 `done`（已有可用图）/ `pending`（暂无可用图）。
- `summary`：由后端拼接的关键字摘要（英文启蒙=`word`；常规=`subject · style`）。
- `thumbnails`：最多返回前 4 张成功图的下载 URL；缩略图接口和原图接口共用同一 URL（前端 `<img>` 直接引用即可）。
- `last_failed`：最近一次重试失败，卡片底部提示"上次失败"。

#### 错误

| code | message |
|------|---------|
| 2020 | template_code 不存在 |
| 2021 | page/page_size 参数非法 |

---

### 2.2 新建任务（幂等）

**POST** `/api/v1/ai/t2i/templates/{code}/tasks`

**需 admin**。创建任务并异步触发第一次生成。同 `(template_code, keywords)` 命中已存任务时不新建，返回 `existing=true` + 现有任务。

#### 请求体（英文启蒙）

```json
{
  "word": "apple"
}
```

#### 请求体（常规）

```json
{
  "subject": "一只戴帽子的小狐狸",
  "style": "扁平插画",
  "extra": "白底"
}
```

#### 响应（新建）

```json
{
  "code": 0,
  "data": {
    "existing": false,
    "task": {
      "id": "task-uuid",
      "template_code": "english-primer",
      "keywords": { "word": "apple" },
      "summary": "apple",
      "status": "generating",
      "business_status": "pending",
      "images_total": 0,
      "images_available": 0,
      "last_failed": false,
      "created_at": "2026-08-10T08:00:00Z",
      "updated_at": "2026-08-10T08:00:00Z"
    }
  },
  "message": "ok"
}
```

#### 响应（幂等命中）

同上，`existing=true`，`task` 是现有任务的当前快照，前端应 toast 提示"任务已存在，已为你打开"并跳转详情。

#### 错误

| code | message |
|------|---------|
| 1001 | 未登录 |
| 1002 | 无权限 |
| 2020 | template_code 不存在 |
| 2022 | 关键字校验失败（具体字段错误） |

关键字校验：
- `english-primer.word`：必填，`^[a-zA-Z][a-zA-Z\-'\s]{0,29}$`，服务端归一化为 lowercase + trim。
- `general.subject`：必填，1-200 字符。
- `general.style` / `general.extra`：可选，≤ 60 / 200 字符。

---

### 2.3 任务详情

**GET** `/api/v1/ai/t2i/tasks/{id}`

匿名可用。含全部图片列表（按 `created_at DESC`）。

#### 响应

```json
{
  "code": 0,
  "data": {
    "task": {
      "id": "task-uuid",
      "template_code": "english-primer",
      "keywords": { "word": "apple" },
      "summary": "apple",
      "status": "succeeded",
      "business_status": "done",
      "images_total": 8,
      "images_available": 3,
      "images_failed": 1,
      "last_failed": false,
      "created_at": "2026-08-10T08:00:00Z",
      "updated_at": "2026-08-10T08:10:00Z"
    },
    "images": [
      {
        "id": "img-1",
        "status": "succeeded",
        "available": true,
        "url": "/api/v1/ai/t2i/images/img-1",
        "created_at": "2026-08-10T08:10:00Z"
      },
      {
        "id": "img-2",
        "status": "failed",
        "available": false,
        "url": null,
        "created_at": "2026-08-10T08:09:00Z"
      },
      {
        "id": "img-3",
        "status": "generating",
        "available": false,
        "url": null,
        "created_at": "2026-08-10T08:08:30Z"
      }
    ]
  },
  "message": "ok"
}
```

#### 错误

| code | message |
|------|---------|
| 2023 | 任务不存在 |

---

### 2.4 再生成一张

**POST** `/api/v1/ai/t2i/tasks/{id}/retry`

**需 admin**。异步生成一张新图追加到任务下。若已有一张 `generating` 图片，返回 `2024`，前端应轮询而非再点。

#### 请求体
空。

#### 响应

```json
{
  "code": 0,
  "data": {
    "image": {
      "id": "img-new",
      "status": "generating",
      "available": false,
      "url": null,
      "created_at": "2026-08-10T08:12:00Z"
    }
  },
  "message": "ok"
}
```

#### 错误

| code | message |
|------|---------|
| 1001 | 未登录 |
| 1002 | 无权限 |
| 2023 | 任务不存在 |
| 2024 | 已有正在生成的图片，请稍候 |

---

## 三、图片

### 3.1 下发图片二进制

**GET** `/api/v1/ai/t2i/images/{id}`

匿名可用。返回 `Content-Type: image/*` 与二进制流。前端直接 `<img src="/api/v1/ai/t2i/images/xxx">`。

#### 响应

- `200`：二进制流，`Content-Type` 与 `t2i_image.mime` 一致。
- `404`：图片不存在或未完成生成，非 JSON，返回空 body 便于浏览器兜底显示 broken-image icon。

（此接口不遵循统一 JSON 结构，仅返回二进制。）

---

### 3.2 标记可用 / 取消可用

**PATCH** `/api/v1/ai/t2i/images/{id}`

**需 admin**。

#### 请求

```json
{ "available": true }
```

#### 响应

```json
{
  "code": 0,
  "data": {
    "id": "img-1",
    "available": true,
    "task_id": "task-uuid",
    "task_business_status": "done"
  },
  "message": "ok"
}
```

`task_business_status` 用来让前端刷新列表卡片徽章无需重新拉整页。

#### 错误

| code | message |
|------|---------|
| 1001 | 未登录 |
| 1002 | 无权限 |
| 2025 | 图片不存在 |
| 2026 | 只有 status=succeeded 的图片可以标记 |

---

### 3.3 删除图片

**DELETE** `/api/v1/ai/t2i/images/{id}`

**需 admin**。硬删除（同时删除 `t2i_image` 与 `t2i_image_blob`）。`available=true` 的图不允许删除；需先取消可用。

#### 响应

```json
{
  "code": 0,
  "data": {
    "id": "img-1",
    "task_id": "task-uuid",
    "images_total": 7,
    "images_available": 2,
    "task_business_status": "done"
  },
  "message": "ok"
}
```

#### 错误

| code | message |
|------|---------|
| 1001 | 未登录 |
| 1002 | 无权限 |
| 2025 | 图片不存在 |
| 2027 | 可用图片不可删除，请先取消可用 |

---

## 四、错误码汇总

| code | 含义 |
|------|------|
| 0 | 成功 |
| 1001 | 未登录 |
| 1002 | 无权限（非 admin） |
| 2020 | template_code 不存在 |
| 2021 | 分页参数非法 |
| 2022 | 关键字校验失败 |
| 2023 | 任务不存在 |
| 2024 | 已有正在生成的图片 |
| 2025 | 图片不存在 |
| 2026 | 图片状态不允许标记 |
| 2027 | 可用图不可删除 |
| 5001 | AI 服务不可用 |
| 5002 | AI 响应超时 |

## 五、前端 Mock 备注

- Step 4 mock 路径：`frontend/src/services/t2i.mock.ts`，通过 `VITE_T2I_MOCK` 切换（默认 `true`）。
- Mock 内部用 `setTimeout` 模拟 2-4s 生成延迟，随机 10% 失败以覆盖 UI 各态。
- Mock 图片 URL 使用 `https://placehold.co/512x512/2563EB/ffffff?text={summary}` 占位。

## 六、后端实现要点（对齐 Step 5）

- 提示词拼接固定在后端：
  - `english-primer`: `"A cute flat cartoon illustration of a {word}, simple design, kids education style, plain white background, no text."`
  - `general`: `"{subject}, style: {style}, {extra}."`（缺失字段自动省略段）
- 关键字幂等：`keywords_hash = sha256(template_code + "|" + canonical_json(keywords))`，唯一索引。
- `AIClient.generate_image` 当前返回 URL（Mock 返回 placeholder，真实实现下载入库）；本次仅需把返回值 `fetch()` 一次成 bytes 存到 `t2i_image_blob.bytes`。
- 生图异步跑：router 里 `asyncio.create_task(...)`，请求立即返回 `generating` 记录；task 完成后 `commit` 更新 `t2i_image.status`。
