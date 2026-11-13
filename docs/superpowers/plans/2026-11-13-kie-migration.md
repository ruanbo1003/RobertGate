# ai-videos 主通道迁移 kie.ai 实施计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 把 ai-videos 的 llm / t2i / i2v / tts 四条能力线从 OpenRouter 切到 kie.ai，单通道、无兜底。

**Architecture:** 新增 `KieAvClient` 实现与 `OpenRouterAvClient` 相同的五方法契约 —— llm 走 kie 的 OpenAI 兼容同步 `chat/completions`，t2i/i2v/tts 走 `jobs/createTask` 异步轮询（复用 `av_client_kie.py` 已踩通的上传/轮询/下载骨架）。模型注册表换成 kie 的裸 id；老项目落库的失效 id 在取用侧回退到新 default。`OpenRouterAvClient` 保留但只服务对白镜兜底。

**Tech Stack:** Python 3.11、FastAPI、httpx（`AsyncBaseTransport` 注入打桩）、pytest + pytest-asyncio、SQLAlchemy 2.0

**Spec:** `docs/superpowers/specs/2026-11-13-kie-migration-design.md`

## Global Constraints

- 遵循 `.claude/rules/backend.md`：DDD 分层，业务逻辑不进 `infrastructure/`，新功能必须附带单元测试，覆盖率目标 80%+。
- 上游失败一律抛 `ServerException`：余额/Key 全局性错误用 `codes.AV_UPSTREAM_QUOTA`，其余用 `codes.AV_UPSTREAM_FAILED`。
- **不改端口契约 `ports.py`**，不改 `av_queue` 调度与并发（`_LIMITS`）、`av_dialogue`、合成管线、前端交互。唯一允许的越界点是 `docker/nginx.conf` 超时配置。
- **不删 `OpenRouterAvClient`**，它仍是对白镜 `DialogueVideoRouter` 的兜底。四条线不再经过它。
- 四条线用 **kie 裸模型 id**，不加渠道前缀。`dialogue_video` 段的 `kie:` / `openrouter:` tag 格式维持现状不动。
- 测试一律用 `httpx.AsyncBaseTransport` 打桩，不打真实网络。Task 1 是唯一的真机环节。
- **第四轮修订（tts 剔除 + 探测结论，覆盖以下各任务原文）**：
  - Task 2：注册表 **tts 段原样不动**；llm 换 `gemini-3-8-flash-openai`；t2i 换 `nano-banana-2`(multi) + `seedream/5-5-text-to-image`(省钱档)；i2v 换 `bytedance/seedance-2-fast`，durations 用已验证的 **[4,5,6,8]**（10s+ 待充值后补探）。
  - Task 3/4：**kie HTTP 恒 200、错误码在 body `code`** —— 错误判定必须读 body；recordInfo 响应体可能非法 JSON（param 字段），解析必须容错。
  - Task 4：**不实现 generate_speech 的真实链路** —— 方法保留（Protocol 要求）但直接抛 `ServerException(AV_UPSTREAM_FAILED, "TTS 链路已退役")`；相关测试改为断言该行为。
  - Task 6：活配置回退只覆盖 llm/t2i/i2v；**tts_voice 回退取消**（tts 注册表没动，老值仍"合法"，且链路已死）。
  - Task 7：无 OPENROUTER_API_KEY 时对白镜兜底缺席——`DialogueVideoRouter` 需支持 fallback 为 None（primary 异常直接冒泡）。
  - Task 9：去掉 TTS 联调步骤。

## Review Focus

spec 隐含但各任务测试未必覆盖的失败模式，按可能咬人的程度排序。每条已在下方对应任务里安排了测试：

