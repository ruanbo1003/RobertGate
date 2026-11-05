# API: AI Videos（英语启蒙短视频工作台）

基础路径：`/api/v1/ai-videos`

对应 PRD：`docs/prd/ai-videos.md`

## 认证约定

所有接口需登录（JWT Bearer Token），未登录 → `1001, "未登录"`。单用户工具，不区分角色。

## 统一响应

沿用项目约定（`.claude/rules/api.md`），成功 `code=0`，失败 `code≠0`。产物文件接口除外（直接返回二进制流）。

## 状态枚举

- 产物状态 `asset_state`：`pending`（待生成）/ `running`（生成中）/ `success` / `failed`
- 产物过期标记 `stale`：bool，上游（prompt / 台词 / 剧本）修改后置 true，产物保留可用
- 项目状态 `project_status`（后端按分镜聚合派生，只读）：`draft` / `generating` / `partial_failed` / `completed`
- 合成状态 `compose_state`：`none` / `running` / `success` / `failed`

---

## 一、模型

### 1.1 列出可用模型

**GET** `/api/v1/ai-videos/models`

返回后端配置的 SiliconFlow 模型清单，供各处模型下拉使用。

#### Query

| 名称 | 类型 | 默认 | 说明 |
|------|------|------|------|
| `type` | string | 全部 | `llm` / `t2i` / `i2v` / `tts`，省略返回全部分组 |

#### 响应

```json
{
  "code": 0,
  "data": {
    "models": {
      "llm":  [ { "id": "google/gemini-3.8-flash", "name": "Gemini 3.8 Flash", "default": true } ],
      "t2i":  [ { "id": "google/gemini-3.1-flash-image", "name": "Gemini 3.1 Flash Image", "default": true, "reference": "multi" } ],
      "i2v":  [ { "id": "bytedance/seedance-2.0-fast", "name": "Seedance 2.0 Fast", "default": true } ],
      "tts":  [ { "id": "openai/gpt-audio", "name": "GPT Audio", "default": true,
                  "voices": ["alex", "anna", "benjamin", "bella"] } ]
    }
  },
  "message": "ok"
}
```

模型全部来自 OpenRouter。t2i 条目的 `reference` 为参考图能力档：`multi`（多参考图，生成分镜图时携带全部出场角色的封面设定图）或 `none`（纯 prompt，角色外形描述拼入 prompt 兜底）。

---

## 二、角色库

### 2.1 列出角色

**GET** `/api/v1/ai-videos/characters`

按 `updated_at DESC` 返回全部角色（数量少，不分页）。

#### 响应

```json
{
  "code": 0,
  "data": {
    "characters": [
      {
        "id": 1,
        "name": "Momo",
        "appearance_prompt": "A cute cartoon fox child, orange fur, big curious eyes, green overalls",
        "personality": "好奇心旺盛，喜欢提问",
        "cover_image_url": "/api/v1/ai-videos/files/characters/1/cover.png",
        "candidate_images": [
          { "id": 11, "url": "/api/v1/ai-videos/files/characters/1/11.png" }
        ],
        "used_count": 4,
        "created_at": "2026-11-01T10:00:00Z",
        "updated_at": "2026-11-02T10:00:00Z"
      }
    ]
  },
  "message": "ok"
}
```

### 2.2 创建角色

**POST** `/api/v1/ai-videos/characters`

#### 请求

```json
{ "name": "Momo", "appearance_prompt": "...", "personality": "..." }
```

| 字段 | 必填 | 约束 |
|------|------|------|
| `name` | 是 | 1-50 字符，唯一 |
| `appearance_prompt` | 是 | 1-1000 字符 |
| `personality` | 否 | ≤500 字符 |

#### 响应

`data` 为完整角色对象（同 2.1 单项，`cover_image_url=null`，`candidate_images=[]`）。

名称重复 → `2001, "角色名称已存在"`。

### 2.3 更新角色

**PUT** `/api/v1/ai-videos/characters/{id}`

请求体同 2.2，均可选；另支持 `cover_image_id`（必须属于该角色的候选图，否则 `2001`）。

修改 `appearance_prompt` **不会**自动作废已生成的分镜产物（设定图是生成时快照）。

### 2.4 删除角色

**DELETE** `/api/v1/ai-videos/characters/{id}`

被项目引用时拒绝：

```json
{ "code": 2002, "data": { "used_by": [ { "project_id": 3, "title": "EP03 · At the Supermarket" } ] }, "message": "角色已被 1 个视频引用，不能删除" }
```

### 2.5 生成设定图（同步）

