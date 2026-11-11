# ai-videos 对白镜（音视同出）Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 分镜支持多角色台词列表，说话镜改走音视同出生成（kie.ai Omni 主、OpenRouter Seedance 兜底），whisper 本地对齐字幕，旧项目零操作兼容。

**Architecture:** 领域层把单台词三字段演进为 `dialogue` JSON 列表并以"列表非空"判定说话镜；基础设施新增 KieClient 与 DialogueVideoRouter（主备路由）；合成按"音频产物文件是否存在"分路（旧 mux / 视频自带音轨），字幕由 faster-whisper 词级时间戳与已知台词模糊对齐。

**Tech Stack:** Python 3.11 + FastAPI + SQLAlchemy 2.0 + alembic；httpx（kie API）；faster-whisper；React 18 + TS。

**Spec:** `docs/superpowers/specs/2026-11-09-av-dialogue-shots-design.md`

## Global Constraints

- 模型渠道仅 OpenRouter + kie.ai；主模型 `gemini-omni-video`（kie），兜底 `bytedance/seedance-2.0-fast`（OpenRouter，`generate_audio: true`）。
- kie omni 时长档位 `4/6/8/10` 秒；每镜台词 ≤4 句、预估 ≤10s。
- `video_model` 记实际渠道+模型：`kie:gemini-omni-video` / `openrouter:bytedance/seedance-2.0-fast`。
- dialogue 非空的镜：`ShotOut.audio = null`，聚合/合成预检不看 audio；合成时磁盘有 audio 文件则仍走旧 mux。
- 错误码沿用 `codes.AV_UPSTREAM_QUOTA / AV_UPSTREAM_FAILED / AV_PARAM_INVALID`，不新增数字。
- 旧三字段 `speaker_character_id/line_en/line_zh` 保留列但新代码不再读写（迁移回填后冻结）。
- 遵循 `.claude/rules/backend.md`（DDD 分层、错误码集中、测试覆盖）与 `.claude/rules/frontend.md`（无 any、API 走 services）。
- 剧本存储结构 `scenes[].lines[]` 不变（ScriptDrawer 不动）；对白镜合并由**确定性纯函数**完成（设计文档"LLM 输出 shots"按此修正，已在 Task 1 注明同步文档）。

## Review Focus

1. kie 任务 success 但 `resultUrls` 为空/下载 404 → 该镜 mark_failed 带错误信息而非未捕获异常（测试在 Task 3）。
2. 10s 请求落到兜底 seedance 时的时长二次 snap（seedance 档位与 omni 不同）→ 不得 400（测试在 Task 5）。
3. whisper 转写为空/对齐不上 → 回退按台词长度均分镜时长，SRT 永不缺条目（测试在 Task 7）。
4. dialogue 行 `character_id` 为 null 或查无此角色 → prompt 构建跳过角色名仍可生成，不崩（测试在 Task 4）。
5. 旧迁移镜（磁盘有 audio.mp3）重新合成 → 走 mux 路径不哑声（测试在 Task 8）。

---

### Task 1: 领域模型——dialogue 字段、校验、聚合与分组

**Files:**
- Modify: `backend/app/domain/models/ai_video.py`
- Modify: `docs/superpowers/specs/2026-11-09-av-dialogue-shots-design.md`（"拆分镜"节一行修正：LLM 输出结构不变，合并为确定性纯函数）
- Test: `backend/tests/unit/test_domain_ai_video.py`

