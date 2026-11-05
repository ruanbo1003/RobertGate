# AI Videos 多 Provider（OpenRouter）+ video_prompt 实现计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** ai-videos 工作台支持 OpenRouter/SiliconFlow 双 provider（默认全切 OpenRouter），分镜图多参考图保角色一致性，每镜新增 video_prompt 动作/运镜提示用于图生视频。

**Architecture:** 模型注册表（`av_models.py`）每条带 `provider` 与 `reference` 能力档；`RoutingAvClient` 按模型路由到 `SiliconFlowAvClient` / 新增 `OpenRouterAvClient`；`AvShot` 的 `ref_character_id` 升级为 `ref_character_ids` 列表并新增 `video_prompt`（由生成剧本的 LLM 按句产出，拆分镜保持确定性映射）；队列生成时按模型能力三档降级动态拼装参考图与点名文本；合成分段统一归一化到 720x1280。

**Tech Stack:** FastAPI + SQLAlchemy 2.0 + Alembic + httpx（后端），React 18 + TS（前端），pytest + httpx.MockTransport（测试）。

**Spec:** docs/superpowers/specs/2026-11-05-ai-videos-openrouter-design.md

## Global Constraints

- API 统一 `/api/v1` 前缀与 `{code, data, message}` 包装；错误码常量只在 `app/domain/errors.py` 的 `codes` 维护。
- DDD 分层：domain 无 FastAPI/infrastructure 依赖；routers 只做校验+调用 service；事务边界在 service（UoW 一用例一 commit）。
- 新 Key 配置名 `OPENROUTER_API_KEY`（`backend/.env.local`，不入库）；`LLM_API_KEY`/`LLM_BASE_URL`（SiliconFlow）保留。
- 两把 Key 都未配 → 整体 `MockAvClient`；只缺一把 → 仅该 provider 模型调用报 `AV_UPSTREAM_FAILED`（提示写明缺哪个环境变量）；启动永不报错。
- OpenRouter 画幅统一 `aspect_ratio: "9:16"`；视频 `resolution: "720p"`；SiliconFlow 保留 `AV_IMAGE_SIZE=720x1280`。
- 上游 401/402（及 429+balance）→ `codes.AV_UPSTREAM_QUOTA`（队列全局暂停语义不变），其余上游错误 → `codes.AV_UPSTREAM_FAILED`。
- 前端禁止硬编码颜色/新字体（`.claude/rules/ui-style.md`）；`npx tsc -b --noEmit` 与 `npm run lint` 必须通过。
- 每个任务结束 `uv run pytest tests/unit tests/smoke -q` 全绿再 commit；commit message 遵循仓库惯例（中文 feat/fix/test 前缀）。

## Review Focus

1. OpenRouter 视频任务轮询到 `status: "failed"` → 必须抛可读 `AV_UPSTREAM_FAILED`（含上游 reason），而不是空转到超时 —— 测试在 Task 2。
2. gpt-audio 流式响应一个音频块都没给（纯文本回复）→ 必须报错，不能落一个 0 字节/纯 ID3 头的假 mp3 —— 测试在 Task 2。
3. `images` 响应缺 `b64_json`（部分 provider 只回 `url`）→ 回退按 `url` 下载，两者都缺才报错 —— 测试在 Task 2。
4. 出场角色里有人没有封面图（刚建的角色）→ multi/single 档对该角色降级为外形描述拼 prompt，不崩、不发空参考图 —— 测试在 Task 6。
5. LLM 剧本里 `characters` 名字匹配不到项目角色（大小写/别名）→ 名字忽略、镜回退 `[speaker_id]`，拆分镜不失败 —— 测试在 Task 4。

---

### Task 1: 模型注册表多 provider 化

**Files:**
- Modify: `backend/app/infrastructure/data/av_models.py`
- Modify: `backend/app/interfaces/api/deps.py:34,88`（import/注入点随新函数名）
- Test: `backend/tests/unit/test_av_models.py`（新建）

