# API: 法律咨询（RAG 对话）

基础路径：`/api/v1`

本文件定义「法律咨询」相关接口。每个用户仅有一个对话（单会话模型），
消息按用户隔离，历史永久保留。知识库为《中华人民共和国民法典》，
按"条"切分索引，服务端启动时若索引不存在则自动构建。

## 认证与权限

| 接口前缀 | 认证 | 角色 |
|----------|------|------|
| `/legal-consult/*` | 必须登录 | `user` 或 `admin` |

- 认证方式：`Authorization: Bearer <token>`

**统一错误码**

| code | message | 说明 |
|------|---------|------|
| 1001 | 未登录 | 未携带 token 或 token 失效 |
| 2001 | 参数缺失 | `content` 为空或全空白 |
| 2003 | 参数超长 | `content` 超过 2000 字 |
| 2010 | 资源不存在 | 条文编号找不到 |
| 5000 | 服务器内部错误 | |
| 5001 | 模型服务异常 | SiliconFlow 调用失败/超时 |
| 5002 | 知识库未就绪 | 向量索引构建中或构建失败 |

除 SSE 流式接口外，所有响应遵循统一返回格式：

```json
{ "code": 0, "data": {...}, "message": "ok" }
```

**公共数据结构**

消息对象 `Message`：

```json
{
  "id": "msg-uuid",
  "role": "user",
  "content": "我租的房子到期了，房东不退押金……",
  "citations": [],
  "created_at": "2026-10-24T10:00:00Z"
}
```

- `role`：`"user" | "assistant"`
- `citations`：仅 `assistant` 消息非空，元素为引用条文对象 `Citation`

引用条文对象 `Citation`：

```json
{ "article_no": 710, "label": "第七百一十条" }
```

---

## 1. 发送消息（SSE 流式）

**POST** `/api/v1/legal-consult/messages`

**需登录**。用户发送一个问题，服务端：
1. 持久化用户消息；
2. 以最近 20 轮对话 + RAG 检索到的条文构造 prompt；
3. 以 SSE 流式返回 AI 回答，完成后持久化 assistant 消息。

### 请求

Header：`Accept: text/event-stream`

Body（JSON）：

```json
{ "content": "房东不退押金合理吗？" }
```

| 字段 | 类型 | 必填 | 约束 |
|------|------|------|------|
| content | string | 是 | 去除首尾空白后 1~2000 字 |

### 响应（`text/event-stream`）

事件按以下顺序推送：

**`event: citations`** — 检索完成后立即推送本次引用的条文（可能为空数组）：

```
event: citations
data: {"citations": [{"article_no": 710, "label": "第七百一十条"}]}
```

**`event: delta`** — 回答增量文本，多次推送：

```
event: delta
data: {"text": "关键在于墙面污渍"}
```

**`event: done`** — 生成完毕，携带落库后的完整 assistant 消息：

```
event: done
data: {"message": { "id": "msg-uuid", "role": "assistant", "content": "...", "citations": [...], "created_at": "..." }}
```

**`event: error`** — 任一环节失败时推送并结束流（流已建立后不再变更 HTTP 状态码）：

```
event: error
data: {"code": 5001, "message": "模型服务异常"}
```

参数校验失败（`2001`/`2003`）、未登录（`1001`）在建立流之前即以普通 JSON
响应返回统一格式，不进入 SSE。

失败：`1001`、`2001`、`2003`、`5001`、`5002`。

---

## 2. 拉取全部历史消息

**GET** `/api/v1/legal-consult/messages`

**需登录**。返回当前用户的全部消息，按 `created_at` 升序。不分页。

### 请求
无。

### 响应

成功：

```json
{
  "code": 0,
  "data": {
    "messages": [
      { "id": "msg-1", "role": "user", "content": "...", "citations": [], "created_at": "..." },
      { "id": "msg-2", "role": "assistant", "content": "...", "citations": [{"article_no": 710, "label": "第七百一十条"}], "created_at": "..." }
    ]
  },
  "message": "ok"
}
```

从未发过消息时 `messages` 为空数组（前端据此渲染空状态）。

失败：`1001`。

---

## 3. 清空对话

**DELETE** `/api/v1/legal-consult/messages`

**需登录**。删除当前用户的全部消息，不可恢复。

### 请求
无。

### 响应

成功：

```json
{ "code": 0, "data": null, "message": "ok" }
```

失败：`1001`。

---

## 4. 查询条文原文

**GET** `/api/v1/legal-consult/articles/{article_no}`

**需登录**。按条文编号返回《民法典》条文原文，供条文抽屉展示。

### 请求

Path：`article_no`（int，必填，如 `710`）

### 响应

成功：

```json
{
  "code": 0,
  "data": {
    "article": {
      "article_no": 710,
      "label": "第七百一十条",
      "content": "承租人按照约定的方法或者根据租赁物的性质使用租赁物，致使租赁物受到损耗的，不承担赔偿责任。"
    }
  },
  "message": "ok"
}
```

失败：`1001`、`2010`、`5002`。

---

## 技术备注

- **模型服务**：SiliconFlow（OpenAI 兼容），对话模型 DeepSeek 系列，
  Embedding 模型 BGE-M3。API Key 通过后端环境变量配置，不暴露给前端。
- **RAG**：查询时取用户问题（可拼接近几轮上下文）做向量检索，Top-K 条文
  注入 system prompt；回答要求模型仅做条文解读、不给行动指引，并在超出
  民法典范围时如实说明。
- **引用解析**：`citations` 由服务端根据检索结果与模型输出共同确定，
  前端不自行从正文解析条文编号。
- **上下文**：服务端取该用户最近 20 轮（40 条）消息参与推理。