**Interfaces:**
- Produces: `AvShot.dialogue: Mapped[list]`（JSONB，default list，元素 `{"character_id": int|None, "en": str, "zh": str}`）；`AvShot.has_dialogue -> bool`（property，`bool(self.dialogue)`）；`AvCharacter.voice_desc: Mapped[str]`（String(200) default ""，`apply_update` 增同名可选参）；`validate_dialogue(value: Any) -> list[dict]`（校验 ≤4 条、en 非空、character_id int|None，抛 `ParamException(codes.AV_PARAM_INVALID)`）；`estimate_dialogue_duration(dialogue: list[dict]) -> float`（全部 en 词数合计 `*0.45+1.5`，clamp 3–10）；`group_script_into_shots(script: dict) -> list[dict]`（替代 shots_from_script 的分组前半：同 scene 连续 lines 贪心合并，约束"每组 ≤4 句且 estimate ≤10s"，每组产出 `{dialogue, image_prompt(取组内第一条非空，否则 setting 回退拼接), video_prompt(同前), character_names(组内 characters∪speakers 名单序)}`）
- `shots_from_script` 改为消费分组结果：`AvShot.create` 增 `dialogue: list[dict]` 参数，`duration_estimate=estimate_dialogue_duration(dialogue)`；旧 `speaker_character_id/line_en/line_zh` 参数移除，创建时三字段留默认。
- `_STALE_TRIGGERS`：删 `line_en/speaker_character_id` 两键，增 `"dialogue": (AssetKind.VIDEO,)`；`_PATCHABLE_FIELDS`：去掉 `line_en/line_zh/speaker_character_id`，加入 `dialogue`（`apply_patch` 对 dialogue 先过 `validate_dialogue`，并同步重算 `duration_estimate`）。
- 聚合改造：`derive_project_status` 与 `missing_compose_items` 的 kind 集合改为 `(AssetKind.IMAGE, AssetKind.VIDEO)` / `(AssetKind.VIDEO,)`——audio 一律不参与（新世界说话镜无独立音频、纯画面镜无音）；`stale_items` 不变。

- [ ] **Step 1: 写失败测试**（节选断言；文件内新增 `TestDialogue` 区）

```python
def test_validate_dialogue_rejects_five_lines():
    with pytest.raises(ParamException):
        validate_dialogue([{"character_id": 1, "en": f"l{i}", "zh": ""} for i in range(5)])

def test_group_script_merges_consecutive_lines_within_scene():
    script = {"scenes": [{"setting": "park", "lines": [_line(1, "Hello Lily"), _line(2, "Hi Max"),
        _line(1, "Repeat after me: apple"), _line(2, "Apple! 苹果"), _line(1, "Great job")]}]}
    groups = group_script_into_shots(validate_script(script))
    assert [len(g["dialogue"]) for g in groups] == [4, 1]

def test_apply_patch_dialogue_stales_video_only():
    shot = _shot(dialogue=[{"character_id": 1, "en": "a", "zh": ""}])
    shot.mark_succeeded(AssetKind.VIDEO, "v.mp4"); shot.mark_succeeded(AssetKind.IMAGE, "i.png")
    staled = shot.apply_patch(dialogue=[{"character_id": 1, "en": "b", "zh": ""}])
    assert staled == [AssetKind.VIDEO] and shot.duration_estimate == estimate_dialogue_duration(shot.dialogue)

def test_project_status_ignores_audio():
    # image+video success、audio pending → completed
```

- [ ] **Step 2: 跑测试确认失败**：`uv run pytest tests/unit/test_domain_ai_video.py -q`，FAIL（名称未定义）
- [ ] **Step 3: 实现上述 Interfaces 全部条目**；同步修正设计文档"拆分镜"节一行
- [ ] **Step 4: 全量 `uv run pytest -q` 绿**（旧用例中依赖 line_en/speaker 的按新形态改写，属本任务工作量）
- [ ] **Step 5: Commit** `feat(av-dialogue): 领域层 dialogue 列表+分组纯函数+聚合去 audio`

### Task 2: 迁移 0010——dialogue/voice_desc 列与旧数据回填

**Files:**
- Create: `backend/app/alembic/versions/0010_av_dialogue.py`
- Test: `backend/tests/unit/test_domain_ai_video.py`（回填纯函数）

**Interfaces:**
- Produces: `av_shots.dialogue`（JSONB NOT NULL server_default `'[]'`）、`av_characters.voice_desc`（VARCHAR(200) NOT NULL server_default `''`）；回填 SQL：`line_en != ''` 的行 `dialogue = [{"character_id": speaker_character_id, "en": line_en, "zh": line_zh}]`。
- 回填逻辑抽纯函数 `legacy_shot_to_dialogue(speaker_character_id, line_en, line_zh) -> list[dict]`（放 ai_video.py，迁移内联等价 SQL；空 line_en → `[]`）。

