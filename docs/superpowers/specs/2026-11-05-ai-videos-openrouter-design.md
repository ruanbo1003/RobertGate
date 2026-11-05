# AI Videos：多 Provider（OpenRouter）+ 分镜 video_prompt 设计

日期：2026-11-05 ｜ 状态：待 Robert 批准 ｜ 关联：docs/prd/ai-videos.md、docs/api/ai-videos.md

## 意图与动机

ai-videos 工作台当前所有生成环节绑定 SiliconFlow 单 provider，带来三个实际痛点：

1. **角色一致性弱**：分镜图参考图只支持 Kolors 单图参考，多角色同框时只能保一个角色的长相，其余靠外形描述拼 prompt 兜底。Robert 明确要求：**同框的每个角色都要用设定图参考，两边都得长得对。**
2. **图生视频无动作/运镜控制**：i2v 直接复用静态画面的 `image_prompt`，没有角色动作、镜头运动、氛围提示，成片动态效果不可控。
3. **模型选择面窄**：SiliconFlow 无 Gemini 图像系、无 Seedance/Kling/Veo 视频系、TTS 只有 CosyVoice。

Robert 的决策：**默认模型全部切换到 OpenRouter**（LLM、文生图、图生视频、TTS 四类都有，已逐类核实），SiliconFlow 模型保留在清单里作备选。此外，OpenRouter 的 `wan-3.0`、`seedance-2.x` 等视频模型接受 audio 输入，为下一期「口型同步」铺平道路（本期不做）。

## 目标

1. 每镜新增 `video_prompt`（英文动作/运镜/氛围提示）：LLM 拆分镜时生成，工作台可编辑，图生视频时使用；为空时回退 `image_prompt`。
2. 每镜的角色引用从单个 `ref_character_id` 升级为**出场角色列表** `ref_character_ids`；分镜图生成时按模型参考能力传入**多张**角色设定图。
3. 模型清单与客户端支持多 provider（`openrouter` / `siliconflow`），按模型条目路由到对应 base_url、Key 与接口格式。
4. 四类默认模型全部切到 OpenRouter；每个进清单的模型先真机验证（一次最小调用）再上架。

## 非目标 / 反目标

- **非目标**：口型同步（下一期，复用本期 provider 架构）；BGM；成本统计；火山引擎/可灵直连；`Qwen-Image-Edit` 系（强制要求参考图，角色首图场景会 400）；`MOSS-Image`（不支持统一尺寸档）。
- **反目标**：破坏现有「单镜重做、失败不连坐」状态机语义；让前端感知 provider 差异（前端只看模型清单，provider 对前端透明）。

## 约束

- 遵循仓库 DDD 分层、`/api/v1` 统一返回格式、错误码常量（`domain/errors.py`）、单测规范（见 `.claude/rules/backend.md`）。
- OpenRouter Key 由 Robert 提供，配置名 `OPENROUTER_API_KEY`，放 `backend/.env.local`（不入库）。SiliconFlow 的 `LLM_API_KEY`/`LLM_BASE_URL` 保留。
- 既有项目/分镜数据需平滑迁移，不丢数据。

## 已定决策（按决策人标注）

### 1. 数据模型（Robert 定方向，细节为我的设计）

- `av_shots` 新增 `video_prompt TEXT NOT NULL DEFAULT ''`。
- `av_shots` 新增 `ref_character_ids JSONB NOT NULL DEFAULT '[]'`（角色 id 数组，有序，次序即 prompt 中点名次序）；迁移时从旧 `ref_character_id` 回填（非空则 `[ref_character_id]`），回填后**删除**旧列 `ref_character_id`。采用 JSONB 数组而非关联表是我的取舍：单用户规模、查询只在镜内展开，不值得一张表。角色删除保护维持现状（项目引用级别校验），`ref_character_ids` 必须是所属项目已选角色的子集（application 层校验，错误码沿用参数错误段）。
- `speaker_character_id` 保留不动（说话人用于 TTS/后续口型，与出场列表是两回事）。
- 迁移文件：`0008_av_multiref_video_prompt.py`。

### 2. 模型清单与能力标记（Robert 定方向，条目为我的筛选）

`AV_MODELS` 每条新增 `provider` 字段；`supports_reference` 布尔升级为 `reference: "multi" | "single" | "none"`。默认条目（**上架前逐一真机验证，验证不过的由实现者替换为同系可用款并在清单注释说明**）：