1. **`snap_duration` / `reference_mode` 精确匹配落空后静默降级** —— 注册表换 id 后若调用侧传的还是老 id，前者悄悄掉进 `max(2, min(10, s))`，后者 `return "none"` 让角色跨镜变脸。**两者都不报错、不告警**。测试归 Task 2。
2. **对白镜兜底在装配改造中被静默摘掉** —— 砍四条线兜底时顺手把 `OpenRouterAvClient` 从装配里拿掉，对白镜兜底就没了，而这只有在 kie 挂掉时才暴露。测试归 Task 7。
3. **ElevenLabs 返回格式若不是 mp3** —— `av_queue._EXT[AssetKind.AUDIO]` 硬编码 `mp3`，合成管线按扩展名找文件。格式不符要在客户端内转码，不是改扩展名。测试归 Task 4。
4. **kie 多参考图可能要求先上传拿 URL** —— 不像 OpenRouter 可直接塞 data URL。上传失败需映射成 `AV_UPSTREAM_FAILED` 而非静默丢参考图（静默丢 = 角色变脸）。测试归 Task 4。
5. **kie 轮询返回未知 state** —— 现有代码只认 success/fail，未知值会一路轮到超时且不留线索。应继续轮询但在超时消息里带上最后一次 state。测试归 Task 4。

---

### Task 1: 真机探测（唯一的网络环节，产出后续任务的输入）

**Files:**
- Modify: `docs/superpowers/specs/2026-11-13-kie-migration-design.md`（追加"## 真机探测结果"一节）

**Interfaces:**
- Produces: 探测结果表，后续 Task 2/4/5 直接引用其中的模型 id、duration 档位、voice_id 清单、端点 URL、请求体字段名。

- [x] **Step 1: 先查余额并报给 Robert**

Run: `curl -s -H "Authorization: Bearer $KIE_API_KEY" https://api.kie.ai/api/v1/chat/credit`
把余额数字发给 Robert 再继续。**余额不足以覆盖探测开销时停下来问** —— 打到 402 会让生产的对白镜生成触发全局暂停。

- [x] **Step 2: 逐条探测，每条记录「实际请求体 + 实际响应」**

| # | 探什么 | 怎么探 | 不确定就停 |
|---|---|---|---|
| 1 | Chat 端点 URL、JSON 模式字段 | 最小 chat 调用，试 `response_format: {"type":"json_object"}` | |
| 2 | **Nano Banana 2 多参考图** | 传 2 张参考图生成一张 | **喂不进就停下来回报 Robert，不要降级成 `none`** |
| 3 | 9:16 竖屏怎么传 | 生成 1 张，核对返回尺寸 | 比例错了整条产线作废 |
| 4 | i2v duration 档位 | 触发 400 读允许值 | |
| 5 | ElevenLabs voice_id 清单 + **返回音频格式** | 查模型详情，生成 1 条最短音频 | 格式非 mp3 记进表（Review Focus 3） |
| 6 | 配额/鉴权错误码 + **限流 429 响应体** | 用错 Key 触发 401 | 429 体里有无 `balance`/`credit` 决定 Task 3 的判别式 |
| 7 | **t2i 单图实际耗时** + 有无同步端点 | 计时 | **接近 180s 就停下来回报**：nginx 方案不成立 |

- [x] **Step 3: 把结果写进设计文档并提交**

每条带上实际请求体与响应片段。后续任务**只准引用这一节，不准照着猜测写**。

```bash
git add docs/superpowers/specs/2026-11-13-kie-migration-design.md
git commit -m "docs(av): kie.ai 真机探测结果"
```

---

### Task 2: 模型注册表换 kie id

**Files:**
- Modify: `backend/app/infrastructure/data/av_models.py`
- Test: `backend/tests/unit/test_av_models.py`

**Interfaces:**
- Consumes: Task 1 探测表的模型 id、duration 档位、voice_id 清单
- Produces: `AV_MODELS` 四条线换 kie 裸 id；`is_known_model(model_type: str, model_id: str) -> bool` 供 Task 6 使用；`default_model` / `reference_mode` / `snap_duration` / `default_voice` 签名不变

