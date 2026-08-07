# 汉字学习：随机学习 & 组合练习 设计

- **日期**：2026-08-07
- **范围**：`/ai-tools/hanzi/:levelId` 学习端页面新增两个学习模式
- **上游依赖**：已完成的 `example_words` 重构（0003 迁移、`AdminHanziService.ai_add`、`OpenRouterAIClient.character_info`）

## 背景

当前学习端 `HanziCharacterGridPage.tsx` 只有一种模式：字表 grid + 点击切换已学/未学。用户希望在同一级别下新增两种更主动的学习方式：

1. **随机学习**：从未学字中随机抽一个，大字号呈现「字 + 拼音 + 4 例词」，每项都能点喇叭朗读。
2. **组合练习**：基于该用户在该级别已学的字，用 AI 生成一小段简单短句（允许少量简单生词），让小朋友练习读文。

## 目标 / 非目标

**目标**
- 三种模式在同一页面切换（Tab），共享 level & 进度上下文，切换零跳转。
- 随机学习支持"读字 + 读词"的 TTS 播放。
- 组合练习支持"生成短文 + 拼音注音开关 + 全文朗读 + 换一段"。
- 已学字 < 3 时组合练习禁用并给出引导。

**非目标**
- 不做多语言 TTS（仅普通话 zh-CN）。
- 不做 TTS 音色/语速自定义（固定 rate 0.85）。
- 不做题目/测验、错题本等更复杂的学习功能。
- 不做 practice 生成结果的持久化 / 收藏。

## 交互设计

### 页面结构

`HanziCharacterGridPage.tsx` 顶部加 Tab bar：`字表 | 随机学习 | 组合练习`。

Tab 状态用 URL query string `?tab=grid|random|practice`（默认 grid），刷新保留、可分享。

父组件 `HanziCharacterGridPage` 负责：
- 一次 fetch `getLevelCharacters(levelId)` → 拿到 level + characters + learned 状态
- 顶部保留返回链接 + 级别标题 + 学习进度条（三个 Tab 都可见）
- 根据当前 tab 渲染对应子组件，把 `level / characters / refresh` 作为 props 传下去
- 子组件调 `updateProgress` 后调用父层 `refresh()` 同步

### 随机学习子组件

**布局**（垂直居中大卡片）：

```
[ 换一个 ↻ ]                    [ 已学 X / 总 Y ]

           ┌──────────────┐
           │              │
           │      人       │  ← 200pt 汉字，font-semibold
           │              │
           │     rén       │  ← 24pt 拼音 text-muted
           │  🔊 读这个字   │  ← icon+文字复合按钮
           └──────────────┘

           例词
   ┌──────┐ ┌──────┐ ┌──────┐ ┌──────┐
   │🔊 人类 │ │🔊 大人│ │🔊 人口 │ │🔊 人们│
   └──────┘ └──────┘ └──────┘ └──────┘

             [ ✓ 标记为已学 ]
```

**行为**：
- 进入 Tab：从 `characters.filter(c => !c.learned)` 中 `Math.random()` 抽一个。
- 「换一个」：从剩余未学中随机选（若剩余只剩当前这个，允许保留）。
- 「读这个字」：调 `speak(char)`。
- 例词按钮：调 `speak(word)`；若例词为空则整个例词区块不渲染。
- 「标记为已学」：`updateProgress(id, true)`。成功后 300ms 短暂显示对勾反馈，然后自动切下一个未学字。
- **空态**（未学 = 0）：不渲染卡片，显示 `🎉 这一级都学完啦！[返回级别列表 ➜]`。

### 组合练习子组件

**布局**：

```
[ 拼音: 隐藏 ⇄ 显示 ]  [ 🔊 朗读全文 ]  [ ↻ 换一段 ]

┌────────────────────────────────────────┐
│                                        │
│  今天，妈妈带我去山上。山上有很多小 树,      │
│  还有 白 云 ，我们一家都很开心。              │
│                                        │
└────────────────────────────────────────┘

新字：[树] shù   [白] bái   [云] yún
```

**行为**：
- 前置：`characters.filter(c => c.learned).length < 3` → 不加载文本，显示引导卡片"再学 N 个字就能来这里练习啦（当前 X / 需要 3）"，并给一个"去学字表"按钮跳回 grid tab。
- 首次进入 Tab（满足前置条件）→ 自动调后端生成一段。
- **拼音开关**：默认「隐藏」。切到「显示」时每个汉字上方用 `<ruby><rt>` 显示拼音。
- **生词高亮**：`new_chars` 里的字用主题色 `text-primary` + 下方细虚线，悬停 tooltip 显示拼音。
- **换一段**：重新请求后端。loading 期间显示 skeleton + "AI 正在写句子…"。
- **朗读全文**：`speak(text)`，全段普通话朗读。

### TTS 封装（`utils/tts.ts`）

浏览器原生 `speechSynthesis`：

```ts
export function speak(text: string): void
```

内部：
- 挑选中文 voice：`voices.find(v => v.lang.startsWith('zh'))`；若首次 `getVoices()` 返回空，监听 `voiceschanged` 后重试一次。
- `utter.lang = 'zh-CN'; utter.rate = 0.85; utter.pitch = 1`。
- 播放前 `cancel()` 掉未完的以避免堆叠。

Web Speech 不可用（老浏览器 / 无中文语音）时静默 no-op，不阻塞交互；控制台一次 warning 提示即可。

## 后端设计

### API

```
POST /api/v1/hanzi/practice-text
Header: Authorization: Bearer <token>
Body: { "level_id": "<uuid>" }
Response:
{
  "code": 0,
  "data": {
    "text": "今天妈妈带我去山上。山上有很多小树……",
    "annotations": [
      {"char": "今", "pinyin": "jīn"},
      {"char": "天", "pinyin": "tiān"},
      ...
    ],
    "new_chars": ["树", "白", "云"]
  }
}
```