- **llm**：默认 `google/gemini-3-flash`（OpenRouter）；备选 `deepseek/deepseek-v3.2`（OpenRouter）；保留 SiliconFlow `deepseek-ai/DeepSeek-V3`、`Qwen/Qwen2.5-72B-Instruct`。
- **t2i**：默认 `google/gemini-3.1-flash-image`（multi）；备选 `google/gemini-3-pro-image`（multi）、`google/gemini-nano-banana-2.1`（multi）；保留 SiliconFlow `Kwai-Kolors/Kolors`（single）、`Qwen/Qwen-Image`、`Tongyi-MAI/Z-Image-Turbo`、`Tongyi-MAI/Z-Image`（均 none）。
- **i2v**：默认 `bytedance/seedance-2.0-fast`；备选 `alibaba/wan-3.0`、`kwaivgi/kling-v3.0-std`、`google/veo-3.1-fast`；保留 SiliconFlow `Wan-AI/Wan2.2-I2V-A14B`、`Wan2.1-720P`。
- **tts**：默认 `openai/gpt-audio`（Robert 拍板），音色以实测为准（文档示例：alloy/echo/fable/onyx/nova/shimmer）；备选 `openai/gpt-audio-mini`；保留 SiliconFlow `FunAudioLLM/CosyVoice2-0.5B`（voices 不变）。
- TTS 音色清单属于模型条目（`voices`），前端按所选模型渲染音色下拉；项目既有 `tts_voice` 若不在新模型音色表中，前端下拉回退默认音色，后端不迁移存量值。

### 3. 客户端架构（我的设计）

- `AVClient` 端口（`application/ports.py`）签名调整：`generate_image(prompt, model, reference_images: list[bytes])`（原单张参数变列表）；`generate_video(image, prompt, model, duration_seconds: int)`（新增时长参数，队列从 `round(shot.duration_estimate)` 传入；OpenRouter 实现夹到模型支持区间，SiliconFlow 实现可忽略）；`generate_speech(text, model, voice)` 不变。`generate_video` 的 `prompt` 语义改为 video_prompt（见 §4）。相关 Protocol、Mock、单测随签名同步。（审查后裁定）
- 基础设施层：新增 `OpenRouterAVClient`，与现有 SiliconFlow 客户端并列；新增一个按模型路由的组合客户端（查模型注册表得 provider，分发到对应实现）。组合根（`main.py`/`deps.py`）装配。**Mock 语义（审查后裁定）**：两把 Key 都未配 → 整体落到 `MockAvClient`，保持现有"无 Key 全链路可跑"的开发/测试体验；只缺其中一把 → 仅该 provider 的模型调用报 `AV_UPSTREAM_FAILED` 段错误并给出可读提示（提示写明缺哪个环境变量），另一 provider 正常；启动永不报错。
- OpenRouter 接口形态（已查官方文档）：
  - 图像：`POST /api/v1/images`，body `{model, prompt, aspect_ratio: "9:16", input_references: [{type:"image_url", image_url:{url:"data:image/png;base64,..."}}], n:1}`，响应 `data[0].b64_json`。
  - 视频：`POST /api/v1/videos`，body `{model, prompt, frame_images:[{type:"image_url", image_url:{url:<data url>}, frame_type:"first_frame"}], aspect_ratio:"9:16", resolution:"720p", duration:<秒>}`；202 返回 job id，`GET /api/v1/videos/{id}` 轮询，完成后 `GET /api/v1/videos/{id}/content?index=0` 下载 mp4。轮询间隔/超时沿用现有 SiliconFlow 视频轮询常量。
  - 音频：`POST /api/v1/chat/completions`，`{model, modalities:["text","audio"], audio:{voice, format:"mp3"}, stream:true, messages:[...]}`；流式拼接 `delta.audio.data`（base64）。system 指令要求“逐字朗读用户内容，不增删”。
  - duration 处理：`round(shot.duration_estimate)` 后夹到模型支持区间（实现者从 OpenRouter 模型元数据或试错确定，最保守统一夹 [2,10] 秒，默认 5）。

### 4. 生成链路语义（Robert 定方向，降级规则为我的设计）