- [ ] **Step 1: 写失败测试**

```python
def test_reference_mode_resolves_for_new_default_t2i():
    # Review Focus 1：匹配落空会静默返回 "none"，角色跨镜变脸
    assert reference_mode(default_model("t2i")) == "multi"

def test_snap_duration_resolves_for_new_default_i2v():
    # 匹配落空会静默掉进 max(2, min(10, s))
    # 期望值取自 Task 1 探测表第 4 条
    assert snap_duration(default_model("i2v"), 12) == 12

def test_is_known_model_rejects_retired_openrouter_id():
    assert is_known_model("t2i", "google/gemini-3.1-flash-image") is False

def test_is_known_model_accepts_current_default():
    assert is_known_model("t2i", default_model("t2i")) is True

def test_dialogue_video_segment_keeps_channel_tags():
    # 对白镜是真·跨渠道段，格式不动
    assert any(m["id"].startswith("kie:") for m in AV_MODELS["dialogue_video"])
```

- [ ] **Step 2: 运行确认失败**

Run: `cd backend && uv run pytest tests/unit/test_av_models.py -v`
Expected: FAIL（`is_known_model` 未定义）

- [ ] **Step 3: 实现**

按设计文档"模型选型"表与 Task 1 探测结果重排 llm/t2i/i2v/tts 四段：换成 kie 裸 id，省钱档（Seedream 5.5、ElevenLabs Turbo 2.5）加入但不设 `default`，tts 的 `voices` 换成探测到的 voice_id 清单，i2v 的 `durations` 换成探测到的档位。**`dialogue_video` 段一行不动。** 新增 `is_known_model`。

- [ ] **Step 4: 运行确认通过**

Run: `cd backend && uv run pytest tests/unit/test_av_models.py -v`
Expected: PASS

- [ ] **Step 5: 提交**

```bash
git add backend/app/infrastructure/data/av_models.py backend/tests/unit/test_av_models.py
git commit -m "feat(av): 模型注册表切换到 kie.ai 模型"
```

---

### Task 3: kie 429 语义拆分

**Files:**
- Modify: `backend/app/infrastructure/ai/av_client_kie.py:38-43`（`_raise_upstream`）
- Test: `backend/tests/unit/test_av_client_kie.py`

**Interfaces:**
- Produces: `_raise_upstream(resp, what)` 行为变更，Task 4 的新客户端共用

- [ ] **Step 1: 写失败测试**

```python
def test_429_with_balance_keyword_is_quota():
    # 响应体带 balance/credit → 全局暂停
    ...assert exc.value.code == codes.AV_UPSTREAM_QUOTA

def test_429_rate_limit_is_plain_failure():
    # 纯限流 429 → 单产物失败，不得全局暂停整条产线
    ...assert exc.value.code == codes.AV_UPSTREAM_FAILED

def test_401_and_402_remain_quota():
    ...
```

- [ ] **Step 2: 运行确认失败**

Run: `cd backend && uv run pytest tests/unit/test_av_client_kie.py -v`
Expected: FAIL（429 当前一律映射成 QUOTA）

- [ ] **Step 3: 实现**

按 `av_client_openrouter.py:79-83` 的既有判别式改写：401/402 恒为 QUOTA；429 仅当响应体小写含 `balance` 或 `credit` 时为 QUOTA，否则 `AV_UPSTREAM_FAILED`。判别关键字以 Task 1 探测第 6 条的实际响应体为准。

- [ ] **Step 4: 运行确认通过 + 跑对白镜测试确认无回归**

Run: `cd backend && uv run pytest tests/unit/test_av_client_kie.py tests/unit/test_av_dialogue_router.py -v`
Expected: PASS

- [ ] **Step 5: 提交**

```bash
git add backend/app/infrastructure/ai/av_client_kie.py backend/tests/unit/test_av_client_kie.py
git commit -m "fix(av): kie 限流 429 不再触发队列全局暂停"
```