错误码：
- `2010` 级别不存在
- `2013` 已学字数不足（< 3）
- `5000` AI 生成失败 / 格式不合规

### 服务层

`HanziService` 新增方法：

```python
async def generate_practice_text(
    self, user_id: str, level_id: str
) -> dict:
    """基于用户已学字生成短文。"""
```

流程：
1. 校验 level 存在。
2. 从 `progress_repo` 获取该 user 在该 level 已学的 character_ids，再联表拿字 → `learned_chars: list[str]`。
3. `if len(learned_chars) < 3: raise ParamException(2013, ...)`。
4. 调 `self.ai.practice_text(learned_chars)` → `{text, annotations, new_chars}`。
5. 兜底：
   - `text` 为空 → 5000
   - `annotations` 缺失 → 允许（前端不显示注音即可），但保证 `annotations` 是 list
   - `new_chars` 若非 list 兜底为 `[]`

### AI Client

`OpenRouterAIClient` 新增：

```python
async def practice_text(self, learned_chars: list[str]) -> dict:
    """返回 {text, annotations: [{char, pinyin}], new_chars: [char]}."""
```

Prompt 大意（最终会调整措辞）：
- 你是儿童中文启蒙助手。
- 已学字：{learned_chars}
- 要求：生成一段 20-40 字的简单短句，主要使用已学字；允许 10-20% 常见简单新字（新字请列在 new_chars）。
- 内容适合 4-8 岁小朋友：日常生活、家庭、自然、动物、食物等主题。
- 严格返回 JSON：`{"text": "...", "annotations": [{"char": "字", "pinyin": "zì"}, ...], "new_chars": ["字1", "字2"]}`。
- annotations 对 text 中每个汉字都要给 pinyin（英文/标点跳过）。
- 使用 `response_format={"type": "json_object"}` + `JsonOutputParser`（与 `character_info` 相同套路）。

### 依赖注入

`get_hanzi_service` 目前不注入 `ai`。新增 `ai: AIClient` 参数（沿用现有 `get_ai_client_dep`）。

## 前端文件清单

**新增**：
- `frontend/src/components/hanzi/HanziGridTab.tsx`（把现有 grid 逻辑从页面里抽出来）
- `frontend/src/components/hanzi/HanziRandomTab.tsx`
- `frontend/src/components/hanzi/HanziPracticeTab.tsx`
- `frontend/src/utils/tts.ts`

**修改**：
- `frontend/src/pages/ai-tools/HanziCharacterGridPage.tsx` → 改成 Tab 容器
- `frontend/src/types/hanzi.ts` → 加 `PracticeTextResponse` / `PinyinAnnotation`
- `frontend/src/services/hanzi.ts` → 加 `getPracticeText(levelId)`
- `frontend/src/services/hanzi.mock.ts` → mock 版返回固定示例文本

## 后端文件清单

**新增**：
- `backend/tests/unit/test_practice_text.py`

**修改**：
- `backend/app/api/user/hanzi_router.py`（或复用现有 user-side hanzi router）→ 加 `POST /practice-text`
- `backend/app/schemas/hanzi.py` → 加 `PracticeTextRequest`
- `backend/app/service/hanzi_service.py` → `generate_practice_text` + 构造函数加 `ai: AIClient`
- `backend/app/api/dependencies.py` → `get_hanzi_service` 注入 ai
- `backend/app/service/openrouter_client.py` → `practice_text` + prompt
- `backend/app/core/exceptions.py` 或错误码常量 → 加 `2013`

## 风险 / 已考虑

- **AI 返回不合规**：`annotations` 数量与 text 汉字数量不一致 → 前端把 annotations 转成 `Map<char, pinyin>`，缺失时不显示注音（宁可不显示也不显示错的）。
- **AI 用未学字过多**：prompt 里明确 10-20% 上限，加"若失误请只在 new_chars 里列出这些字"；前端 `new_chars` 数组只用于高亮，不做二次校验。
- **TTS 首次调用无声**：`voiceschanged` 事件监听 + 一次重试；仍失败则 no-op。
- **组合练习 loading 体验**：AI 首字节 3-5s，用 skeleton + 文案 "AI 正在写句子…"，「换一段」按钮期间禁用。
- **Tab 切换重复请求**：只在 `HanziPracticeTab` 首次挂载或已学字数变化时请求；切回来不重复请求（组件 unmount 会失记忆——可接受，因为 practice 每次也应该是新内容）。**权衡**：状态用 URL query 保留，组件 remount 就重新请求；如果这个体验差可以后续升级到父组件 cache。当前 MVP 不做 cache。
- **`updateProgress` 完成到父组件 refresh 的延迟**：随机学习标记已学后依赖 refresh 更新已学计数——refresh 会重新拉整个 characters 列表，可能有 200ms 空窗。可接受，或改成本地乐观更新 + 后台 refresh（与现有 grid 一致的做法）。

## 测试策略

**后端单测**（`test_practice_text.py`）：
- 已学字不足 → 2013
- level 不存在 → 2010
- AI 正常返回 → 结构透传
- AI 返回缺 annotations → 兜底为 `[]`
- AI 抛异常 → 5000

**前端**：不写单测，靠手动验证 + tsc。

**手动验证清单**：
1. `?tab=random` 刷新保留
2. 未学字数 = 0 时随机学习显示空态
3. 已学字数 < 3 时组合练习显示引导
4. 随机学习"标记已学"后自动跳到下一个
5. 拼音注音开关切换正常
6. 生词高亮显示 pinyin tooltip
7. Web Speech 在 Chrome / Safari 都能出声