- [ ] **Step 1: 写失败测试**：`legacy_shot_to_dialogue(3, "Hello", "你好") == [{"character_id": 3, "en": "Hello", "zh": "你好"}]`；`legacy_shot_to_dialogue(None, "", "") == []`
- [ ] **Step 2: 确认失败** → **Step 3: 实现函数 + 迁移脚本**（upgrade 用 `op.add_column` + `op.execute` 批量 UPDATE；downgrade 删列）
- [ ] **Step 4: 真库验证**：`uv run alembic upgrade head`，对联调库抽查 `SELECT dialogue FROM av_shots WHERE line_en != '' LIMIT 3`
- [ ] **Step 5: Commit** `feat(av-dialogue): 0010 迁移——dialogue/voice_desc 列+旧台词回填`

### Task 3: KieClient（kie.ai 上传/创建/轮询/下载）

**Files:**
- Create: `backend/app/infrastructure/ai/av_client_kie.py`
- Test: `backend/tests/unit/test_av_client_kie.py`

**Interfaces:**
- Produces: `class KieVideoClient:`，构造 `(api_key: str, model: str = "gemini-omni-video", base: str = "https://api.kie.ai/api/v1", upload_base: str = "https://kieai.redpandaai.co/api", poll_interval: float = 10.0, poll_timeout: float = 900.0)`；方法 `async generate_dialogue_video(self, image: bytes, prompt: str, duration_seconds: int) -> bytes`。
- 行为：① `POST {upload_base}/file-stream-upload`（multipart `file/uploadPath="av-dialogue"/fileName`）取 `data.downloadUrl`；② `POST {base}/jobs/createTask`，payload `{"model": model, "input": {"prompt", "image_urls": [url], "duration": str(snap)(档位 4/6/8/10 就近向上), "aspect_ratio": "9:16", "resolution": "720p"}}`；③ 轮询 `GET {base}/jobs/recordInfo?taskId=`，state `success` → 解析 `resultJson`（字符串则 json.loads）取 `resultUrls[0]` 下载返回 bytes；`fail` / 超时 / resultUrls 空 / 下载 ≥400 → `ServerException(codes.AV_UPSTREAM_FAILED, ...)`；HTTP 401/402/429 → `codes.AV_UPSTREAM_QUOTA`。
- 测试手法沿用 `test_av_client_openrouter.py` 的 httpx MockTransport 模式。

- [ ] **Step 1: 写失败测试**（成功链路、success-但-resultUrls-空 → AV_UPSTREAM_FAILED、402 → AV_UPSTREAM_QUOTA、duration snap：`7 → "8"`，`11 → "10"`）
- [ ] **Step 2: 确认失败** → **Step 3: 实现** → **Step 4: 测试过 + 全量绿**
- [ ] **Step 5: Commit** `feat(av-dialogue): KieVideoClient——上传/createTask/轮询/下载`

### Task 4: dialogue prompt 构建纯函数

**Files:**
- Create: `backend/app/application/services/av_dialogue.py`
- Test: `backend/tests/unit/test_av_dialogue.py`

**Interfaces:**
- Consumes: `AvCharacter.voice_desc`（Task 1）
- Produces: `build_dialogue_prompt(scene_hint: str, speakers: list[dict], dialogue: list[dict]) -> str`，`speakers` 元素 `{"id": int, "name": str, "voice_desc": str}`。模板以 PoC 已验证版本参数化：风格句（children's storybook cartoon + scene_hint）→ 逐角色一句 "`{name}` has a {voice_desc or 'clear friendly'} voice" → 按序台词 `Then {name} says: "{en}"`（首句无 Then；character_id 为 None 或查无 speaker → 该句写 `The narrator says` 且不标名）→ 固定尾缀（mouths in sync / no background music / clear speech / gentle camera）。
- `snap_dialogue_duration(estimate: float, ladder: tuple[int, ...]) -> int`（就近向上取档，超最大取最大）。

- [ ] **Step 1: 失败测试**（双角色模板含两句 voice 描述与引号台词；character_id=None → "The narrator says"；`snap_dialogue_duration(7.2, (4,6,8,10)) == 8`）
- [ ] **Step 2: 确认失败** → **Step 3: 实现** → **Step 4: 过**
- [ ] **Step 5: Commit** `feat(av-dialogue): 对白 prompt 构建与时长取档纯函数`