---

### Task 4: KieAvClient 的 t2i / i2v / tts（异步 jobs 三方法）

**Files:**
- Create: `backend/app/infrastructure/ai/av_client_kie_av.py`
- Test: `backend/tests/unit/test_av_client_kie_av.py`

**Interfaces:**
- Consumes: Task 3 的 `_raise_upstream`、`av_client_kie.py` 的上传/轮询/下载私有方法、Task 2 的 `snap_duration`
- Produces: `KieAvClient` 三方法，签名与 `OpenRouterAvClient` 对应方法**逐字一致**（端口契约不变）：
  - `generate_image(prompt: str, model: str, reference_images: list[bytes] | None = None) -> bytes`
  - `generate_video(image: bytes, prompt: str, model: str, duration_seconds: int = 5, generate_audio: bool = False) -> bytes`
  - `generate_speech(text: str, model: str, voice: str) -> bytes`
  - 构造参数含 `image_poll_interval: float = 2.5`（图像轮询，区别于视频沿用的 10s）

- [ ] **Step 1: 写失败测试**

```python
async def test_generate_image_passes_multiple_reference_images():
    # Review Focus 4：参考图必须真的抵达上游
    ...assert len(captured_refs) == 2

async def test_generate_image_upload_failure_raises_not_silently_drops():
    # 静默丢参考图 = 角色变脸
    ...assert exc.value.code == codes.AV_UPSTREAM_FAILED

async def test_generate_image_uses_short_poll_interval():
    ...assert client._image_poll_interval == 2.5

async def test_unknown_poll_state_keeps_polling_and_reports_last_state():
    # Review Focus 5：超时消息要带最后一次 state
    ...assert "weird_state" in exc.value.message

async def test_generate_speech_returns_mp3_bytes():
    # Review Focus 3：非 mp3 要在客户端内转码，不是改扩展名
    ...assert out.startswith(b"ID3") or out[:2] == b"\xff\xfb"

async def test_generate_video_snaps_duration_to_model_ladder():
    ...

async def test_quota_status_propagates():
    ...assert exc.value.code == codes.AV_UPSTREAM_QUOTA
```

- [ ] **Step 2: 运行确认失败**

Run: `cd backend && uv run pytest tests/unit/test_av_client_kie_av.py -v`
Expected: FAIL（模块不存在）

- [ ] **Step 3: 实现三方法**

请求体字段名、参考图传法（直传 bytes 还是先上传拿 URL）、9:16 的传法、duration 字段 —— **全部以 Task 1 探测表为准**。
`generate_speech`：若探测第 5 条显示返回非 mp3，在客户端内用 `av_client_openrouter.py:44` 的 `_pcm16_to_mp3` 同款 ffmpeg 子进程转成 mp3 再返回。`AV_TTS_TEMPO != 1.0` 时附加 `atempo` 滤镜；`== 1.0` 且已是 mp3 时直接返回，不空跑 ffmpeg。
不再需要 `_SPEECH_SYSTEM` 的 "Repeat after me" 包裹（ElevenLabs 是纯 TTS，不会把台词当提问）。

- [ ] **Step 4: 运行确认通过**

Run: `cd backend && uv run pytest tests/unit/test_av_client_kie_av.py -v`
Expected: PASS

- [ ] **Step 5: 提交**

```bash
git add backend/app/infrastructure/ai/av_client_kie_av.py backend/tests/unit/test_av_client_kie_av.py
git commit -m "feat(av): KieAvClient 的 t2i/i2v/tts 三方法"
```

---

### Task 5: KieAvClient 的 generate_json（同步 chat 端点）

**Files:**
- Modify: `backend/app/infrastructure/ai/av_client_kie_av.py`
- Modify: `backend/app/config.py`（新增 `KIE_CHAT_BASE_URL`）
- Test: `backend/tests/unit/test_av_client_kie_av.py`

