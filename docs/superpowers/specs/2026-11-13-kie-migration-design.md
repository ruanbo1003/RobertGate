# ai-videos 主通道迁移 kie.ai 设计

日期：2026-11-13 ｜ 状态：待 Robert 批准

## 意图与背景

2026-11-13 OpenRouter 官方答复确认：Robert 的账号被限制使用**闭源三家（Anthropic / Google / OpenAI）**的模型，理由是"遵守厂商访问政策"。原文：

> Your account has been restricted from using closed-weight models (Anthropic, Google, and OpenAI) to comply with provider access policies.

这依次修正了 11-08 的"封出口 IP 段"和 11-12 的"全账号封禁"两次误判：**不是封号，是闭源三家被剔除**，其余厂商（bytedance、kwaivgi、deepseek 等）在 OpenRouter 上照常可用。11-12 看起来像"全模型封禁"，只因当时抽的样本恰好全是这三家。

ai-videos 当前四条能力线（llm / t2i / i2v / tts）全部压在 OpenRouter 上，其中 **llm、t2i、tts 的默认模型全是 Google 或 OpenAI**，即刻失效。

kie.ai 是另一条合规路径，**不受该限制**，且本项目已真机验证过（2026-11-09 对白镜 `gemini-omni-video`，`av_client_kie.py` 已在生产跑）。kie.ai 的市场覆盖 Chat / Text to Image / Text to Video / Image to Video / Text to Speech 全部所需分类，并且照样能调 Google、OpenAI、Anthropic 的模型。

## 目标

1. **三条能力线（llm / t2i / i2v）**切到 kie.ai，**能力与用户可见行为保持与当前一致**。
2. 历史数据（已落库的模型 id、音色）不被迁移破坏，存量项目迁移后仍可继续生成。

### TTS 不在范围内（第四轮已决，Robert 2026-11-13）

执行期核查发现 **TTS 是死链路**：11-09 对白镜改造后，说话镜全走音视同出（语音长在视频里），生成端两处入口全被拦死——对白镜被 `av_service.py:522` 拒绝（"对白镜无独立配音"），非对白镜因新建 shot 时 `line_en=""` 恒空被 `:524` 拦截；0010 迁移又把旧 `line_en` 数据转进了 `dialogue`。`generate_speech` / `AV_MODELS["tts"]` / `AV_TTS_TEMPO` / pcm16 转码整套均为死代码，唯一活的消费是合成管线读旧项目磁盘残留的 audio.mp3（不触发上游调用）。

**决定：tts 不迁。** 注册表 tts 段、`/ai-videos/models` 返回、`project.tts_voice`、创建表单音色下拉全部原样保留（保 API 契约）；原"决策 3：TTS 换家（ElevenLabs）"整节作废。清理死功能属另一个需求，不混进本次。

## 非目标 / 反目标

- 不改业务逻辑：`av_queue` 的调度与并发策略、`av_dialogue`、合成管线、前端工作台的交互一律不动。**唯一允许的越界点**是 `docker/nginx.conf` 的超时配置（见决策 6）。
- 不改端口契约 `ports.py`（第三轮决定砍掉兜底后，`(bytes, tag)` 的改造失去理由）。
- 不重新生成任何已有产物。
- 不接 SiliconFlow。
- **不为四条线配跨通道兜底。**
- **不删除 `OpenRouterAvClient`** —— 对白镜的兜底链路仍在用它（见决策 5）。
- 不换 MaaS 平台（2026-11-13 评估过 APIMart / Atlas Cloud / WaveSpeedAI 等 OpenAI 兼容聚合，结论见"决策演进"第三轮）。
- 反目标：为了"看起来有容灾"而配一个质量明显劣化的兜底通道，导致同一项目内出图风格或配音音色不一致。宁可没有兜底，也不要静默降质。

## 决策演进（三轮，保留轨迹便于回看）

**第一轮（brainstorm）**：Robert 定"四条线能力保持跟当前一样"、"OpenRouter 留着当兜底"、"TTS 不兜也不用 SiliconFlow"。模型按**同源平移**选型（我的决定）。

**第二轮（builder check 之后）**：Robert 定 A 角色设定图用加长 nginx 超时扛过去、B 改端口契约让兜底 tag 落库、C 用生产 Key 小额验证。

