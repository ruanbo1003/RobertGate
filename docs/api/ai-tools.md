# API: AI Tools

基础路径：`/api/v1`

工具集合接口，涵盖翻译/英文优化、汉字学习、英文启蒙、文生图。

## 认证约定

| 接口 | 认证 |
|------|------|
| AI 通用接口（`/ai/*`） | 匿名可用 |
| 汉字字库（`/hanzi/library/*`）| 必须登录，Header `Authorization: Bearer <token>` |
| 英文启蒙（`/english/*`）| 匿名可用（只读预生成数据） |

未登录访问受保护接口 → `code: 1001, message: "未登录"`。

---

## 一、翻译 / 英文优化

### 1.1 翻译或优化文本

**POST** `/api/v1/ai/translate`

对输入文本按指定动作处理：`translate`（中英互译，自动检测方向）/ `grammar`（英文语法与拼写修正）/ `native`（英文改地道）。

#### 请求
```json
{
  "text": "string  // 1-2000 字符",
  "action": "translate | grammar | native"
}
```

#### 响应

成功：
```json
{
  "code": 0,
  "data": {
    "action": "translate",
    "source_lang": "zh",      // zh | en，自动检测
    "target_lang": "en",
    "result": "The translated text..."
  },
  "message": "ok"
}
```

失败：
| code | message | 说明 |
|------|---------|------|
| 2001 | text 不能为空 | 参数缺失 |
| 2002 | text 超过 2000 字符 | 参数过长 |
| 2003 | action 非法 | 不在允许枚举内 |
| 5001 | AI 服务不可用 | 上游模型异常 |
| 5002 | AI 响应超时 | 上游超时 |

---

## 二、汉字学习

### 2.1 查询字库

**GET** `/api/v1/hanzi/library`

**需登录**。返回当前用户完整字库（含已学状态）。

#### 请求
Query 参数：无。

#### 响应

成功：
```json
{
  "code": 0,
  "data": {
    "total": 30,
    "learned": 12,
    "items": [
      {
        "char": "汉",
        "learned": true,
        "created_at": "2026-06-20T10:00:00Z",
        "learned_at": "2026-06-25T09:00:00Z"
      },
      {
        "char": "字",
        "learned": false,
        "created_at": "2026-06-20T10:00:00Z",
        "learned_at": null
      }
    ]
  },
  "message": "ok"
}
```

---

### 2.2 批量加入字库

**POST** `/api/v1/hanzi/library`

**需登录**。接受纯汉字数组或含中英标点的原始文本，后端负责提取汉字、去重、忽略非汉字字符。

#### 请求
```json
{
  "text": "string  // 原始文本，任意长度 ≤ 5000，将自动提取汉字"
}
```

#### 响应

成功：
```json
{
  "code": 0,
  "data": {
    "added": ["汉", "字"],
    "duplicated": ["中", "国"],
    "total": 32
  },
  "message": "ok"
}
```

失败：
| code | message | 说明 |
|------|---------|------|
| 1001 | 未登录 | 缺失或无效 token |
| 2001 | text 不能为空 | 参数缺失 |
| 2002 | text 超过 5000 字符 | 参数过长 |
| 2004 | 未识别到有效汉字 | 提取结果为空 |

---

### 2.3 更新单字学习状态

**PATCH** `/api/v1/hanzi/library/{char}`

**需登录**。将某字标记为已学 / 未学。

#### 请求
Path 参数：`char` — 单个汉字（URL encoded）。

Body：
```json
{
  "learned": true
}
```

#### 响应

成功：
```json
{
  "code": 0,
  "data": {
    "char": "汉",
    "learned": true,
    "learned_at": "2026-07-01T12:00:00Z"
  },
  "message": "ok"
}
```

失败：
| code | message | 说明 |
|------|---------|------|
| 1001 | 未登录 | |
| 2005 | 字不在字库中 | |

---

### 2.4 删除单字

**DELETE** `/api/v1/hanzi/library/{char}`

**需登录**。从字库删除单个汉字（不可撤销）。

#### 响应

成功：
```json
{
  "code": 0,
  "data": {
    "char": "汉",
    "total": 29
  },
  "message": "ok"
}
```

失败：
| code | message | 说明 |
|------|---------|------|
| 1001 | 未登录 | |
| 2005 | 字不在字库中 | |

---

### 2.5 获取单字信息（拼音 / 组词 / 例句）

**POST** `/api/v1/ai/character-info`

匿名可用。为「逐字学习」页面 AI 生成单字的辅助信息。

#### 请求
```json
{
  "char": "汉"
}
```

#### 响应

成功：
```json
{
  "code": 0,
  "data": {
    "char": "汉",
    "pinyin": "hàn",
    "words": ["汉字", "汉语", "汉朝"],
    "sentence": "汉字是中华文化的瑰宝。",
    "sentence_pinyin": "hàn zì shì zhōng huá wén huà de guī bǎo"
  },
  "message": "ok"
}
```