**Interfaces:**
- Produces: `AV_MODELS: dict[str, list[dict]]`（每条新增 `provider: "openrouter"|"siliconflow"`；t2i 条目 `reference: "multi"|"single"|"none"` 取代 `supports_reference`）；`default_model(model_type) -> str`、`default_voice() -> str` 签名不变；新函数 `model_provider(model_id: str) -> str`（全类型查找，未知模型返回 `"siliconflow"` 兜底）、`reference_mode(model_id: str) -> str`（非 t2i/未知返回 `"none"`）；删除 `supports_reference`。

- [ ] **Step 1: 写失败测试** `tests/unit/test_av_models.py`：

```python
def test_every_entry_has_provider():
    for entries in AV_MODELS.values():
        for m in entries:
            assert m["provider"] in ("openrouter", "siliconflow")

def test_defaults_are_openrouter():
    for t in ("llm", "t2i", "i2v", "tts"):
        assert model_provider(default_model(t)) == "openrouter"

def test_reference_mode():
    assert reference_mode("google/gemini-3.1-flash-image") == "multi"
    assert reference_mode("Kwai-Kolors/Kolors") == "single"
    assert reference_mode("Qwen/Qwen-Image") == "none"
    assert reference_mode("unknown/x") == "none"

def test_default_voice_matches_default_tts_model():
    tts = next(m for m in AV_MODELS["tts"] if m.get("default"))
    assert default_voice() == tts["voices"][0]
```

- [ ] **Step 2: 跑测试确认失败**（`uv run pytest tests/unit/test_av_models.py -q`，Expected: FAIL/ImportError）
- [ ] **Step 3: 改写 `av_models.py`**。条目（slug 以 Task 11 真机核实为准，注释标注"待 Task 11 验证"）：
  - llm：`google/gemini-3-flash`（default）、`deepseek/deepseek-v3.2`（均 openrouter）；保留现有两条 SiliconFlow。
  - t2i：`google/gemini-3.1-flash-image`（default, multi）、`google/gemini-3-pro-image`（multi）、`google/gemini-nano-banana-2.1`（multi）；现有 Kolors 改 `reference: "single"`，Qwen-Image/Z-Image×2 改 `reference: "none"`（均 siliconflow，保留原注释）。
  - i2v：`bytedance/seedance-2.0-fast`（default）、`alibaba/wan-3.0`、`kwaivgi/kling-v3.0-std`、`google/veo-3.1-fast`（openrouter）；保留两条 SiliconFlow Wan。
  - tts：`openai/gpt-audio`（default, `voices: ["alloy","echo","fable","onyx","nova","shimmer"]`）、`openai/gpt-audio-mini`（同 voices）（openrouter）；保留 CosyVoice（siliconflow，voices 不变）。
  - `default_voice()` 改为取 default tts 条目的首个 voice。
  - `deps.py` 的 `supports_reference` import/注入暂改为 `reference_mode`（queue 侧签名 Task 6 才换，此处先让两个名字都可用：保留一个 `supports_reference = lambda m: reference_mode(m) != "none"` 的过渡 shim 于 deps 内，Task 6 删除）。
- [ ] **Step 4: 跑全量单测确认通过**（`uv run pytest tests/unit -q`，Expected: PASS）
- [ ] **Step 5: Commit**（`feat(ai-videos): 模型注册表多 provider 化 + reference 三档`）

### Task 2: OpenRouter 客户端

**Files:**
- Modify: `backend/app/config.py`（`OPENROUTER_API_KEY: str = ""`、`OPENROUTER_BASE_URL: str = "https://openrouter.ai/api/v1"`，放在 LLM 配置旁）
- Create: `backend/app/infrastructure/ai/av_client_openrouter.py`
- Test: `backend/tests/unit/test_av_client_openrouter.py`（新建）