**POST** `/api/v1/ai-videos/characters/{id}/generate-image`

同步调 SiliconFlow 文生图，生成一张加入候选集（候选集上限 8 张，先进先出淘汰未选中的旧图）。前端点一次生成一张。超时 120s。

#### 请求

```json
{ "model": "google/gemini-3.1-flash-image", "prompt": "可选，缺省用 appearance_prompt 拼接标准后缀" }
```

#### 响应

```json
{ "code": 0, "data": { "image": { "id": 12, "url": "/api/v1/ai-videos/files/characters/1/12.png" } }, "message": "ok" }
```

上游失败 → `5001`；余额/Key 问题 → `5002`。

---

## 三、视频项目

### 3.1 分页列项目

**GET** `/api/v1/ai-videos/projects`

#### Query

| 名称 | 类型 | 默认 | 说明 |
|------|------|------|------|
| `page` | int | 1 | |
| `page_size` | int | 20 | 1-50 |

#### 响应

```json
{
  "code": 0,
  "data": {
    "total": 4,
    "items": [
      {
        "id": 3,
        "title": "EP03 · At the Supermarket",
        "status": "generating",
        "cover_url": "/api/v1/ai-videos/files/projects/3/shots/1/image.png",
        "duration_estimate": 90,
        "shot_count": 15,
        "progress": { "image": 15, "video": 8, "audio": 12 },
        "updated_at": "2026-11-04T09:00:00Z"
      }
    ]
  },
  "message": "ok"
}
```

`cover_url` 取第一镜的分镜图，无则 `null`。

### 3.2 创建项目

**POST** `/api/v1/ai-videos/projects`

创建草稿，此时还没有剧本和分镜。

#### 请求

```json
{
  "title": "EP03 · At the Supermarket",
  "synopsis": "Momo 和 Kuku 去超市买苹果，学习水果和购物用语",
  "character_ids": [1, 3],
  "target_duration": 90,
  "default_models": { "llm": "google/gemini-3.8-flash", "t2i": "google/gemini-3.1-flash-image", "i2v": "bytedance/seedance-2.0-fast", "tts": "openai/gpt-audio" },
  "tts_voice": "alex"
}
```

| 字段 | 必填 | 约束 |
|------|------|------|
| `title` | 是 | 1-100 字符 |
| `synopsis` | 是 | 1-1000 字符 |
| `character_ids` | 是 | 1-4 个已存在角色 |
| `target_duration` | 是 | 30-120（秒） |
| `default_models` | 否 | 缺省取各类型 default 模型 |
| `tts_voice` | 否 | 缺省取 tts 模型第一个 voice |

### 3.3 项目详情

**GET** `/api/v1/ai-videos/projects/{id}`

```json
{
  "code": 0,
  "data": {
    "project": {
      "id": 3,
      "title": "EP03 · At the Supermarket",
      "synopsis": "...",
      "status": "generating",
      "target_duration": 90,
      "characters": [ { "id": 1, "name": "Momo", "cover_image_url": "..." } ],
      "default_models": { "llm": "...", "t2i": "...", "i2v": "...", "tts": "..." },
      "tts_voice": "alex",
      "script": {
        "scenes": [
          { "setting": "At the supermarket entrance",
            "lines": [ { "character_id": 1, "en": "Look, Kuku! A supermarket!", "zh": "看，Kuku！一家超市！",
                        "video_prompt": "points at the supermarket, slow pan right", "characters": ["Momo", "Kuku"] } ] }
        ]
      },
      "compose": { "state": "none", "video_url": null, "error": null, "stale": false },
      "shots": [
        {
          "id": 31,
          "order": 1,
          "duration_estimate": 5.0,
          "speaker_character_id": 1,
          "ref_character_ids": [1],
          "video_prompt": "the fox waves happily, slow push-in, sunny mood",
          "line_en": "Look, Kuku! A supermarket!",
          "line_zh": "看，Kuku！一家超市！",
          "image_prompt": "Momo the fox pointing at a small supermarket...",
          "image":  { "state": "success", "url": "/api/v1/ai-videos/files/projects/3/shots/31/image.png", "model": "google/gemini-3.1-flash-image", "stale": false, "error": null },
          "video":  { "state": "running", "url": null, "model": "bytedance/seedance-2.0-fast", "stale": false, "error": null },
          "audio":  { "state": "pending", "url": null, "model": "openai/gpt-audio", "voice": "alloy", "duration": null, "stale": false, "error": null }
        }
      ]
    }
  },
  "message": "ok"
}
```