### Task 5: 路由兜底、配置与装配

**Files:**
- Modify: `backend/app/config.py`（增 `KIE_BASE_URL/KIE_UPLOAD_BASE_URL/AV_DIALOGUE_MODEL="gemini-omni-video"/AV_DIALOGUE_FALLBACK_MODEL="bytedance/seedance-2.0-fast"/AV_WHISPER_MODEL="small"`；`KIE_API_KEY` 已存在）
- Modify: `backend/app/application/ports.py`（`AvGenClient` 增 `async generate_dialogue_video(image: bytes, prompt: str, duration_seconds: int) -> tuple[bytes, str]`——返回 `(mp4, used_model_tag)`）
- Modify: `backend/app/infrastructure/ai/av_client_openrouter.py`（`generate_video` 增可选 `generate_audio: bool = False` 透传 payload）
- Create: `backend/app/infrastructure/ai/av_dialogue_router.py`
- Modify: `backend/app/infrastructure/ai/av_client.py` + `backend/app/interfaces/api/deps.py`（装配）、`backend/app/infrastructure/ai/mock_client.py`（mock 实现新方法）
- Test: `backend/tests/unit/test_av_dialogue_router.py`

**Interfaces:**
- Produces: `class DialogueVideoRouter:` 构造 `(primary: KieVideoClient, fallback_video: Callable, primary_tag: str, fallback_tag: str, fallback_ladder: tuple[int, ...])`；`async generate_dialogue_video(image, prompt, duration_seconds) -> tuple[bytes, str]`：primary 抛任意 ServerException → log warning + 调 fallback（OpenRouter `generate_video(..., generate_audio=True)`，时长按 fallback_ladder 二次 snap）→ 返回 `(bytes, "openrouter:bytedance/seedance-2.0-fast")`；两级都挂 → 抛 fallback 的异常。
- tag 值即 Global Constraints 规定的 `kie:...`/`openrouter:...`。

- [ ] **Step 1: 失败测试**（primary 成功 → tag 为 kie:*；primary 抛 AV_UPSTREAM_FAILED → fallback 被调且 duration 二次 snap、tag 为 openrouter:*；双挂 → 异常冒泡）
- [ ] **Step 2: 确认失败** → **Step 3: 实现 + 装配**（deps 在 `KIE_API_KEY` 为空时 primary 直接缺席、router 退化为 fallback-only）
- [ ] **Step 4: 全量绿** → **Step 5: Commit** `feat(av-dialogue): kie 主 + seedance 兜底路由与装配`

### Task 6: 生成链路接入（av_service / av_queue）

**Files:**
- Modify: `backend/app/application/services/av_service.py`（`split_shots` 用 `group_script_into_shots`；`generate_asset`/`generate_all`）
- Modify: `backend/app/application/services/av_queue.py`（video 任务对 has_dialogue 镜走 dialogue 路径）
- Test: `backend/tests/unit/test_av_service.py`、`backend/tests/unit/test_av_queue.py`

**Interfaces:**
- Consumes: Task 1 分组函数、Task 4 prompt 构建、Task 5 router（经 AvGenClient 端口）。
- 行为规约：`generate_asset(kind="audio")` 对 `has_dialogue` 镜抛 `ParamException(codes.AV_PARAM_INVALID, "对白镜无独立配音")`；`generate_all` 的任务展开对 has_dialogue 镜只排 image+video；video 生成时 has_dialogue → 读分镜图 bytes + 项目角色表组 speakers（含 voice_desc）→ `build_dialogue_prompt` → `generate_dialogue_video` → `mark_succeeded(VIDEO, path)` 且 `video_model = used_tag`；无台词镜走原 i2v 不变。
- `split_shots` 创建分镜：`character_names` 经现有 `resolve_character` 逻辑转 `ref_character_ids`。

- [ ] **Step 1: 失败测试**（对白镜 audio 生成 400；generate_all 不给对白镜排 audio；对白镜 video 成功后 video_model == "kie:gemini-omni-video"（FakeClient 返回该 tag）；split 后 dialogue 分组落库）
- [ ] **Step 2: 确认失败** → **Step 3: 实现** → **Step 4: 全量绿**
- [ ] **Step 5: Commit** `feat(av-dialogue): 生成链路——对白镜走音视同出、audio 退役`