**Interfaces:**
- Produces: `class OpenRouterAvClient`，构造 `__init__(self, api_key: str, base_url: str, transport: httpx.AsyncBaseTransport | None = None)`（transport 供测试注入 `httpx.MockTransport`）。方法即新版 `AvGenClient` 契约（见 Task 3）：
  - `generate_image(prompt, model, reference_images: list[bytes] | None = None) -> bytes`：`POST {base}/images`，body `{model, prompt, aspect_ratio: "9:16", n: 1}` + 非空参考时 `input_references: [{type:"image_url", image_url:{url:"data:image/png;base64,..."}}...]`；响应取 `data[0].b64_json` 解码，缺失则回退 `data[0].url` 下载，两者皆缺抛 `AV_UPSTREAM_FAILED`。
  - `generate_video(image, prompt, model, duration_seconds: int) -> bytes`：`POST {base}/videos`，body `{model, prompt, frame_images:[{type:"image_url", image_url:{url:<png data url>}, frame_type:"first_frame"}], aspect_ratio:"9:16", resolution:"720p", duration: max(2, min(10, duration_seconds))}`；取响应 `id`，`GET {base}/videos/{id}` 轮询（间隔/超时沿用 `_VIDEO_POLL_INTERVAL`/`_VIDEO_POLL_TIMEOUT`，从现有模块 import 或复制常量）；`status` 为 completed/succeeded → `GET {base}/videos/{id}/content?index=0` 下载 bytes；failed/error → 抛 `AV_UPSTREAM_FAILED`（带上游 error/reason 截断 200 字符）。
  - `generate_speech(text, model, voice) -> bytes`：`POST {base}/chat/completions` 流式，body `{model, modalities:["text","audio"], audio:{voice, format:"mp3"}, stream:true, messages:[{role:"system", content:<逐字朗读指令>},{role:"user", content:text}]}`；逐行解析 SSE `data:` 块，拼接 `choices[0].delta.audio.data`（base64）；一个音频块都没有 → 抛 `AV_UPSTREAM_FAILED`。
  - `generate_json(system, user, model) -> dict`：与 SiliconFlow 版同构（`response_format: {"type":"json_object"}`）。
  - 错误约定：复用 `_raise_upstream` 语义（401/402/429+balance → `AV_UPSTREAM_QUOTA`，文案改为"OpenRouter 余额不足或 Key 失效"），可从 av_client.py 抽成共享或本文件内实现。

- [ ] **Step 1: 写失败测试**（`httpx.MockTransport` 注入；覆盖：image 请求体含 aspect_ratio/input_references、b64_json 解码、b64 缺失回退 url 下载、url 也缺时报错；video 提交→poll pending→completed→content 下载全链、poll 到 failed 抛含 reason 的错、duration 夹取 [2,10]；speech SSE 多块拼接、零音频块报错；402 → `AV_UPSTREAM_QUOTA`）
- [ ] **Step 2: 跑测试确认失败**
- [ ] **Step 3: 实现 `OpenRouterAvClient` 与 config 新增项**
- [ ] **Step 4: 跑全量单测确认通过**
- [ ] **Step 5: Commit**（`feat(ai-videos): OpenRouter 生成客户端（images/videos/audio/llm）`）

### Task 3: 端口签名升级 + 路由客户端 + Mock/工厂

**Files:**
- Modify: `backend/app/application/ports.py:85-108`（AvGenClient）
- Modify: `backend/app/infrastructure/ai/av_client.py`（SiliconFlow 实现、Mock、工厂）
- Test: `backend/tests/unit/test_av_client_routing.py`（新建）

**Interfaces:**
- Produces: `AvGenClient` Protocol 新签名：
  - `generate_image(self, prompt: str, model: str, reference_images: list[bytes] | None = None) -> bytes`
  - `generate_video(self, image: bytes, prompt: str, model: str, duration_seconds: int) -> bytes`
  - `generate_speech` / `generate_json` 不变。
