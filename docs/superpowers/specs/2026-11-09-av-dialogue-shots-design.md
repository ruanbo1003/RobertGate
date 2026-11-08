# ai-videos 对白镜（音视同出）设计

日期：2026-11-09 ｜ 状态：待 Robert 批准

## 意图与背景

ai-videos 现状是"一镜一说话角色"：剧本每句台词拆一镜，走 分镜图 → i2v（无声）→ TTS 配音 → ffmpeg 合成。口型与声音天然不同步，且一镜内无法让多个角色对话。

经真机 PoC 验证（2026-11-09，两条样片在 Robert 桌面）：音视同出模型可以在一镜内让多角色轮流说话、口型同步。Robert 验收 Omni 效果可用，并拍板三个方向性决定（见"已决事项"）。

## 目标

1. 一个分镜支持多段台词（多角色轮流说话），口型与语音同步。
2. 所有含台词的镜头改走音视同出生成；成片管线适配"视频自带音轨"。
3. 字幕精确对齐到词级（本地 whisper），保持现有烧录体验。
4. 生成渠道可插拔：kie.ai 为主、OpenRouter Seedance 自动兜底。

## 非目标 / 反目标

- 不迁移旧项目已生成的产物（旧数据只做结构迁移，不重新生成）。
- 不做歌唱、不做单镜 >10s、不接 Veo（账号被 Google provider 封禁）。
- 不恢复 TTS 转写自检（Robert 已否决）。
- 反目标：为省钱混排 TTS 镜与 Omni 镜导致同一角色跨镜变声——Robert 明确选择整集声音风格统一。

## 已决事项（Robert 拍板）

1. **所有说话镜走 Omni 音视同出**，不保留"单人镜走 TTS"的混排。TTS 基础设施保留在代码中但退出说话镜链路（无台词的纯画面镜仍走旧 i2v，无音轨，合成时静音垫底）。
2. **字幕用本地 whisper 对齐**：从成片音轨转写词级时间戳，与已知台词模糊对齐生成 SRT；不走云端转写。
3. **对白镜由 LLM 拆分镜自动判定**：同一 scene 内连续对答的 lines 合并为一个对白镜，每镜 ≤4 句；工作台可手动增删/调整台词行（即手动拆合）。
4. 渠道与模型：主路由 kie.ai `gemini-omni-video`（实测 $0.023/s、60s 出片），兜底 OpenRouter `bytedance/seedance-2.0-fast`（实测 $0.091/s、160s 出片，`generate_audio: true`）。
5. 约束放宽说明：原"模型只用 OpenRouter"约束经 Robert 同意扩展为"OpenRouter + kie.ai"（因 OpenRouter 账单地区封禁 Google 系模型）。

## 数据模型

**角色音色（builder check 裁定，我的决定）**：`AvCharacter` 新增 `voice_desc: str` 文字字段（音色气质描述，如"温暖的大哥哥声""清脆的小女孩声"），用于 dialogue prompt；同一 0010 迁移内完成，默认空串。角色编辑弹窗（CharacterEditorModal）加一个文本输入。项目级 `tts_voice` 与创建表单音色下拉保留不动（纯画面镜/旧链路兼容），新链路不读。

`Shot` 的台词从单数字段改为列表：

- 新增 `dialogue: JSON` 列，结构 `[{"character_id": int|null, "en": str, "zh": str}, ...]`，1 条即单人镜，≥2 条即对白镜（无单独的"镜类型"字段，以列表长度为准；空列表 = 纯画面镜）。
- 迁移（alembic 0010）：旧 `speaker_character_id/line_en/line_zh` 有值的行转为单元素 `dialogue`；旧三字段保留列但废弃（不再读写），避免破坏性迁移。
- 产物语义：说话镜的 `video` 产物含音轨，`audio` 产物对新生成不再产生；`duration_estimate` 按全部台词长度估算后 snap 到模型档位（kie omni: 4/6/8/10）。
- 失效传播：`dialogue` 任一变更使 `video` 过期（沿用现有 `_STALE_RULES` 机制，`audio` 规则对说话镜退役）。
- **audio 产物退役的契约口径**（builder check 裁定，我的决定）：`dialogue` 非空的镜，`ShotOut.audio` 返回 `null`，`derive_project_status`/`missing_compose_items` 聚合时只要求 image+video 两产物（audio 不适用即不阻塞 completed 与合成）；纯画面镜 audio 同样不适用。旧迁移镜 dialogue 非空但磁盘留有 audio 文件——聚合同样跳过 audio，合成按"音频文件存在则 mux"分路（见生成链路第 4 条）。`docs/api/ai-videos.md` 与 openapi baseline、前端 types 同步更新。

## 生成链路