### Task 7: whisper 词级对齐

**Files:**
- Create: `backend/app/infrastructure/av_whisper.py`（薄执行层：faster-whisper 调用，`WhisperAligner.transcribe_words(media: Path) -> list[tuple[str, float, float]]`，懒加载模型 `AV_WHISPER_MODEL`，`word_timestamps=True`）
- Create: `backend/app/application/services/av_subtitle.py`（纯函数）
- Modify: `backend/requirements.txt`（`faster-whisper==1.2.1`，以 `uv pip install` 实际可装版本为准钉死）
- Test: `backend/tests/unit/test_av_subtitle.py`（纯函数；whisper 执行层不进单测）

**Interfaces:**
- Produces: `align_dialogue(lines: list[str], words: list[tuple[str, float, float]], total: float) -> list[tuple[str, float, float]]`——把每句台词对齐到词序列（大小写/标点归一后贪心匹配句尾词边界），返回每句 `(text, start, end)`；`words` 为空或匹配率 <50% → 回退均分：第 i 句 `(i*total/n, (i+1)*total/n)`。
- Consumes（Task 8 用）：对齐结果直接作为该镜字幕条目。

- [ ] **Step 1: 失败测试**（两句台词+完整词序列 → 按词边界切分；空 words → 均分且条目数 == 台词数；whisper 多识别少识别样例 → 不抛异常）
- [ ] **Step 2: 确认失败** → **Step 3: 实现**（匹配算法留实现者，约束如上）→ **Step 4: 过**
- [ ] **Step 5: Commit** `feat(av-dialogue): whisper 词级对齐纯函数与执行层`

### Task 8: 合成分路与镜内多条字幕

**Files:**
- Modify: `backend/app/infrastructure/av_compose.py`
- Modify: `backend/app/application/services/av_service.py`（compose 组装 items）
- Test: `backend/tests/unit/test_av_compose.py`

**Interfaces:**
- `ComposeItem` 改为 `(video: Path, audio: Path | None, subtitles: list[tuple[str, float, float]])`——`line_en` 字段删除，字幕一律显式条目（单人旧镜 = 单条目全时长）。
- `build_segment_cmd(video, audio: Path | None, duration, out, ffmpeg_bin)`：audio None → 不加 `-i audio`、映射视频自带音轨（`-map 0:v -map 0:a? -c:a aac`）。
- `build_srt(entries: list[tuple[str, float, float]]) -> str`（签名从 `(text, duration)` 改为显式起止；全局偏移由 compose 按各镜起点累加）。
- `av_service.compose`：item 组装处——`audio = storage.absolute(s.audio_path) if s.audio_path else None`；subtitles：has_dialogue 且 audio 为 None → `WhisperAligner.transcribe_words(video)` + `align_dialogue`（行文本 `f"{en}"`，中文 zh 非空则 `en\nzh` 双行）；否则单条目 `(line_en 或 dialogue[0].en, 0, duration)`。whisper 在 `_run_compose` 后台段执行（不阻塞请求事务）。

- [ ] **Step 1: 失败测试**（audio=None 的 segment cmd 不含第二个 `-i`；`build_srt` 显式时间；混排项目：镜 1 有 audio 文件走 mux、镜 2 无 audio 用自带音轨，最终 SRT 偏移正确）
- [ ] **Step 2: 确认失败** → **Step 3: 实现** → **Step 4: 全量绿**
- [ ] **Step 5: Commit** `feat(av-dialogue): 合成分路（mux/自带音轨）+ 镜内多条字幕`

### Task 9: API 契约（schemas/DTO/docs/baseline）