**Interfaces:**
- Produces: `generate_json(system: str, user: str, model: str) -> dict`

- [ ] **Step 1: 写失败测试**

```python
async def test_generate_json_parses_content():
    ...assert out == {"scenes": []}

async def test_generate_json_raises_on_malformed_json():
    ...assert exc.value.code == codes.AV_UPSTREAM_FAILED

async def test_generate_json_hits_chat_base_not_jobs_base():
    # chat 与 jobs 不同源，走错 base 会 404
    ...assert captured_url.startswith("https://kie.test/v1")
```

- [ ] **Step 2: 运行确认失败**

Run: `cd backend && uv run pytest tests/unit/test_av_client_kie_av.py -k json -v`
Expected: FAIL

- [ ] **Step 3: 实现**

端点 URL 与 JSON 模式字段以 Task 1 探测第 1 条为准。结构可照 `av_client_openrouter.py:280-299` 平移（`temperature: 0.7`，解析 `choices[0].message.content` 后 `json.loads`）。`config.py` 新增 `KIE_CHAT_BASE_URL: str`，默认值取探测结果。

- [ ] **Step 4: 运行确认通过**

Run: `cd backend && uv run pytest tests/unit/test_av_client_kie_av.py -v`
Expected: PASS

- [ ] **Step 5: 提交**

```bash
git add backend/app/infrastructure/ai/av_client_kie_av.py backend/app/config.py backend/tests/unit/test_av_client_kie_av.py
git commit -m "feat(av): KieAvClient 的 generate_json"
```

---

### Task 6: 活配置校验回退

**Files:**
- Modify: `backend/app/application/services/av_service.py:526`、`:555`（`effective_model`）
- Modify: `backend/app/application/services/av_queue.py:276`（`voice`）
- Test: `backend/tests/unit/test_av_service.py`、`backend/tests/unit/test_av_queue.py`

**Interfaces:**
- Consumes: Task 2 的 `is_known_model` / `default_model` / `default_voice`

- [ ] **Step 1: 写失败测试**

```python
async def test_legacy_project_default_model_falls_back_to_new_default():
    # 老项目存的是已死的 OpenRouter 闭源模型，不回退则每次生成必失败
    project.default_models = {"t2i": "google/gemini-3.1-flash-image"}
    ...assert used_model == default_model("t2i")

async def test_legacy_tts_voice_falls_back_to_new_default():
    shot.audio_voice = "alloy"
    ...assert used_voice == default_voice()

async def test_known_model_is_used_as_is():
    ...
```

- [ ] **Step 2: 运行确认失败**

Run: `cd backend && uv run pytest tests/unit/test_av_service.py tests/unit/test_av_queue.py -v`
Expected: FAIL

- [ ] **Step 3: 实现**

取用侧加一层校验：`is_known_model(line, value)` 为假则回退到 `default_model(line)` 并打 info 日志（带原值，便于排查有多少老项目在走回退）。音色同理用 `default_voice()`。**不写库、不加 alembic** —— 用户在工作台改一次模型就会自然写入新 id。

- [ ] **Step 4: 运行确认通过**

Run: `cd backend && uv run pytest tests/unit/test_av_service.py tests/unit/test_av_queue.py -v`
Expected: PASS

- [ ] **Step 5: 提交**

```bash
git add backend/app/application/services/ backend/tests/unit/
git commit -m "feat(av): 老项目失效模型/音色读取时回退新默认"
```

---

### Task 7: 工厂装配

**Files:**
- Modify: `backend/app/infrastructure/ai/av_client.py:134-175`（`get_av_client`）
- Test: `backend/tests/unit/test_av_client_factory.py`

**Interfaces:**
- Consumes: Task 4/5 的 `KieAvClient`

- [ ] **Step 1: 写失败测试**