- `SiliconFlowAvClient`：`generate_image` 取 `reference_images[0]`（非空时）作原 `image` 参数；`generate_video` 接受并**忽略** `duration_seconds`。
- `MockAvClient`：签名对齐；`generate_json` 的 mock 剧本每句 line 增加 `"video_prompt": "the dog waves, camera static"` 与 `"characters": ["dog"]`。
- 新 `class RoutingAvClient`（放 `av_client.py`）：`__init__(self, clients: dict[str, AvGenClient], provider_of: Callable[[str], str])`；四个方法均按 `provider_of(model)` 分发；provider 无对应 client → 抛 `ServerException(codes.AV_UPSTREAM_FAILED, "未配置 <OPENROUTER_API_KEY|LLM_API_KEY>，无法调用 <model>")`。
- `get_av_client()` 工厂：两 Key 皆缺 → `MockAvClient()`；否则 `RoutingAvClient(clients={有 Key 的 provider: 对应实现}, provider_of=model_provider)`。

- [ ] **Step 1: 写失败测试**（RoutingAvClient 按 provider 分发到正确 fake client、缺 provider 的可读报错文案含环境变量名；工厂三种 Key 组合的返回类型）
- [ ] **Step 2: 跑测试确认失败**
- [ ] **Step 3: 实现**（ports、SiliconFlow/Mock 签名、RoutingAvClient、工厂；同步修正现用 `reference_image=` 的调用点：`av_service.py:154` 角色图生成改传 `reference_images=None` 省略即可）
- [ ] **Step 4: 跑全量单测确认通过**（既有 test_av_queue/test_av_service 的 fake client 签名同步更新）
- [ ] **Step 5: Commit**（`feat(ai-videos): AvGenClient 多参考图+时长签名 + 按 provider 路由`）

### Task 4: Domain——ref_character_ids / video_prompt + 迁移

**Files:**
- Create: `backend/app/alembic/versions/0008_av_multiref_video_prompt.py`
- Modify: `backend/app/domain/models/ai_video.py`
- Test: `backend/tests/unit/test_domain_ai_video.py`（扩展）

**Interfaces:**
- Produces: `AvShot.ref_character_ids: Mapped[list]`（JSONB, server_default `'[]'`）、`AvShot.video_prompt: Mapped[str]`（Text, server_default `''`）；`ref_character_id` 列与属性删除。
- `AvShot.create(..., ref_character_ids: list[int], video_prompt: str = "", ...)`（替换原 `ref_character_id` 参数）。
- `_PATCHABLE_FIELDS`：`ref_character_id` → `ref_character_ids`，新增 `video_prompt`。
- `_STALE_TRIGGERS`：`"ref_character_ids": (IMAGE, VIDEO)`、`"video_prompt": (VIDEO,)`（`image_prompt` 保持 `(IMAGE, VIDEO)`）。
- `validate_script`：line 可选字段 `video_prompt`（str，strip 保留）与 `characters`（list[str]，逐项 strip、去空），缺省分别为 `""` / `[]`，输出结构中始终携带。
- `shots_from_script(project_id, script, appearance_of, models, tts_voice, resolve_character)`：新参数 `resolve_character: Callable[[str], int | None]`（名字→项目角色 id，大小写不敏感匹配由调用方实现）；每镜 `ref_character_ids` = line.characters 逐名解析去 None 去重保序，为空则回退 `[speaker_id]`（speaker 为 None 则 `[]`）；`video_prompt` 直落。
- 迁移 0008：`add_column(video_prompt)`、`add_column(ref_character_ids)` → `UPDATE av_shots SET ref_character_ids = jsonb_build_array(ref_character_id) WHERE ref_character_id IS NOT NULL` → `drop_column(ref_character_id)`；downgrade 反向（回填取数组首元素）。

- [ ] **Step 1: 写失败测试**：

```python
def test_validate_script_passes_optional_fields():
    s = validate_script({"scenes": [{"setting": "park", "lines": [
        {"character_id": 1, "en": "Hi!", "zh": "嗨", "video_prompt": "waves, push-in", "characters": ["Max", " Dog "]}]}]})
    line = s["scenes"][0]["lines"][0]
    assert line["video_prompt"] == "waves, push-in" and line["characters"] == ["Max", "Dog"]

def test_shots_from_script_resolves_characters_and_falls_back():
    # characters=["Max","Ghost"]，resolve 只认 Max→7 → ref_character_ids==[7]
    # characters 缺省 → ref_character_ids==[speaker_id]
    ...

def test_patch_video_prompt_stales_video_only(): ...
def test_patch_ref_character_ids_stales_image_and_video(): ...
```

