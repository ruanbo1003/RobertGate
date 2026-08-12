# 汉字管理：合并为「汉字添加」+ AI 生成拼音/例词

日期：2026-08-07

## 背景

`AdminCharacterListPage` 现在有两个按钮：「批量导入」（modal 里手填 `char/pinyin/meaning`）和「单条添加」（modal 里手填单条）。用户实际使用时希望能一次贴入任意文本，让后端提取汉字并用 AI 自动补齐 `pinyin` 和例词，减少手工录入。

## 目标

- 页面合并为一个按钮「汉字添加」；用一个 modal（含 textarea）同时支持 1 个或多个汉字。
- 后端接收任意文本，提取其中的汉字（`[\u4e00-\u9fa5]`），去重、剔除已存在字符。
- 对每个新字，调 AI（LangChain + OpenRouter）拿 `pinyin` 和 4 个含该字的**简单词语**。
- 拼音 + 例词落库；不再需要「释义」。
- 前端卡片除了显示字和拼音，还要展示 4 个例词。

## 非目标

- 不做异步任务/进度轮询；一次请求全部跑完再返回。
- 不改动 `hanzi_levels` 表结构。
- 不新增 admin 之外的能力，但由于 `meaning` 列被删、`example_words` 列被加，学习端 API 响应必然同步变化（见"连带修改"）。

## 数据模型变更

`hanzi_characters` 表：

- **新增** `example_words JSONB NOT NULL DEFAULT '[]'`（PostgreSQL JSONB，存 `list[str]`）
- **删除** `meaning TEXT`（数据一并丢弃）

Alembic 迁移：一个 revision，两步 op（add_column + drop_column）。回滚方向对称。

Model 更新：

```python
class HanziCharacter(Base):
    ...
    # 移除 meaning
    example_words: Mapped[list[str]] = mapped_column(JSONB, default=list)
```

## API 变更

**删除**：
- `POST /api/v1/admin/hanzi/levels/{level_id}/characters/batch`（旧批量导入，前端手工录入的入口，不再需要）

**新增**：
- `POST /api/v1/admin/hanzi/levels/{level_id}/characters/ai-add`
  - Request: `{ "text": "任意字符串，可含标点/字母/多汉字/重复" }`
  - Response `data`:
    ```json
    {
      "ok": 3,
      "added": [{"char": "字", "pinyin": "zì", "example_words": ["文字","字体","字幕","汉字"]}, ...],
      "skipped": [{"char": "字", "reason": "已存在"}],
      "failed": [{"char": "呀", "reason": "AI 服务不可用: ..."}]
    }
    ```

**修改**：
- `POST /api/v1/admin/hanzi/levels/{level_id}/characters`（单条创建）：
  - 请求体去掉 `meaning`
  - 新增可选 `example_words: list[str]`（编辑用，长度 ≤ 20）
- `PUT /api/v1/admin/hanzi/characters/{id}`：同上。

响应体：所有 character 字段返回 `example_words`，去掉 `meaning`。

## Prompt（`character_info`）

在 `OpenRouterAIClient` 里实装 `character_info`（当前委托给 mock），使用 LangChain + `JsonOutputParser`。

System prompt（中文）：

```
你是一名中文教师，请为下面这个汉字生成学习资料。
要求：
1. 只输出 JSON，字段固定为 pinyin（string，带声调的拼音，多音字取最常用读音）和 words（长度恰好为 4 的 string 数组，每个是包含该字的常见双字词）。
2. words 要贴近日常，避免生僻词、成语、专有名词。
3. 不要解释、不要 markdown、不要额外键。

示例：
输入：字
输出：{"pinyin": "zì", "words": ["文字", "字体", "字幕", "汉字"]}
```

User message: 单字。

`ChatOpenAI` 设置 `model_kwargs={"response_format": {"type": "json_object"}}` 以强制 JSON。若上游模型不支持，退回纯文本 + `JsonOutputParser` 容错。

保留 `character_info` 返回结构 `{pinyin, words, sentence, sentence_pinyin}` 的兼容性：`sentence` / `sentence_pinyin` 保持为 mock 分支的兜底或空串，本次不用到。

## Service 编排（并发）

`AdminHanziService.ai_add(level_id, text)`：

1. `_extract_chars(text)`：正则提取 `[\u4e00-\u9fa5]`，按出现顺序保序去重。
2. 命中 DB `existing_chars(...)`：分出 `skipped[already-exists]` 与 `to_generate`。
3. `asyncio.gather(*(self._fetch_one(c) for c in to_generate), return_exceptions=True)`：并发调 AI。
4. 收集三类结果：`added / skipped / failed`。
5. 顺序分配 `order_index`，从当前 `max_order_index + 1` 起递增，落库 `save_many`。
6. 返回结果 dict。