失败：
| code | message | 说明 |
|------|---------|------|
| 2001 | char 不能为空 | |
| 2006 | char 必须为单个汉字 | 长度非 1 或非汉字 |
| 5001 | AI 服务不可用 | |

---

### 2.6 生成句子（句子学习）

**POST** `/api/v1/ai/sentence`

匿名可用（前端传入字库快照）。基于给定字集合生成一句话；库外字由前端根据返回文本高亮。

#### 请求
```json
{
  "known_chars": ["汉", "字", "是", "中", "华", "瑰", "宝"]
}
```

#### 响应

成功：
```json
{
  "code": 0,
  "data": {
    "sentence": "汉字是中华瑰宝。",
    "pinyin": "hàn zì shì zhōng huá guī bǎo",
    "translation": "Chinese characters are treasures of Chinese culture.",
    "out_of_vocab": []
  },
  "message": "ok"
}
```

失败：
| code | message | 说明 |
|------|---------|------|
| 2001 | known_chars 不能为空 | |
| 2007 | known_chars 少于 5 个字 | 前端应先做兜底提示 |
| 5001 | AI 服务不可用 | |

---

## 三、英文启蒙

### 3.1 主题列表

**GET** `/api/v1/english/themes`

匿名可用。返回全部起步主题、每个主题包含的单词及图片 URL。

#### 响应

成功：
```json
{
  "code": 0,
  "data": {
    "themes": [
      {
        "id": "colors",
        "name_en": "Colors",
        "name_zh": "颜色",
        "emoji": "🎨",
        "ready": true,
        "words": [
          {
            "word": "red",
            "translation": "红色",
            "image_url": "/images/english/colors/red.png"
          }
        ]
      },
      {
        "id": "animals",
        "name_en": "Animals",
        "name_zh": "动物",
        "emoji": "🐶",
        "ready": true,
        "words": []
      }
    ]
  },
  "message": "ok"
}
```

字段说明：
- `ready`：主题是否所有图片已生成完毕，`false` 时前端主题卡显示「准备中」不可点。

---

### 3.2 出一轮题目

**POST** `/api/v1/english/quiz`

匿名可用。按主题一次性返回 10 道题；每题含 1 个正确单词 + 4 张图片（1 张正确 + 3 张干扰），正确项由 `correct_index` 标识。

#### 请求
```json
{
  "theme_id": "colors",
  "count": 10
}
```

#### 响应

成功：
```json
{
  "code": 0,
  "data": {
    "theme_id": "colors",
    "questions": [
      {
        "word": "red",
        "translation": "红色",
        "options": [
          "/images/english/colors/red.png",
          "/images/english/colors/blue.png",
          "/images/english/animals/dog.png",
          "/images/english/fruits/apple.png"
        ],
        "correct_index": 0
      }
    ]
  },
  "message": "ok"
}
```

失败：
| code | message | 说明 |
|------|---------|------|
| 2001 | theme_id 不能为空 | |
| 2008 | theme_id 不存在 | |
| 2009 | 主题尚未准备完毕 | ready=false |

---

## 四、文生图

### 4.1 生成图片

**POST** `/api/v1/ai/text-to-image`

匿名可用。一次只生成 1 张，同步返回图片 URL（后端已下载/存储）。

#### 请求
```json
{
  "prompt": "string  // 1-1000 字符，中英文皆可",
  "size": "1024x1024"    // 可选，默认 1024x1024
}
```

#### 响应

成功：
```json
{
  "code": 0,
  "data": {
    "prompt": "watercolor cat",
    "image_url": "/images/t2i/2026/07/01/xxxxxx.png",
    "created_at": "2026-07-01T12:00:00Z"
  },
  "message": "ok"
}
```

失败：
| code | message | 说明 |
|------|---------|------|
| 2001 | prompt 不能为空 | |
| 2002 | prompt 超过 1000 字符 | |
| 2010 | size 不支持 | 目前仅支持 1024x1024 |
| 5001 | AI 服务不可用 | |
| 5002 | AI 响应超时 | |
| 5003 | 图片下载失败 | 上游图片存储失败 |

---

## 五、错误码汇总

| 范围 | 含义 |
|------|------|
| 0 | 成功 |
| 1001 | 未登录 / token 无效 |
| 2001-2009 | 参数错误 |
| 2010 | 尺寸不支持（文生图） |
| 5001 | AI 服务不可用 |
| 5002 | AI 响应超时 |
| 5003 | 图片下载失败 |

---

## 六、前端 Mock 数据备注

Step 4 前端实现阶段使用本地 mock 数据，路径：`frontend/src/mock/ai-tools.ts`，导出符合上述响应结构的假数据，通过统一 `apiClient` 拦截返回。Step 6 联调时替换为真实请求。