**第三轮（Robert 质疑工程量）**：Robert 问"迁移不就是换个 URL + key 吗"。核查结论——
- llm 确实是（kie 有 OpenAI 兼容 `chat/completions`）；
- t2i / i2v / tts 不是（kie 这三条走 `jobs/createTask` 异步轮询，与 OpenRouter 的同步 `/images`、异步 `/videos`、流式音频三种形态都不同）；
- **11 个任务里有 3 个纯粹是"保留兜底"的成本**（tag 格式、ChannelRouter、端口契约），与迁移本身无关。

Robert 随后问是否有"跟 OpenRouter 一样用法但不限三家"的 MaaS。查到 APIMart / Atlas Cloud / WaveSpeedAI / ToAPIs / CCAPI / RouterBase 等候选，但**视频生成不存在同步接口**（模型要跑 1–3 分钟），各家异步形态又无行业标准，"OpenAI 兼容"实际只覆盖 `chat/completions`——换平台救不了 i2v，且换不掉根因（厂商地区政策 + 大陆出口 IP）。

**Robert 拍板：维持 kie.ai，砍掉 OpenRouter 兜底。** 由此推翻第一轮的"留着当兜底"与第二轮的 B；第二轮 A、C 保留。

## 模型选型

按**同源平移**原则（我的决定）：尽量选与现用模型同一家、产出风格最接近的，把迁移的意外面压到最小。

| 线 | 现在（OpenRouter，已失效） | 迁到（kie.ai） | 备注 |
|---|---|---|---|
| llm | `google/gemini-3.8-flash` | Gemini 4 | 同源 |
| t2i | `google/gemini-3.1-flash-image` | Nano Banana 2（$0.04/1K 图） | Nano Banana 即 Gemini 图像模型代号，同源 |
| i2v | `bytedance/seedance-2.0-fast` | `bytedance/seedance-2-fast`（真机核实的 kie id） | 同名模型换 id 拼法 |
| tts | `openai/gpt-audio` | **不迁（死链路，见目标节）** | 注册表原样保留 |
| dialogue | `kie:gemini-omni-video` | **不动，本次不碰** | 已在生产跑 |

llm 的 kie id 经真机核实为 `gemini-3-8-flash-openai`（`-openai` 后缀 = 走 OpenAI 兼容端点，与现用 `google/gemini-3.8-flash` 同一模型，同源平移零落差）。省钱档一并进注册表但不设 default：t2i 的 Seedream 5.5。**通道内换模型是本设计唯一的容灾手段**。

## 关键设计决策

### 1. 模型 id 与历史数据 —— 分两类，不能一刀切

四条线是单通道（kie），**模型 id 用裸 id 即可，不加渠道前缀**。`dialogue_video` 段维持现有的 `kie:` / `openrouter:` tag 格式不变（它是真·跨渠道段）。

历史落库数据分两类：

- **溯源字段**（`AvAsset.image_model` / `video_model` / `audio_voice`，只读只展示）：老值原样保留可读，不迁移、不改写。
- **活配置字段**（`av_projects.default_models` JSONB、`av_projects.tts_voice`）：**这两个是每次生成时真正取用的值**。`av_service.py` 的 `effective_model = model or project.default_models[...]` 和 `av_queue.py` 的 `voice = item.voice or shot.audio_voice` 都读它。老项目存的是 `google/gemini-3.1-flash-image`、`openai/gpt-audio`、`alloy` —— **迁移后这些模型一个都调不通，不处理则每次生成必失败**。

  **决定：读取时校验 + 回退，不做数据迁移、不加 alembic。** 取用时若值不在当前注册表内，回退到该能力线的新 default 并打 info 日志。理由：存量数据不动（幂等、可回滚）；用户在工作台改一次模型即自然写入新 id。代价是老项目里用户原先选的 Gemini 会被静默换成同源的 Nano Banana —— 符合同源平移原则，且不换就是必然失败。

**施工陷阱**：`snap_duration()` 与 `reference_mode()` 都按注册表 id **精确匹配**。注册表 id 换成 kie 的新 id 后，若调用侧传的还是老 id，匹配会全部落空，悄悄掉进 `max(2, min(10, seconds))` / `return "none"` 的兜底分支——duration 档位失效、`multi` 降成 `none`（**角色跨镜变脸**），**不报错、不告警**。两者各补一条单测。

### 2. kie.ai 的两套接口形态