```python
def test_kie_key_wires_kie_as_base_client():
    ...assert isinstance(client._base, KieAvClient)

def test_openrouter_client_still_serves_dialogue_fallback():
    # Review Focus 2：砍四条线兜底时极易顺手摘掉它，
    # 对白镜兜底就没了，而且只有 kie 挂掉时才暴露
    ...assert client._router._fallback_tag == "openrouter:bytedance/seedance-2.0-fast"

def test_no_kie_key_returns_mock():
    # kie 是唯一通道，没有它就没有主通道
    ...assert isinstance(get_av_client(), MockAvClient)

def test_openrouter_only_returns_mock():
    ...assert isinstance(get_av_client(), MockAvClient)
```

- [ ] **Step 2: 运行确认失败**

Run: `cd backend && uv run pytest tests/unit/test_av_client_factory.py -v`
Expected: FAIL

- [ ] **Step 3: 实现**

主通道判据由 `OPENROUTER_API_KEY` 改为 `KIE_API_KEY`：有 kie → `base = KieAvClient(...)`；无 kie → `MockAvClient`。
**`OpenRouterAvClient` 的构造保留**，但只传给 `DialogueVideoRouter` 的 `_fallback_video`，不再作为 `base`。`AvClientWithDialogue` 与 `MockAvClient` 不动。

- [ ] **Step 4: 跑全部 av 测试确认无回归**

Run: `cd backend && uv run pytest tests/unit/ -k av -v`
Expected: PASS

- [ ] **Step 5: 提交**

```bash
git add backend/app/infrastructure/ai/av_client.py backend/tests/unit/test_av_client_factory.py
git commit -m "feat(av): 工厂改 kie 为主通道，OpenRouter 仅留对白镜兜底"
```

---

### Task 8: nginx 超时、API 文档与 openapi baseline

**Files:**
- Modify: `docker/nginx.conf`
- Modify: `docs/api/ai-videos.md`
- Modify: `backend/tests/smoke/` 下的 openapi baseline
- Modify: `frontend/src/services/aiVideos.mock.ts`（mock 数据里的模型 id）

- [ ] **Step 1: 加长角色设定图路径的 `proxy_read_timeout` 到 180s**

仅针对 `/api/v1/ai-videos/characters/` 路径段，不要全局放宽。
**若 Task 1 探测第 7 条测出单图耗时接近 180s，停下来回报 Robert** —— 说明该方案不成立，需回到"改异步 + 前端轮询"。

- [ ] **Step 2: 更新 `docs/api/ai-videos.md` 里 `GET /ai-videos/models` 的模型清单与示例**

- [ ] **Step 3: 跑 smoke 测试，按失败提示更新 openapi baseline**

Run: `cd backend && uv run pytest tests/smoke/ -v`

- [ ] **Step 4: 同步前端 mock 数据里的模型 id**

- [ ] **Step 5: 跑全量测试与前端检查**

Run: `cd backend && uv run pytest`
Run: `cd frontend && npm run type-check && npm run lint`
Expected: 全绿

- [ ] **Step 6: 提交**

```bash
git add docker/nginx.conf docs/api/ai-videos.md backend/tests/smoke/ frontend/src/services/aiVideos.mock.ts
git commit -m "chore(av): nginx 超时、API 文档与 openapi baseline 同步"
```

---

### Task 9: 端到端联调验证

**Files:** 无代码改动，产出验证记录

- [ ] **Step 1: 起后端，四条线各跑通一次**

角色设定图（同步路径，**计时确认不超时**）→ 分镜图（**带参考图，肉眼核对角色一致性**）→ i2v → TTS。

- [ ] **Step 2: 确认对白镜链路无回归**

跑一个对白镜，确认仍走 kie `gemini-omni-video`，且 `shot.video_model` 落的是 `kie:gemini-omni-video`。

- [ ] **Step 3: 确认老项目可用**

拿一个迁移前建的项目直接点生成，确认活配置回退生效、不报错。

- [ ] **Step 4: 把验证结果与实测耗时/成本追加到设计文档并提交**
