# 翻译 API 接入 OpenRouter（LangChain）设计文档

日期：2026-08-05

## 背景

`/ai-tools/translate` 页面（`frontend/src/pages/ai-tools/TranslatePage.tsx`）已完成，通过 `POST /api/v1/ai/translate` 调用后端。后端目前 `TranslateService` 依赖 `MockAIClient`，返回确定性假数据。本次任务：把 AI 调用换成基于 **LangChain + OpenRouter** 的真实实现，支持三个动作：`translate`、`grammar`、`native`。

## 目标

- 不改动前端契约、`schemas`、路由、`TranslateService`。
- 新增一个实现 `AIClient` Protocol 的 `OpenRouterAIClient`。
- Prompt 写成中文 system message，要求模型只输出结果本身，不加解释。
- 配置项从 `.env.local` 读取，**不硬编码 key 或模型名**。
- 提供本地测试脚本，先在命令行跑通再接入服务。

## 非目标

- 不做流式响应（当前前端为一次性返回）。
- 不做多语种扩展（只支持 zh ↔ en）。
- 不做 rate limit / cache / 计费统计。
- 不改 `character_info`、`compose_sentence`、`generate_image` 等其它 AI 能力，本次只覆盖 3 个翻译动作。

## 涉及文件

新增：
- `backend/app/service/openrouter_client.py`：新的 `OpenRouterAIClient` 实现。
- `backend/scripts/test_translate.py`：本地手工测试脚本。
- `backend/.env.local`：本地环境变量（不提交，含 API key）。

修改：
- `backend/requirements.txt`：添加 `langchain`、`langchain-openai`。
- `backend/app/core/setting.py`：新增 `OPENROUTER_API_KEY`、`OPENROUTER_MODEL`、`OPENROUTER_BASE_URL`。
- `backend/app/service/ai_client.py`：修改 `get_ai_client()`，`OPENROUTER_API_KEY` 有值时返回 `OpenRouterAIClient`，否则保持 `MockAIClient`。

## 配置

`Settings` 新增字段：

```python
OPENROUTER_API_KEY: str = ""
OPENROUTER_BASE_URL: str = "https://openrouter.ai/api/v1"
OPENROUTER_MODEL: str = "z-ai/glm-4.6"  # 默认 4.6，可通过 .env.local 覆盖为 z-ai/glm-5.2
```

`.env.local` 示例：

```
OPENROUTER_API_KEY=sk-or-v1-xxxxxxxx
OPENROUTER_MODEL=z-ai/glm-4.6
```

## `OpenRouterAIClient` 设计

```python
class OpenRouterAIClient:
    def __init__(self, api_key: str, model: str, base_url: str) -> None:
        self._llm = ChatOpenAI(
            model=model,
            api_key=api_key,
            base_url=base_url,
            temperature=0.3,
            timeout=30,
        )

    async def translate(self, text: str) -> tuple[str, str, str]:
        # Python 侧判定方向
        if _is_chinese(text):
            source, target = "zh", "en"
            direction_hint = "中文翻译成英文"
        else:
            source, target = "en", "zh"
            direction_hint = "英文翻译成中文"
        result = await self._run(TRANSLATE_PROMPT, {"text": text, "direction": direction_hint})
        return source, target, result

    async def grammar_correct(self, text: str) -> str:
        return await self._run(GRAMMAR_PROMPT, {"text": text})

    async def rewrite_native(self, text: str) -> str:
        return await self._run(NATIVE_PROMPT, {"text": text})

    async def _run(self, prompt: ChatPromptTemplate, vars: dict) -> str:
        chain = prompt | self._llm | StrOutputParser()
        out = await chain.ainvoke(vars)
        return out.strip()

    # 其余 Protocol 方法（character_info / compose_sentence / generate_image）
    # 本次不实现，暂时 raise NotImplementedError（不影响翻译流程；
    # 其它模块用到 AI 时若走 mock 分支即可，或后续单独实现）。
```

**注**：`AIClient` 是 Protocol，不强制实现全部方法即可通过静态检查，但运行时若被调用会 AttributeError。为避免影响到 `hanzi`、`t2i` 等模块（它们目前依赖同一个 `get_ai_client()` 拿到的 mock 客户端），此次改造需保证：**只有翻译走真实 client**。

**方案**：`get_ai_client()` 保持返回 `MockAIClient`；新增 `get_translate_ai_client()`，仅供 `TranslateService` 使用。或者更简单：`OpenRouterAIClient` 组合一个 `MockAIClient` 作为后备，未实现方法委托给 mock。采用后者以最小改动 `dependencies.py`。

## Prompt 设计（中文）

三个 prompt 都遵循同一原则：**system 指令严格要求"只输出结果，不要解释、不要引号、不要 markdown"**。

### translate

```
system:
你是一名专业翻译。请把下面的文本进行{direction}。
要求：
1. 只输出翻译结果本身，不要添加任何解释、注释、引号或 markdown。
2. 保留原文的语气、标点风格和段落结构。
3. 遇到专有名词、代码、数字、URL 保持不变。

user:
{text}
```

### grammar

```
system:
你是一名英语语言老师。请修正下面这段英文的语法、拼写和用词错误。
要求：
1. 只输出修正后的完整文本，不要解释、不要标注修改位置、不要 markdown。
2. 保留原意和作者的语气，不要过度改写。
3. 如果原文没有错误，原样返回。

user:
{text}
```

### native

```
system:
你是一位英语母语作家。请把下面这段英文改写得更地道、自然、符合母语者表达习惯。
要求：
1. 只输出改写后的完整文本，不要解释、不要 markdown、不要引号。
2. 意思不变，风格可以更自然口语化或书面化，视原文场景而定。
3. 避免过度修饰，保持简洁清晰。

user:
{text}
```

## 依赖

`requirements.txt` 追加：

```
langchain==0.3.7
langchain-openai==0.2.8
```

## 错误处理

- `OpenRouterAIClient._run` 内如抛异常，向上冒泡到 `TranslateService.process`，已有 `except Exception -> ServerException(5001)` 兜底，前端会拿到 `code=5001, message="AI 服务不可用: ..."`。
- 无 key（开发环境未配置）时 `get_ai_client()` 走 mock 分支，翻译返回 mock 数据，服务不会挂。

## 本地测试步骤

1. `cp` 出 `backend/.env.local` 并写入 key 与模型。
2. `uv pip install -r backend/requirements.txt` 安装新依赖。
3. `cd backend && uv run python scripts/test_translate.py`
   - 脚本内容：分别用 `translate` / `grammar` / `native` 跑一个样例（"你好世界"、"He go to school every days"、"The meeting is very good and I feel happy"），打印结果。
4. 通过后启动后端：`uv run uvicorn app.main:app --reload`
5. `curl -X POST http://localhost:8000/api/v1/ai/translate -H 'Content-Type: application/json' -d '{"text":"你好世界","action":"translate"}'` 验证端到端。

## 验收标准

- `.env.local` 未配置 key 时，翻译接口返回 mock 数据（回归不破坏）。
- `.env.local` 配置 key 后，`scripts/test_translate.py` 三个动作输出真实、非 mock、无解释性前后缀的结果。
- 前端页面点击「翻译 / 语法修正 / 改地道」三个按钮均能拿到真实 AI 返回，展示在结果卡上。
- `z-ai/glm-4.6` 走通后，改配置到 `z-ai/glm-5.2` 观察是否返回 400（模型不存在）或正常响应，用于确认真实模型 slug。