- **video_prompt 与出场角色的产出环节（审查后裁定）**：现有拆分镜是**纯确定性函数**（无 LLM），保持不变。改为在**生成剧本**环节扩展：LLM 产出的剧本每句 line 新增可选字段 `video_prompt`（英文：角色动作 + 运镜 [static/push-in/pull-back/pan 等] + 氛围）与 `characters`（出场角色名列表）；拆分镜时确定性映射——角色名匹配项目角色得 `ref_character_ids`（匹配不到的名字忽略并容错），`video_prompt` 直接落镜。剧本 JSONB 两字段均可选，旧剧本缺字段时拆出的镜 `video_prompt` 为空、`ref_character_ids` 回退为说话人，兼容不迁移。拆分镜接口维持同步毫秒级语义。
- **分镜图**：收集 `ref_character_ids` 中每个角色的封面图。按模型 `reference` 能力降级，**点名/兜底文本一律在队列生成时动态拼装，不写入存储的 `image_prompt`**（审查后裁定：存储的 prompt 保持纯场景描述，角色列表变更或换模型后不会留下错位的 "reference image N" 残留）：
  - `multi`：全部封面图按序进 `input_references`，动态前缀按序点名（"Max is the character in reference image 1…"）。
  - `single`：第一个角色的封面图作参考，其余角色外形描述动态拼进 prompt（现有兜底逻辑推广）。
  - `none`：全部角色外形描述动态拼 prompt。封面图缺失的角色一律按外形描述兜底。
- **图生视频**：prompt 用 `video_prompt`，为空回退 `image_prompt`；时长传 `round(duration_estimate)`（见 §3）。
- **stale 语义**：编辑 `video_prompt` → `video_stale`（镜像现有 `image_prompt` → `image_stale` 规则）；编辑 `ref_character_ids` → `image_stale`。重新拆分镜按现有规则覆盖/重建分镜。
- **合成归一化（审查后裁定）**：OpenRouter 各模型出图/出视频分辨率档位不一，且每镜可独立选模型；`FfmpegComposer` 的分段 concat 不能再假设统一 720x1280。合成时每个分段先重编码统一 scale+pad 到 720x1280（9:16 画布，不足部分黑边/模糊垫底由实现者定），再 concat。合成变慢可接受。

### 5. 前端（我的设计，沿用既有风格与组件）

- `ShotEditor`：新增「视频动作/运镜」textarea（紧挨画面 prompt 下方，同款样式）；「出场角色」从单选改多选（项目角色范围内的 chip 多选，复用既有 token 风格）。
- `ModelSelect`：选项按 provider 分组展示（`optgroup`：OpenRouter / SiliconFlow），其余交互不变。
- TTS 音色下拉数据源改为所选 TTS 模型条目的 `voices`。
- 剧本编辑器：line 的 `video_prompt`/`characters` 为可选字段，编辑剧本文本时不得丢弃它们（最低要求透传；是否在剧本编辑 UI 中暴露编辑入口留给实现者，工作台 ShotEditor 已是编辑主入口）。
- `types/aiVideos.ts`、`services/aiVideos.ts`、`aiVideos.mock.ts` 同步更新；mock 行为与真实接口语义一致。
- `docs/api/ai-videos.md` 同步：Shot 字段（`video_prompt`、`ref_character_ids` 替换 `ref_character_id`）、models 响应结构（`provider`、`reference`）。

### 6. 验证与测试（规范要求）

- 纯逻辑新行为全部进单测：参考能力三档降级、video_prompt 回退、stale 联动、`ref_character_ids` 子集校验、拆分镜解析容错。OpenRouter 客户端以 httpx mock 测请求组装与响应解析（含视频轮询、音频流拼接）。
- OpenAPI 冒烟快照（`tests/smoke/openapi_baseline.json`）随 schema 变更更新。
- 上架模型逐一真机冒烟（每模型一次最小调用），结果记录在模型清单注释。

## 留给实现者

- OpenRouter 各模型确切 slug、支持的 duration/resolution 档位、gpt-audio 实测可用音色——以实现当天 `GET /api/v1/models`（及 `?output_modalities=video`）与真机冒烟为准。
- 视频轮询的具体退避节奏、音频流式拼接的分块细节。
- 拆分镜 prompt 模板的具体措辞（满足 §4 输出契约即可）。

## 修订（2026-11-05，Robert 执行中指令）

**只用 OpenRouter，不保留 SiliconFlow 备选。** 覆盖以上各节中与 SiliconFlow 并存相关的决策：

- 模型清单只含 OpenRouter 条目，不需要 `provider` 字段；`reference` 档只剩 `multi` / `none`（Kolors 单图档随 SF 移除）。
- 不做多 provider 路由客户端；`get_av_client()`：配了 `OPENROUTER_API_KEY` → `OpenRouterAvClient`，否则 → `MockAvClient`（无 Key 全链路可跑的语义保留）。
- `SiliconFlowAvClient` 删除（git 历史可恢复）；`LLM_API_KEY`/`AV_IMAGE_SIZE` 等 SF 配置项保留给其他功能，ai-videos 不再使用。
- 前端模型下拉不做 provider 分组。