- **Chat（llm）**：OpenAI 兼容的同步 `chat/completions`，支持 JSON schema。`generate_json` 可近乎原样平移。
- **图像 / 视频 / TTS**：异步 `jobs/createTask` + 轮询 `jobs/recordInfo` + 下载 `resultJson.resultUrls[0]`。**`av_client_kie.py` 已经把这套踩通了**（上传、轮询、下载、配额错误映射），新客户端复用其骨架，不重写。

新客户端 `KieAvClient` 实现与 `OpenRouterAvClient` 相同的五方法契约，`AvClientWithDialogue` 与 `MockAvClient` 保持不动。

### 3. ~~TTS 换家~~（已作废，见"目标 → TTS 不在范围内"）

### 4. kie.ai 的 429 必须从配额错误里拆出来

`av_client_kie.py` 现在把 401/402/429 一律映射成 `AV_UPSTREAM_QUOTA`，队列据此**全局暂停**且需人工重新入队才恢复。今天没出事是因为 kie 只承载对白镜、并发为 1。迁移后四条线全压 kie，队列并发是 image 2 + video 1 + audio 2 共 5 路——**若 kie 用 429 做速率限制，一次瞬时限流就会把整条产线停掉**。

注意这不是"映射是否一致"的问题：即便 kie 的错误码与现有映射完全一致，该语义在新的并发模型下也是错的。

**决定**：沿用 `OpenRouterAvClient` 已有的区分做法——**只有 401/402，以及响应体里带 `balance`/`credit` 字样的 429，才算 `AV_UPSTREAM_QUOTA`**；其余 429 按 `AV_UPSTREAM_FAILED` 处理，让单个产物失败、其余继续跑。不动 `av_queue` 的并发上限。

### 5. 工厂装配与 OpenRouter 的去留

现在：`if settings.OPENROUTER_API_KEY` → OpenRouter，否则整体 `MockAvClient`。

**改为**：以 `KIE_API_KEY` 为判据。
- 有 `KIE_API_KEY` → 四条线装 `KieAvClient`。
- 无 `KIE_API_KEY` → 整体 `MockAvClient`（保持"无 Key 环境全链路可走通"的现有语义不变）。

**`OpenRouterAvClient` 保留不删**：对白镜的 `DialogueVideoRouter` 仍拿它的 `generate_video` 当兜底，该链路在生产跑着，不在本次范围内。装配时它**只提供给 `DialogueVideoRouter`**，四条线不再经过它。其余四个方法变成死代码但保留——删除需要连带改测试，收益为零，且将来恢复兜底时还要写回来。

config 需新增 kie.ai 的 Chat 端点 base（OpenAI 兼容端点与现有 `KIE_BASE_URL` 的 jobs 端点不同源）。`KIE_API_KEY` / `KIE_BASE_URL` / `KIE_UPLOAD_BASE_URL` / `OPENROUTER_API_KEY` 均已存在。

### 6. 角色设定图的同步请求：加长 nginx 超时

`POST /ai-videos/characters/{id}/generate-image` 在**同一个 HTTP 请求里**直接 `await generate_image(...)` 并返回（`av_service.py:182`）。今天能用是因为 OpenRouter 的 `/images` 是同步端点；kie.ai 的图像生成是 createTask + 轮询，可能跨过 nginx 默认 60s `proxy_read_timeout`。分镜图走队列不受影响，只有这一条路径是同步的。

**决定（Robert 第二轮 A）：改 `docker/nginx.conf` 加长该路径的 `proxy_read_timeout`（建议 180s），不改接口形态、不动前端。**

配套（我的决定）：kie 客户端的**图像轮询间隔从沿用视频的 10s 降到 2–3s**。现有 10s 是为分钟级视频任务定的，拿来轮十几秒出完的图会让单图白白多等一个轮询周期，正是这条路径最吃不起的开销。

**诚实记录这个权衡**：这是治标。请求会挂着占用一个 worker，图再慢仍会超时。真机验证测出的单图耗时若接近 180s，这条路不成立，需回到"改异步 + 前端轮询"。

## 必须真机验证的事项

下列每条都会改变设计，**施工前用最小调用逐条钉死**，不要照着文档里的猜测写。用对白镜在用的生产 `KIE_API_KEY`，按最小调用来（Robert 第二轮 C）。**动手前先查一次余额并报给 Robert** —— 验证期间若把余额打到 402，生产的对白镜生成会触发全局暂停。