### 3.4 更新项目

**PUT** `/api/v1/ai-videos/projects/{id}`

可改 `title` / `synopsis` / `default_models` / `tts_voice`。改 `synopsis` 不自动作废任何产物。

### 3.5 删除项目

**DELETE** `/api/v1/ai-videos/projects/{id}`

级联删除分镜、任务与磁盘产物。有任务在跑 → 先取消再删。

---

## 四、剧本与分镜

### 4.1 生成剧本（同步，可较慢）

**POST** `/api/v1/ai-videos/projects/{id}/script/generate`

LLM 按 `synopsis` + 角色设定 + `target_duration` 生成结构化剧本。同步返回（前端 loading 可取消），超时 120s。重复调用直接覆盖旧剧本（分镜不动，由 4.3 重拆决定）。

#### 请求

```json
{ "model": "google/gemini-3.8-flash" }
```

#### 响应

`data.script` 同 3.3 中 `script` 结构。

### 4.2 保存剧本

**PUT** `/api/v1/ai-videos/projects/{id}/script`

请求体为编辑后的完整 `script` 对象（line 的 `video_prompt`/`characters` 为可选字段，编辑时保留透传；拆分镜按 `characters` 匹配项目角色得到各镜 `ref_character_ids`，匹配不到回退说话人）。保存后**不**自动改分镜；若已存在分镜，响应附 `"shots_exist": true` 供前端提示「是否重新拆分镜」。

### 4.3 拆分镜（同步）

**POST** `/api/v1/ai-videos/projects/{id}/shots/split`

LLM 把当前剧本拆为分镜列表（每镜一句短台词、生成画面 prompt、预估时长）。

#### 请求

```json
{ "model": "google/gemini-3.8-flash", "confirm_replace": true }
```

已存在分镜且 `confirm_replace` 非 true → `2005`，`data.existing_shot_count` 提示数量；为 true 则**删除全部旧分镜及产物**后重建。

#### 响应

`data.shots` 同 3.3 中 `shots` 结构（全部产物 `pending`）。

### 4.4 新增分镜

**POST** `/api/v1/ai-videos/projects/{id}/shots`

```json
{ "after_shot_id": 31 }
```

在指定镜后插入空镜（`after_shot_id=null` 插到最前），返回新镜对象。

### 4.5 编辑分镜

**PUT** `/api/v1/ai-videos/projects/{id}/shots/{shot_id}`

可改字段：`line_en`、`line_zh`、`speaker_character_id`、`ref_character_ids`（必须是项目已选角色的子集）、`image_prompt`、`video_prompt`、`duration_estimate`。

**过期链规则（服务端执行）**：
- 改 `image_prompt` 或 `ref_character_ids` → 该镜 `image`、`video` 置 `stale=true`
- 改 `video_prompt` → 该镜 `video` 置 `stale=true`
- 改 `line_en` 或 `speaker_character_id` → 该镜 `audio` 置 `stale=true`（字幕随台词走）
- 产物重新生成成功后 `stale` 复位，合成产物置 `compose.stale=true`

响应返回更新后的完整镜对象。生成中的任务不受编辑影响，按旧参数跑完后立即标 `stale`。

### 4.6 删除分镜

**DELETE** `/api/v1/ai-videos/projects/{id}/shots/{shot_id}`

### 4.7 分镜排序

**PUT** `/api/v1/ai-videos/projects/{id}/shots/order`

```json
{ "shot_ids": [31, 33, 32, 34] }
```

必须恰好覆盖全部分镜，否则 `2001`。排序使 `compose.stale=true`。

---

## 五、生成与合成（异步任务）

单镜三类产物 + 批量 + 合成均为异步：接口立即返回 `202` 语义（`code=0`），实际进度靠 6.1 轮询。失败**不自动重试**，由用户手动重发。同一产物已有 `running` 任务时再次提交 → `2006, "该产物正在生成中"`。

服务端并发：t2i 2 路、i2v 1 路、tts 2 路，超出排队（FIFO）。遇 `5002`（余额/Key 全局错误）暂停整个队列。

### 5.1 生成分镜图

**POST** `/api/v1/ai-videos/projects/{id}/shots/{shot_id}/image`

```json
{ "model": "google/gemini-3.1-flash-image" }
```

`reference=multi` 的模型自动携带 `ref_character_ids` 中每个角色的封面设定图（按序点名）；`none` 则把各角色 `appearance_prompt` 拼入 prompt。产物直接覆盖旧图。

### 5.2 生成视频

**POST** `/api/v1/ai-videos/projects/{id}/shots/{shot_id}/video`