`_fetch_one(char)` 返回 `(char, pinyin, words)` 或抛异常（异常里带 char + reason）。

**限流**：并发上限用 `asyncio.Semaphore(5)`，避免一次贴 50 字打爆 OpenRouter。

## 前端

**移除**：
- `components/admin/CharacterBatchImportModal.tsx`
- `AdminCharacterListPage` 的「批量导入」按钮、`handleBatch`、空态里的"批量导入"链接
- `services/hanzi.ts` 里的 `adminBatchImport`
- `types/hanzi.ts` 里的 `BatchImportItem`

**新增**：
- `components/admin/CharacterAiAddModal.tsx`
  - 单个 textarea（`rows=6`），placeholder：「粘贴或输入汉字，一个或多个都可以（其它字符会被自动过滤）」
  - 提交时前端做一次预览：正则提取 + 去重，显示"将处理 N 个字"（不显示具体是哪些，避免长）
  - 点击提交 → 调 `adminAiAddCharacters(levelId, text)`
  - 返回后展示结果 summary：`✓ 成功 N` / `⚪ 已存在 M` / `✗ 失败 K（列出前 5 个 reason）`
  - 关闭 modal 触发 `refresh()`

**修改**：
- 「单条添加」按钮改名「汉字添加」，图标从 `Plus` 保留，点击打开新 `CharacterAiAddModal`
- 卡片增加显示 `example_words`：4 个词以 pill/tag 形式在拼音下方，字号很小；空 array 则不显示
- `CharacterEditModal`：移除 `meaning` 字段；新增 `example_words` 编辑（一行一个词，或逗号分隔的文本框），可选
- 空态里的"批量导入"链接改成"汉字添加"

**类型**：
- `HanziCharacter`：去掉 `meaning`，新增 `example_words: string[]`
- 新增 `AiAddResponse { ok, added, skipped, failed }`

## 连带修改（学习端）

删除 `meaning` 列会影响 `/api/v1/hanzi/library`：

- `backend/app/service/hanzi_service.py:72` 序列化里去掉 `"meaning": c.meaning`，加上 `"example_words": c.example_words`
- `frontend/src/types/hanzi.ts` 删除 `HanziCharacter.meaning`，加 `example_words: string[]`
- `frontend/src/pages/ai-tools/HanziCharacterGridPage.tsx` 卡片：删掉 `meaning` 展示；例词是否展示由后续需求决定，本次先不加（用户端 UI 未提及）
- 「编辑」相关的 admin type 里删除 `meaning`

## Schemas 变更（backend）

- `CharacterCreateRequest` / `CharacterUpdateRequest`：删 `meaning`，加 `example_words: list[str] | None`（长度 ≤ 20，每项 ≤ 16 字符）
- 删 `BatchImportRequest` / `BatchImportItem`
- 新增 `AiAddRequest { text: str }`，`text` 长度 1..2000

## 错误处理

- Modal 提交时若提取后 `chars` 为空 → 前端直接不发请求，提示"未识别到汉字"
- 单字 AI 失败 → 计入 `failed`，不阻断其它字
- 若全部失败 → response 仍是 200 `code=0`（业务成功，但 ok=0）；前端展示 failed 列表

## 测试

- `test_admin_hanzi_service.py`：
  - `_extract_chars` 正确剔除非汉字/去重/保序
  - `ai_add`：mock AI，验证 3 类分桶正确
  - `ai_add`：AI 抛异常 → 该字进 failed，其它继续
  - `ai_add`：文本为空/无汉字 → `ok=0, added=[], skipped=[], failed=[]`
- `test_ai_tools_schemas.py` / hanzi schemas：补 `AiAddRequest` 校验、`CharacterCreateRequest` 无 `meaning`
- Alembic 迁移 offline dry-run（`alembic upgrade head --sql`）

## 验收标准

1. 「批量导入」按钮和 modal 消失；只有「汉字添加」一个按钮。
2. 粘贴 `"你好世界，Hello, 好，界！"` 后：`你 / 好 / 世 / 界`（保序去重）被识别；`好` 若已存在则 skipped，其它三个成功入库。
3. 数据库 `hanzi_characters` 有 `example_words` 列且非空数组；`meaning` 列不复存在。
4. 卡片显示 `example_words` 4 个词。
5. `AdminHanziService` 单测全部通过。