1. **kie.ai Chat 的确切端点 URL 与请求体**，以及 JSON 模式字段。
2. **Nano Banana 2 在 kie.ai 上是否支持多参考图**。这是**角色一致性的命脉**（注册表 `reference: "multi"` 档）。若 input 结构不支持多图输入，角色跨镜会变脸 —— 产品级退化，**停下来回报 Robert，不要自行降级成 `none` 蒙混过去**。
3. **t2i 的 9:16 竖屏**怎么传。ai-videos 是竖屏短视频，比例错了整条产线作废。
4. **i2v 各模型的 duration 档位**。现有 `durations` 是 OpenRouter 真机 400 报错实测出来的，kie 侧档位可能不同，`snap_duration` 依赖它。
5. **ElevenLabs 的 voice_id 清单**与返回音频格式（mp3 / wav），决定 `voices` 字段与是否还需转码。
6. **kie.ai 的配额/鉴权错误码**，以及**限流 429 的响应体长什么样**（决定决策 4 里 `balance`/`credit` 关键字的判别能否生效）。
7. **t2i 单图实际耗时**与有无同步端点（决定决策 6 的 nginx 方案成不成立）。

## 测试策略

遵循 `.claude/rules/backend.md`：新功能必须附带单元测试，覆盖率目标 80%+。参照现有 `tests/unit/test_av_client_factory.py` 的模式，用 `httpx.AsyncBaseTransport` 打桩，不打真实网络。

- `KieAvClient` 五方法：成功、上游 4xx/5xx、配额码、轮询超时、产物缺失、多参考图确实抵达上游。
- **429 语义拆分**：带 `balance`/`credit` 的 429 → `AV_UPSTREAM_QUOTA`；不带的 → `AV_UPSTREAM_FAILED`。两条各一个用例。
- **活配置回退**：老项目 `default_models` 存 `google/gemini-3.1-flash-image`、`tts_voice` 存 `alloy` 时，取用侧回退到新 default 且不抛异常 —— 这条是存量项目迁移后还能不能用的唯一保障。
- **id 精确匹配**：`snap_duration` / `reference_mode` 在新 id 下不得落到兜底分支。
- 工厂装配：有/无 `KIE_API_KEY` 两种组合各自落到什么客户端；确认 `OpenRouterAvClient` 仍只挂在 `DialogueVideoRouter` 上。
- 对白镜链路无回归：`test_av_dialogue_router.py` 全绿。
- openapi 快照回归（`tests/smoke/`）随模型 id 变更更新 baseline。

## 留给施工者

- `KieAvClient` 是扩展现有 `av_client_kie.py` 的 `KieVideoClient`，还是新建类并复用其私有方法 —— 看真机验证第 1 条的结果（Chat 走同步端点，与现有异步 jobs 骨架不同源，可能不适合塞进同一个类）。
- 各线超时与轮询间隔的具体取值（图像轮询 2–3s 已定，其余自行判断）。

## 风险

1. **kie.ai 是完全单点**。四条线 + 对白镜主通道全压 kie.ai，其余额耗尽或服务中断会同时打掉整个 ai-videos 的生成能力。砍掉兜底是 Robert 2026-11-13 的明确决定（理由：OpenRouter 自身已只剩非三家模型，作为兜底本就残缺——t2i 要跨家降质、tts 根本兜不了，买不到对等价值）。

   **仅有的缓解**：`AV_UPSTREAM_QUOTA` → 队列全局暂停的机制仍然生效，余额耗尽时不会无脑烧钱，但恢复依赖人工充值；以及注册表内的省钱档可供手动切换。**对白镜是唯一仍有兜底的链路**（OpenRouter seedance）。

2. **真机验证第 2 条（多参考图）若失败**，角色一致性退化，这次迁移的价值要重新评估。属于必须回报而非自行决定的事项。

3. **根因未解**：被限的诱因八成是 hk 服务器的大陆出口 IP（118.26.37.92）触发厂商地区访问政策。kie.ai 目前不受影响，但同样的压力对任何正规对接 Google/OpenAI 的平台都存在。**服务器出口走境外是独立于本设计之外、仍待处理的事项。**

## 真机探测结果（2026-11-13，Task 1）