1. **Prompt 构建**（纯函数，TDD）：由出场角色名/外形简述 + 按序台词 + 音色气质描述（来自角色的 voice 描述字段，复用现有 tts_voice 语义改为文字描述）+ 固定尾缀（口型同步、无 BGM、清晰语音、镜头静止类指令）拼成 dialogue prompt。PoC 的 prompt 模板已验证，进代码时参数化。
2. **KieClient**（新增 `app/infrastructure/ai/av_client_kie.py`）：文件上传（`kieai.redpandaai.co/api/file-stream-upload`，24h 临时托管）→ `POST /api/v1/jobs/createTask` → 轮询 `GET /api/v1/jobs/recordInfo` → 下载 `resultJson.resultUrls[0]`。鉴权 `KIE_API_KEY`。
3. **路由与兜底**：`AvGenClient` 端口新增 `generate_dialogue_video(image, prompt, duration) -> bytes`；装配层组合 Kie 主 + OpenRouter Seedance 兜底（kie 提交失败/超时/任务 fail 时自动降级一次，日志记录降级原因）。兜底时长 snap 到 seedance 档位。
4. **合成**（builder check 裁定，我的决定）：按**音频产物文件是否存在**分路——该镜有 audio 产物文件 → 走旧 mux 路径（旧项目重合成不哑声）；没有 → 直接用视频自带音轨。说话镜 duration = 视频实际时长（ffprobe）。纯画面镜保持现状。
5. **模型记录与下拉**（builder check 裁定，我的决定）：说话镜的 `video_model` 记录**实际使用**的模型（带渠道前缀，如 `kie:gemini-omni-video`、兜底后 `openrouter:bytedance/seedance-2.0-fast`）；工作台说话镜的视频行模型展示为只读文本，i2v 模型下拉只保留给纯画面镜；`/models` 清单新增 `dialogue_video` 段（仅展示用）。

## 字幕（whisper 对齐）

- 依赖 `faster-whisper`（small 模型，中英混识别够用，CPU 可跑）；模型文件首次使用时下载，路径可配 `AV_WHISPER_MODEL`。
- 流程：成片合成前对每个说话镜的音轨转写（word timestamps）→ 与该镜已知台词做模糊对齐（台词为真值，whisper 只取时间；对齐失败回退"按台词长度均分镜时长"）→ 生成镜内多条 SRT 条目（对白镜每句一条，可带角色名前缀，默认带）。
- 对齐算法为纯函数，TDD 覆盖中英混、吞字、whisper 多识别/少识别的回退路径。

## 剧本拆分镜

- 拆分镜 LLM prompt 改为输出 `shots: [{dialogue: [{character_id, en, zh}], image_prompt, video_prompt, characters}]`——**每镜原有字段全部保留**（`image_prompt` 纯场景描述、`characters` 出场角色名单解析为 `ref_character_ids`，即 feature/av-scene-prompt 刚修复的角色一致性机制原样沿用，此前文档的 `setting_hint` 为简写笔误）；变化只有一处：`dialogue` 列表替代单句台词。同 scene 连续对答合并，每镜 ≤4 句、预估 ≤10s，超出拆镜。
- 目标时长换算从"每句一镜×5s"改为按台词时长估算。
- 校验函数 `validate_script`/拆分结果规范化同步更新（TDD）。

## 前端（工作台）

- ShotEditor：台词区改为**可增删排序的台词行列表**（每行：角色下拉 + 英文台词 + 中文释义），替代单"说话角色+台词"；产物区移除说话镜的"配音"行（视频行即含声音）；状态徽标不变。
- ShotTrack：对白镜显示参与角色数小标（如 `2人`）。
- 类型与 service 同步（`types/aiVideos.ts`、`services/aiVideos.ts` + mock）。
- UI 遵循 ui-style.md token；不新增颜色字体。

## 配置

`KIE_API_KEY`（.env.local 已有）、`KIE_BASE_URL`、`AV_DIALOGUE_MODEL=gemini-omni-video`、`AV_DIALOGUE_FALLBACK_MODEL=bytedance/seedance-2.0-fast`、`AV_WHISPER_MODEL=small`。

## 预备工作（动工前）

1. 提交当前未提交的 unslop 改动（HomePage/Navbar，挂在 feature/invest-reports 工作树上）。
2. `feature/av-scene-prompt`（4 个 ai-videos 修复 commit）合并回 main——与本功能同文件，不先合必冲突。
3. 新功能从 main 开分支 `feature/av-dialogue-shots`。
4. feature/invest-reports 分支的去留由 Robert 另行决定，与本功能无依赖。

## 风险与对策

- kie.ai 可靠性口碑差 → Seedance 自动兜底；余额小额充值策略（Robert 已知）。
- Omni 中文/中英混读质量量产波动 → 工作台单镜重生成本来就有；保留 PoC 脚本做回归样张。
- whisper 对齐失败 → 均分时长回退，字幕永不缺席。
- kie 的 `gemini-omni-video` 是平台别名，指向版本可能漂移 → 配置化模型 id，出问题可钉到带版本的 id。

## 留给实现者

模糊对齐算法选型、KieClient 的重试/超时参数、迁移脚本细节、台词行 UI 的交互微调、prompt 模板措辞。