- [ ] **Step 2: 跑测试确认失败**
- [ ] **Step 3: 实现 domain 变更 + 迁移文件**（迁移风格参照 `0007_ai_videos.py`）
- [ ] **Step 4: 对联调库执行迁移并验证**：`uv run alembic upgrade head`；`docker exec robertgate-db-1 psql -U postgres -d robertgate -c "\d av_shots"` 确认新列存在、`ref_character_id` 已删
- [ ] **Step 5: 跑全量单测确认通过**
- [ ] **Step 6: Commit**（`feat(ai-videos): 分镜多角色引用 + video_prompt（迁移 0008）`）

### Task 5: Service/Schema/DTO——剧本 prompt、拆分镜、分镜编辑

**Files:**
- Modify: `backend/app/application/services/av_service.py`（`_SCRIPT_SYSTEM:63`、`_FALLBACK_MODELS:50`、`split_shots:374`、`create_shot:415`、`update_shot:443`）
- Modify: `backend/app/interfaces/api/schemas/ai_videos.py:57-64`（UpdateShotRequest）
- Modify: `backend/app/application/dto/ai_video.py:102-126`（ShotOut）
- Modify: `backend/tests/smoke/openapi_baseline.json`、`docs/api/ai-videos.md`
- Test: `backend/tests/unit/test_av_service.py`（扩展）

**Interfaces:**
- Consumes: Task 4 的 `shots_from_script(..., resolve_character)`、`AvShot.create(..., ref_character_ids, video_prompt)`；Task 1 的 `default_model`。
- Produces: `UpdateShotRequest`：删 `ref_character_id`，增 `ref_character_ids: list[int] | None = None`、`video_prompt: str | None = Field(default=None, max_length=1000)`。`ShotOut`：同名字段替换/新增。`_FALLBACK_MODELS` 更新为新 OpenRouter 默认四元组、`_FALLBACK_VOICE = "alloy"`。

- [ ] **Step 1: 写失败测试**（`update_shot` 传 `ref_character_ids=[非项目角色id]` → `AV_PARAM_INVALID`；传合法列表 → 落库且 image/video 标 stale；`split_shots` 后镜带 `video_prompt` 与解析后的 `ref_character_ids`；`_SCRIPT_SYSTEM` 文案断言含 `"video_prompt"` 与 `"characters"` 两个键名）
- [ ] **Step 2: 跑测试确认失败**
- [ ] **Step 3: 实现**：
  - `_SCRIPT_SYSTEM` line 结构追加 `"video_prompt": "<英文：角色动作 + 运镜(static/push-in/pull-back/pan…) + 氛围>"` 与 `"characters": ["<出场角色名，取自角色列表>"]`，并明确"video_prompt 不写台词内容"。
  - `split_shots`：从项目角色构建 `name → id`（`name.strip().lower()` 键），传 `resolve_character`。
  - `update_shot`：patch 含 `ref_character_ids` 时校验 ⊆ 项目角色 id 集（违例抛 `AV_PARAM_INVALID`），空列表合法。
  - `create_shot`：`ref_character_ids=[]`、`video_prompt=""`。
- [ ] **Step 4: 更新 OpenAPI 快照**（smoke 测试的既有再生成方式）与 `docs/api/ai-videos.md`（Shot 字段、models 响应 `provider`/`reference`、默认模型表）
- [ ] **Step 5: 跑全量单测+冒烟确认通过**（`uv run pytest tests/unit tests/smoke -q`）
- [ ] **Step 6: Commit**（`feat(ai-videos): 剧本按句产出 video_prompt/出场角色，分镜编辑多角色引用`）

### Task 6: 队列——三档参考降级 + video_prompt/duration

**Files:**
- Modify: `backend/app/application/services/av_queue.py`（`__init__:62-76`、`_generate:198-224`）
- Modify: `backend/app/interfaces/api/deps.py:82-91`（注入 `reference_mode`，删除 Task 1 的过渡 shim）
- Test: `backend/tests/unit/test_av_queue.py`（扩展，沿用既有 fake uow/client 风格）