```json
{ "model": "bytedance/seedance-2.0-fast" }
```

该镜 `image.state != success` → `2003, "请先生成分镜图"`。以分镜图为首帧。

### 5.3 生成配音

**POST** `/api/v1/ai-videos/projects/{id}/shots/{shot_id}/audio`

```json
{ "model": "openai/gpt-audio", "voice": "alloy" }
```

对 `line_en` 做 TTS，成功后回填 `audio.duration`（秒，用于合成对齐）。

### 5.4 批量生成

**POST** `/api/v1/ai-videos/projects/{id}/generate-all`

```json
{ "types": ["image", "video", "audio"], "scope": "missing" }
```

| 字段 | 说明 |
|------|------|
| `types` | 要生成的产物类型，子集 |
| `scope` | `missing`：只排 `pending`/`failed`/`stale` 的；`all`：全部重做 |

按镜序入队；`video` 自动等待同镜 `image` 成功后才派发，`image` 失败则该镜 `video` 标记 `failed`（error="前置分镜图失败"）。响应返回 `data.enqueued`（各类型入队数）。

### 5.5 取消队列

**POST** `/api/v1/ai-videos/projects/{id}/queue/cancel`

清空该项目所有排队中任务（`running` 的跑完为止），对应产物回到原状态。

### 5.6 合成成片

**POST** `/api/v1/ai-videos/projects/{id}/compose`

```json
{ "ignore_stale": false }
```

前置校验：
- 任一镜 `video` 或 `audio` 非 `success` → `2003`，`data.missing` 列出缺失清单
- 存在 `stale=true` 产物且 `ignore_stale` 非 true → `2004`，`data.stale_items` 列出过期清单（前端据此弹确认框）

合成规则：每镜时长 = max(视频时长, 音频时长)，视频不足末帧定格；字幕烧录 `line_en`（底部整句）。产出 `projects/{id}/final.mp4`。

### 5.7 下载成片

**GET** `/api/v1/ai-videos/projects/{id}/download`

`compose.state != success` → `2003`。成功返回 `video/mp4` 二进制流（`Content-Disposition: attachment`）。

---

## 六、轮询与文件

### 6.1 聚合状态（工作台轮询，2-3s 间隔）

**GET** `/api/v1/ai-videos/projects/{id}/status`

轻量接口，只返回状态不返回 prompt/台词等重内容：

```json
{
  "code": 0,
  "data": {
    "status": "generating",
    "queue": { "pending": 5, "running": 2, "paused": false, "paused_reason": null },
    "progress": { "image": { "done": 15, "total": 15 }, "video": { "done": 8, "total": 15 }, "audio": { "done": 12, "total": 15 } },
    "stale_count": 2,
    "compose": { "state": "none", "video_url": null, "error": null, "stale": false },
    "shots": [
      { "id": 31,
        "image": { "state": "success", "stale": false, "url": "...", "version": 3 },
        "video": { "state": "running", "stale": false, "url": null, "version": 1 },
        "audio": { "state": "pending", "stale": false, "url": null, "version": 0 } }
    ]
  },
  "message": "ok"
}
```

`version` 每次生成成功 +1，前端用于刷新缓存图片（URL 加 `?v=`）。`paused=true` 时 `paused_reason` 给出全局错误文案（顶部横幅展示）。

### 6.2 产物文件

**GET** `/api/v1/ai-videos/files/{path}`

返回二进制流（图 `image/png`、音频 `audio/mp3`、视频 `video/mp4`）。`path` 限定在 `backend/data/ai-videos/` 内（防目录穿越），不存在 → 404。

---

## 错误码汇总

| code | 含义 |
|------|------|
| 0 | 成功 |
| 1001 | 未登录 |
| 2001 | 参数错误（字段校验失败、名称重复、排序不完整等） |
| 2002 | 角色被引用不可删除 |
| 2003 | 前置条件不满足（无图不能生视频、未合成不能下载、缺产物不能合成） |
| 2004 | 存在过期产物需确认（合成未带 `ignore_stale`） |
| 2005 | 已存在分镜需确认替换 |
| 2006 | 产物已有任务在生成中 |
| 2007 | 资源不存在（项目 / 角色 / 分镜） |
| 5001 | SiliconFlow 上游调用失败（message 附上游错误摘要） |
| 5002 | SiliconFlow 余额不足或 Key 失效（全局，暂停队列） |
| 5003 | ffmpeg 合成失败（message 附日志摘要） |
| 5000 | 其他服务器内部错误 |