**Files:**
- Modify: `backend/app/application/dto/ai_video.py`（`ShotOut.dialogue: list[DialogueLineOut]`、`audio: AudioAssetOut | None`——`ShotOut.build` 在 `shot.has_dialogue` 时置 None；`CharacterOut.voice_desc`；status 的 `AssetStatusLiteOut.audio` 同步可选）
- Modify: `backend/app/interfaces/api/schemas/ai_videos.py`（ShotPatch 增 `dialogue`、Character create/update 增 `voice_desc`）、`backend/app/interfaces/api/routers/ai_videos.py`（`/models` 返回增 `dialogue_video` 段：两条目 kie/seedance 仅展示）
- Modify: `docs/api/ai-videos.md`、`backend/tests/smoke/openapi_baseline.json`（重新生成）
- Test: `backend/tests/unit/test_av_service.py` 增契约断言

**Interfaces:**
- Produces: `DialogueLineOut(character_id: int | None, en: str, zh: str)`；前端据此出 TS 类型（Task 10）。

- [ ] **Step 1: 失败测试**（对白镜 ShotOut.audio is None 且 dialogue 长度正确；voice_desc 出现在 CharacterOut）
- [ ] **Step 2: 确认失败** → **Step 3: 实现 + 重新生成 baseline + 更新 docs/api**
- [ ] **Step 4: 全量绿** → **Step 5: Commit** `feat(av-dialogue): API 契约——dialogue/voice_desc/audio 可空`

### Task 10: 前端（类型/编辑器/角色弹窗/轨道）

**Files:**
- Modify: `frontend/src/types/aiVideos.ts`（`DialogueLine`、`Shot.dialogue: DialogueLine[]`、`Shot.audio: ShotAudioAsset | null`、`Character.voice_desc`、`ShotPatch.dialogue?`）
- Modify: `frontend/src/components/ai-videos/ShotEditor.tsx`（台词区 → 台词行列表：每行角色下拉(出场角色+旁白)/en/zh/删除，底部"+ 添加台词"，上限 4 行；产物区 audio 为 null 时隐藏配音行；video 行模型改只读文本显示 `video_model`）
- Modify: `frontend/src/components/ai-videos/CharacterEditorModal.tsx`（voice_desc 文本输入，label "音色描述"）
- Modify: `frontend/src/components/ai-videos/ShotTrack.tsx`（dialogue.length ≥2 显示 `N人` 徽标，样式用现有 token）
- Modify: `frontend/src/services/aiVideos.ts` + mock（patch dialogue、voice_desc 透传；mock 数据含一个双人对白镜）
- Test: `npx tsc -b --noEmit` + `npm run lint`

- [ ] **Step 1: 类型与 service 先行**（tsc 立红）→ **Step 2: 组件实现到 tsc/lint 绿**
- [ ] **Step 3: mock 模式人工过一遍工作台**（增删台词行、保存、重生成按钮状态）
- [ ] **Step 4: Commit** `feat(av-dialogue): 前端——台词行编辑器/音色描述/配音行退役`

### Task 11: 真机冒烟（Robert 验收门）

**Files:** 无新增（冒烟脚本放 scratchpad）

- [ ] **Step 1**: `alembic upgrade head`；起后端+前端，新建小项目（2 角色、目标 30s）
- [ ] **Step 2**: 生成剧本 → 拆分镜（验证对白镜合并落库）→ 为 1 个对白镜真跑 kie 生成（~$0.2）→ 验证 video_model tag、预览有声
- [ ] **Step 3**: 人为给 kie 填错 key 重试一镜 → 验证自动兜底 seedance 且 tag 正确（~$0.9）
- [ ] **Step 4**: 合成 → ffprobe 验音轨、抽帧验字幕时间 → 交 Robert 试听验收
- [ ] **Step 5: Commit**（如有修补）+ 汇报

---

## Self-Review 记录

- 规格覆盖：设计各节 ↔ Task 1/2（数据模型+迁移）、3/4/5（链路三件套）、6（接入）、7/8（字幕+合成）、9（契约口径五条裁定）、10（前端）、11（冒烟）。预备工作已在计划外完成（分支已建）。
- 类型一致性：`generate_dialogue_video` 统一返回 `tuple[bytes, str]`（Task 3 的 KieVideoClient 返回 bytes，由 Task 5 router 包 tag——KieVideoClient 单独返回 bytes、router 返回 tuple，Task 6 只消费 router 经端口的 tuple）。
- 比例：计划 ≈ 设计的 2 倍行数，以签名/断言为主，无整函数转录。
