# API: 汉字学习（Level 化重构）

基础路径：`/api/v1`

本文件定义「汉字学习」相关接口，替换 `docs/api/ai-tools.md` 中原有的
`/hanzi/library/*` 系列。旧接口在后端实现完成后需从代码与文档中移除。

## 认证与权限

| 接口前缀 | 认证 | 角色 |
|----------|------|------|
| `/hanzi/levels/*`、`/hanzi/progress/*` | 必须登录 | `user` 或 `admin` |
| `/admin/hanzi/*` | 必须登录 | 仅 `admin` |

- 认证方式：`Authorization: Bearer <token>`
- 用户角色来自 `users.role` 字段（`'user' | 'admin'`，默认 `'user'`）

**统一错误码**

| code | message | 说明 |
|------|---------|------|
| 1001 | 未登录 | 未携带 token 或 token 失效 |
| 1002 | 无权限 | 非 admin 访问 admin 接口 |
| 2001 | 参数缺失 | 必填字段为空 |
| 2002 | 参数格式错误 | 例如 `char` 非单个汉字 |
| 2003 | 参数超长 | `name`、`pinyin` 等超过长度限制 |
| 2010 | 资源不存在 | `level_id` / `character_id` 找不到 |
| 2011 | 资源冲突 | `name` 或 `char` 已存在（全局唯一） |
| 2012 | 级别下仍有字条 | 删除 level 时被拦截 |
| 5000 | 服务器内部错误 | |

所有响应遵循统一返回格式：

```json
{ "code": 0, "data": {...}, "message": "ok" }
```

---

## 一、用户接口（`/hanzi/*`）

### 1.1 查询所有级别（含当前用户进度）

**GET** `/api/v1/hanzi/levels`

**需登录**。返回按 `order_index` 升序的级别列表；`learned` 为当前用户在该级别下已学字数。

#### 请求
无。

#### 响应

成功：
```json
{
  "code": 0,
  "data": {
    "levels": [
      {
        "id": "lvl-1",
        "name": "启蒙 · Level 1",
        "description": "最基础的常用字",
        "order_index": 1,
        "total": 20,
        "learned": 8,
        "created_at": "2026-07-01T00:00:00Z",
        "updated_at": "2026-07-01T00:00:00Z"
      }
    ]
  },
  "message": "ok"
}
```

失败：`1001`。

---

### 1.2 查询某级别的字表（含每字学习状态）

**GET** `/api/v1/hanzi/levels/{level_id}/characters`

**需登录**。返回级别内字条，按 `order_index` 升序；`learned` 与 `learned_at` 为当前用户状态。

#### 请求
Path：`level_id`（UUID，必填）

#### 响应

成功：
```json
{
  "code": 0,
  "data": {
    "level": {
      "id": "lvl-1",
      "name": "启蒙 · Level 1",
      "description": "最基础的常用字",
      "order_index": 1
    },
    "characters": [
      {
        "id": "char-1-0",
        "char": "人",
        "pinyin": "rén",
        "meaning": "人类",
        "order_index": 0,
        "learned": true,
        "learned_at": "2026-07-01T00:00:00Z"
      }
    ]
  },
  "message": "ok"
}
```

失败：`1001`、`2010`。

---

### 1.3 标记已学 / 取消已学

**PUT** `/api/v1/hanzi/progress/{character_id}`

**需登录**。幂等：
- `learned: true` → upsert 一条 `hanzi_user_progress`
- `learned: false` → 删除对应记录（无记录也返回 200）

#### 请求
Path：`character_id`（UUID，必填）
Body：
```json
{ "learned": true }
```

#### 响应

成功：
```json
{
  "code": 0,
  "data": {
    "character_id": "char-1-0",
    "learned": true,
    "learned_at": "2026-07-28T10:20:00Z"
  },
  "message": "ok"
}
```
- `learned: false` 时 `learned_at` 为 `null`。

失败：`1001`、`2001`（body 缺 `learned`）、`2010`（字条不存在）。

---

## 二、管理员接口（`/admin/hanzi/*`）

所有接口要求 `role = 'admin'`，否则返回 `1002`。

### 2.1 级别 CRUD

#### 2.1.1 列出级别（管理视图，含 total、无用户进度）

**GET** `/api/v1/admin/hanzi/levels`

响应：
```json
{
  "code": 0,
  "data": {
    "levels": [
      {
        "id": "lvl-1",
        "name": "启蒙 · Level 1",
        "description": "最基础的常用字",
        "order_index": 1,
        "total": 20,
        "created_at": "2026-07-01T00:00:00Z",
        "updated_at": "2026-07-01T00:00:00Z"
      }
    ]
  },
  "message": "ok"
}
```

#### 2.1.2 新建级别

**POST** `/api/v1/admin/hanzi/levels`

请求：
```json
{
  "name": "string  // 1-64",
  "description": "string  // 可空，<=500",
  "order_index": 1
}
```

响应：新建的 level（同 2.1.1 单项结构，`total=0`）。

失败：`1001`、`1002`、`2001`（name 缺失）、`2003`（超长）、`2011`（name 已存在）。

#### 2.1.3 更新级别

**PUT** `/api/v1/admin/hanzi/levels/{level_id}`

请求（所有字段可选，缺省表示不修改）：
```json
{
  "name": "string?",
  "description": "string | null",
  "order_index": 2
}
```