**Interfaces:**
- Consumes: Task 1 `reference_mode`；Task 3 客户端新签名；Task 4 `shot.ref_character_ids` / `shot.video_prompt`。
- Produces: `AvGenerationQueue.__init__(..., reference_mode: Callable[[str], str], ...)`（替换 `supports_reference` 参数名与类型）。`_generate` 的 IMAGE 分支语义：
  - 按 `shot.ref_character_ids` 顺序加载角色；有封面图的收集 `(name, cover_bytes)`，无封面的收集 `(name, appearance_prompt)`。
  - `multi`：全部有图角色进 `reference_images`，prompt 前缀逐一点名 `"{name} is the character in reference image {n}. "`；无图角色外形描述拼接 `"{name}: {appearance}. "`。
  - `single`：首个有图角色进 `reference_images`（同款点名，编号 1）；其余全部按外形描述拼接。
  - `none`：全部按外形描述拼接。
  - 动态文本一律加在 `shot.image_prompt` 之前，不回写存储。
  - VIDEO 分支：`prompt = shot.video_prompt or shot.image_prompt`；`duration_seconds=round(shot.duration_estimate)`。

- [ ] **Step 1: 写失败测试**（fake client 记录调用参数：multi 两角色两图 → `reference_images` 长度 2 且 prompt 含两处点名；multi 下一个角色无封面 → 1 图 + 1 外形描述；single 两角色 → 1 图 + 第二角色外形描述；none → 0 图全描述；video 用 `video_prompt`、空时回退 `image_prompt`、duration 传 round 值）
- [ ] **Step 2: 跑测试确认失败**
- [ ] **Step 3: 实现**（既有 `ref_character_id` 相关旧测试同步改写）
- [ ] **Step 4: 跑全量单测确认通过**
- [ ] **Step 5: Commit**（`feat(ai-videos): 队列多参考图三档降级 + 图生视频走 video_prompt/时长`）

### Task 7: 合成分段归一化

**Files:**
- Modify: `backend/app/infrastructure/av_compose.py:60-77`（`build_segment_cmd`）
- Test: `backend/tests/unit/test_av_compose.py`（扩展）

**Interfaces:**
- Produces: `build_segment_cmd` 的 `-filter_complex` 变为 `[0:v]scale=720:1280:force_original_aspect_ratio=decrease,pad=720:1280:(ow-iw)/2:(oh-ih)/2:black,setsar=1,tpad=stop_mode=clone:stop_duration={duration}[v]`；其余参数与 concat 流程不变（分段统一后 `-c copy` 拼接安全）。

- [ ] **Step 1: 写失败测试**（断言命令串含 `scale=720:1280`、`pad=720:1280`、`setsar=1` 且 `tpad` 仍在其后）
- [ ] **Step 2: 跑测试确认失败** → **Step 3: 实现** → **Step 4: 全量单测通过**
- [ ] **Step 5: Commit**（`feat(ai-videos): 合成分段归一化 720x1280，兼容混合分辨率模型`）

### Task 8: 前端——类型/服务/Mock

**Files:**
- Modify: `frontend/src/types/aiVideos.ts`（`ModelInfo`、`Shot`、`ShotPatch`）
- Modify: `frontend/src/services/aiVideos.mock.ts`
- Modify: `frontend/src/services/aiVideos.ts`（如有字段名引用）

**Interfaces:**
- Produces: `ModelInfo` 增 `provider: 'openrouter' | 'siliconflow'`，`supports_reference?: boolean` 改为 `reference?: 'multi' | 'single' | 'none'`；`Shot`：`ref_character_id: number | null` → `ref_character_ids: number[]`，新增 `video_prompt: string`；`ShotPatch` 同步。Mock 的模型清单镜像 Task 1 注册表（含 provider/reference/voices），mock 分镜数据与 patch 逻辑用新字段。