余额 828 → 249.59 credits。**duration 档位扫描误开 4 个 seedance 视频任务烧掉约 558 credits（无取消端点）**——createTask 校验通过即计费，教训已吸收：探档位只试非法值。

| # | 结论 |
|---|---|
| 1 | Chat：`POST https://api.kie.ai/v1/chat/completions`，OpenAI 标准形态，`response_format: {"type":"json_object"}` 生效；模型 `gemini-3-8-flash-openai`（不带 `-openai` 的同名 id 属 jobs 侧，422）。0.01 credits/次 |
| 2 | **多参考图 ✅**：`input.image_urls` 数组，2 张均生效且按序可区分（红三角/蓝方块验证图）。上传走 `file-stream-upload` 两次各拿 downloadUrl |
| 3 | **9:16 ✅**：`input.aspect_ratio: "9:16"`，实出 768×1376 |
| 4 | i2v `bytedance/seedance-2-fast`：duration 为字符串；3 → 422 "Invalid duration"，4/5/6/8 合法；**10/12/15 因余额 402 未探明**，注册表先用 4/5/6/8 保守档，充值后补 |
| 5 | TTS：入参 `text` + `voiceId`（驼峰；缺 voiceId → 422 "voiceId cannot be empty"）。**已随 tts 剔除失去意义，voiceId 清单未探** |
| 6 | **HTTP 状态码恒 200，错误码在 body `code`**（401/402/422/500 皆然，两套端点一致）。402 文案 "Credits insufficient : Your current balance isn't enough…"。⚠️ 现有 `av_client_kie.py` 通篇 `resp.status_code >= 400` 判错**从未生效**——生产对白镜的配额暂停机制一直失效，本次顺带修 |
| 7 | **单图 10s**（nano-banana-2 costTime=10），nginx 180s 方案成立且余量大 |
| + | **recordInfo 响应体可能是非法 JSON**：`param` 字段嵌套转义缺层，`resp.json()` 直接抛 JSONDecodeError。新客户端必须容错（如先剥 `param` 再解析，或用正则提取 state/resultJson） |
| + | `recordInfo` 带 `creditsConsumed` 字段，可做成本追踪；成功态 `state: "success"`，结果在 `resultJson.resultUrls[0]` |

## 端到端联调记录（2026-11-13，Task 9）

真机直打客户端层（service/queue 层由 550 条单测覆盖）：

| 链路 | 结果 | 耗时 | 产物 |
|---|---|---|---|
| llm generate_json | ✅ `{"ok": true}` | 6.6s | — |
| t2i 角色设定图（无参考） | ✅ | 29.7s / 14.3s 两次 | 768×1376 (9:16) |
| t2i 分镜图（1 参考图点名） | ✅ | 16.5s | 768×1376 |
| i2v seedance-2-fast 4s | ✅ | 100.7s | 720×1280，带 AAC 音轨 |
| 对白镜 omni 回归（_parse_body 重构波及） | ✅ | 57.8s | 720×1280，AAC |

- 角色设定图同步路径实测 14–30s < 180s，nginx 方案余量充足。
- **seedance 有内容审核**：卡通狐狸形象被拒 "copyright restrictions"（疑似撞 IP），失败任务**不扣费**，state=fail → ServerException 路径真机验证通过；换原创形象后通过。生产提示词需避开知名 IP 相似形象。
- i2v 即使不开 generate_audio 也带 AAC 音轨（静音），合成管线按 has_audio_stream 分路可处理。
- 老项目活配置回退未做真机（需起库），由单测三条覆盖（test_legacy_*）。
- 花费：Task 9 共 ~170 credits；**余额 63.38 credits（≈$0.32），生产对白镜只够 1–2 条，需充值**。

## 待补事项（充值后）

1. **i2v 10s+ duration 档位补探**（只试非法值！合法值会建任务即计费），补进注册表 `durations`。
2. **i2v 第二款模型真机验证入表**——seedance 有内容审核（版权相似即拒），单模型没有通道内容灾（final review I3）；候选：`bytedance/seedance-2` / `kling-3.0-omni/image-to-video`。
3. seedream 5.5 已真机验证（出图 + 9:16，1584×2816，2026-11-13 修复轮）；参考图能力未验，维持 `none` 档。
4. gpt-5.5 真机 422 已从注册表摘除；/v1/models 列表不可信，新条目入表前必须真机调通。