响应：更新后的 level。

失败：`1001`、`1002`、`2003`、`2010`、`2011`。

#### 2.1.4 删除级别

**DELETE** `/api/v1/admin/hanzi/levels/{level_id}`

**约束**：级别下 `total > 0` 时拒绝删除，返回 `2012`；前端应先清空字条。

响应：
```json
{ "code": 0, "data": null, "message": "ok" }
```

失败：`1001`、`1002`、`2010`、`2012`。

---

### 2.2 字条 CRUD

#### 2.2.1 列出某级别字条（管理视图，无用户进度）

**GET** `/api/v1/admin/hanzi/levels/{level_id}/characters`

响应：
```json
{
  "code": 0,
  "data": {
    "level": { "id": "lvl-1", "name": "启蒙 · Level 1" },
    "characters": [
      {
        "id": "char-1-0",
        "char": "人",
        "pinyin": "rén",
        "meaning": "人类",
        "order_index": 0,
        "created_at": "2026-07-01T00:00:00Z",
        "updated_at": "2026-07-01T00:00:00Z"
      }
    ]
  },
  "message": "ok"
}
```

失败：`1001`、`1002`、`2010`。

#### 2.2.2 新建单条字

**POST** `/api/v1/admin/hanzi/levels/{level_id}/characters`

请求：
```json
{
  "char": "人  // 必须为 1 个汉字，匹配 [\\u4e00-\\u9fa5]{1}",
  "pinyin": "string  // 1-32",
  "meaning": "string | null  // <=500",
  "order_index": 0
}
```

响应：新建的字条。

失败：`1001`、`1002`、`2001`、`2002`（char 非单汉字）、`2003`、`2010`、`2011`（char 已在其他级别）。

#### 2.2.3 批量导入字条

**POST** `/api/v1/admin/hanzi/levels/{level_id}/characters/batch`

**幂等策略**：整体半事务 —— 成功的入库，冲突/校验失败的记入 `failed`。
- `order_index` 由后端在当前 level `max(order_index) + 1` 起递增分配
- 单次上限 200 条

请求：
```json
{
  "items": [
    { "char": "人", "pinyin": "rén", "meaning": "人类" },
    { "char": "口", "pinyin": "kǒu", "meaning": "嘴巴" }
  ]
}
```

响应：
```json
{
  "code": 0,
  "data": {
    "ok": 1,
    "failed": [
      { "char": "口", "reason": "已存在（全局唯一）" }
    ]
  },
  "message": "ok"
}
```

失败：`1001`、`1002`、`2001`（items 为空）、`2003`（items > 200）、`2010`。

#### 2.2.4 更新字条

**PUT** `/api/v1/admin/hanzi/characters/{character_id}`

请求（字段可选）：
```json
{
  "char": "string?",
  "pinyin": "string?",
  "meaning": "string | null",
  "order_index": 3
}
```

响应：更新后的字条。

**注意**：修改 `char` 会触发全局唯一校验；若与其他级别的字冲突，返回 `2011`。

失败：`1001`、`1002`、`2002`、`2003`、`2010`、`2011`。

#### 2.2.5 删除字条

**DELETE** `/api/v1/admin/hanzi/characters/{character_id}`

**级联行为**：`hanzi_user_progress` 表通过 `ON DELETE CASCADE` 自动清理相关用户学习记录。

响应：
```json
{ "code": 0, "data": null, "message": "ok" }
```

失败：`1001`、`1002`、`2010`。

---

## 三、错误码汇总

| code | 场景 |
|------|------|
| 0 | 成功 |
| 1001 | 未登录 |
| 1002 | 无权限（非 admin 访问 admin 接口） |
| 2001 | 参数缺失 |
| 2002 | 参数格式错误（如 char 非单汉字） |
| 2003 | 参数超长或超上限（含 batch items > 200） |
| 2010 | 资源不存在（level / character） |
| 2011 | 资源冲突（level.name / character.char 已存在） |
| 2012 | 级别下仍有字条，拒绝删除 |
| 5000 | 服务器内部错误 |

---

## 四、字段长度与校验

| 字段 | 类型 | 约束 |
|------|------|------|
| `hanzi_levels.name` | String | 1-64，全局 UNIQUE |
| `hanzi_levels.description` | Text | 可空，<= 500 |
| `hanzi_levels.order_index` | Integer | >= 0 |
| `hanzi_characters.char` | String(4) | 匹配 `^[\u4e00-\u9fa5]$`，全局 UNIQUE |
| `hanzi_characters.pinyin` | String | 1-32 |
| `hanzi_characters.meaning` | Text | 可空，<= 500 |
| `hanzi_characters.order_index` | Integer | >= 0，级别内不强制唯一（前端按其排序） |

---

## 五、旧接口清理

后端实现完成后，需从 `docs/api/ai-tools.md` 与代码中移除：

- `GET  /api/v1/hanzi/library`
- `POST /api/v1/hanzi/library`
- `PUT  /api/v1/hanzi/library/{id}`
- `DELETE /api/v1/hanzi/library/{id}`

前端已在设计阶段删除 `HanziLibraryPage / HanziLearnPage / HanziSentencePage`
的路由入口，对应旧代码将在 Step 4 一并清理。