- [ ] **Step 1: 更新类型与 mock**（mock 行为与后端语义一致：patch `ref_character_ids`/`video_prompt` 生效并触发相应 stale 展示字段，如 mock 已模拟 stale）
- [ ] **Step 2: 验证**：`npx tsc -b --noEmit` 通过（此时引用旧字段的组件会报错——顺延到 Task 9 一起改完才绿，故本任务与 Task 9 同一条 commit 边界；若希望独立绿灯，可先改组件引用处字段名的最小替换）
- [ ] **Step 3: 不单独 commit，进入 Task 9**

### Task 9: 前端——ShotEditor 多选出场角色 + video_prompt + 分组下拉

**Files:**
- Modify: `frontend/src/components/ai-videos/ShotEditor.tsx`（`:48`、`:172-215` 画面区、`:241-250` 音色）
- Modify: `frontend/src/components/ai-videos/ModelSelect.tsx`
- Modify: `frontend/src/components/ai-videos/CreateWizard.tsx:50,58,373`（voices 跟随所选 tts 模型，默认音色随模型条目）
- Modify: `frontend/src/pages/ai-videos/WorkbenchPage.tsx:126-128`（voices 改按分镜当前 audio 模型条目取，而非项目默认模型）

**Interfaces:**
- Consumes: Task 8 类型。
- Produces: ShotEditor「参考角色」单选 select 改为**出场角色多选 chip 组**（候选=项目角色，点击切换选中，选中态用 primary token；顺序按点击先后追加），blur/变更即 `onPatch({ ref_character_ids })`；画面 Prompt textarea 下方新增同款「视频动作/运镜」textarea（label `视频动作 / 运镜`，blur 时 `onPatch({ video_prompt })`）。`ModelSelect` 按 `provider` 分 `<optgroup label="OpenRouter|SiliconFlow">`。

- [ ] **Step 1: 实现上述 UI 变更**（样式 token 遵循 ui-style.md，复用现有 chip/选中视觉；不新增颜色）
- [ ] **Step 1.5: 剧本编辑透传检查**：`ScriptDrawer.tsx` 编辑剧本回传时必须保留 line 上的 `video_prompt`/`characters` 字段（若其实现按字段重组 line 对象则补透传；UI 不必暴露编辑入口）
- [ ] **Step 2: 验证**：`npx tsc -b --noEmit` 与 `npm run lint` 通过；`npm run dev` + mock 模式人工点一遍：多选出场角色、编辑 video_prompt、模型下拉分组、音色随 TTS 模型切换
- [ ] **Step 3: Commit**（Task 8+9 一并，`feat(ai-videos): 工作台出场角色多选 + 视频运镜提示 + provider 分组下拉`）

### Task 10: 真机验证与模型清单修正（需 OPENROUTER_API_KEY）

**Files:**
- Modify: `backend/app/infrastructure/data/av_models.py`（按验证结果修 slug/注释）
- Create（临时，不提交）: 探针脚本放 scratchpad

**Interfaces:**
- Consumes: Robert 在 `backend/.env.local` 配好 `OPENROUTER_API_KEY`。

- [ ] **Step 1: 核对 slug**：`GET /api/v1/models`（text+image）与 `GET /api/v1/models?output_modalities=video` 对照注册表逐条确认存在；不存在的替换为同系最接近可用款并记录
- [ ] **Step 2: 逐模型最小真机调用**（每个 t2i 一张 9:16 图、每个 i2v 一段最短时长视频、gpt-audio 一句话音频、llm 默认模型一次 json 调用；t2i 的 multi 档带 2 张参考图验证 `input_references`）；验证结论写进注册表注释
- [ ] **Step 3: 全链路冒烟**：起后端（`VITE_AI_VIDEOS_MOCK=false` 前端或直接 curl）：建项目 → 生成剧本（断言 line 含 video_prompt/characters）→ 拆分镜 → 单镜生成图/视频/音频 → 合成 → 下载 mp4 可播放
- [ ] **Step 4: 跑全量测试**（`uv run pytest -q` 后端全绿；前端 tsc/lint 绿）
- [ ] **Step 5: Commit**（`fix(ai-videos): 模型清单按真机验证修正`，如无修正则并入文档性 commit）
