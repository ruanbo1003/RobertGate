# why-video 技术实现报告

> 把小朋友的"为什么"问题变成可发布的竖屏科普短视频——一个 Claude Code skill 的完整技术拆解。
>
> 日期：2026-10-27 · 代码：`.claude/skills/why-video/` · 复现脚本：本目录 `scripts/`

---

## 1. 它是什么

输入一个问题（如"地球为什么是圆的"），输出一条 **1080×1920 竖屏 MP4**：
AI 生成的连续视频画面 + 中文 TTS 旁白 + 烧录字幕，手机可播、可直接发抖音/视频号。

首条成片实测：8 个分镜、55.4 秒、22 MB，端到端约 30 分钟（绝大部分是视频生成排队）。

## 2. 总体架构

设计上只有两个部件，职责按"谁擅长什么"切分：

```
┌─────────────────────────────────────────────────────┐
│  SKILL.md（Claude 在会话里编排，干"需要判断"的活）     │
│  研究查证 → 写旁白 → 拆分镜 → 确认关卡 → 指挥返工      │
└──────────────────────┬──────────────────────────────┘
                       │ 写入 storyboard.json（唯一状态源）
                       ▼
┌─────────────────────────────────────────────────────┐
│  pipeline.py（单文件 ~470 行，干"确定性+花钱"的活）    │
│  verify     能力验证（key / ffmpeg / 模型清单）        │
│  generate   TTS + 视频生成（断点续跑、自动重试）        │
│  assemble   ffmpeg 合成（对齐、拼接、烧字幕）           │
└─────────────────────────────────────────────────────┘
```

**为什么这样切**：轮询几分钟的视频生成、中断续跑、只重做第 N 段——这些逻辑靠大模型
现场发挥偶尔会错，而每次错都是真金白银；收进脚本后行为确定。反过来，查证科学事实、
写儿童旁白、把画面翻译成英文 prompt，是模型的强项，写死成代码反而僵硬。

**两幕式 + 硬性确认关卡**：第一幕（研究+写稿）免费，第二幕（生成+合成）花钱，
中间必须把"旁白全文 + 分镜表 + 预计时长 + 预计成本"摆给用户过目，确认前禁止任何生成调用。

## 3. 数据模型：storyboard.json

每个视频一个项目目录 `output/why-videos/<YYYYMMDD>-<slug>/`，机器状态全部存在
`storyboard.json`（schema 固定在 pipeline.py 模块 docstring）：

```json
{
  "question": "地球为什么是圆的",
  "voice": "FunAudioLLM/CosyVoice2-0.5B:anna",
  "video_model": "Wan-AI/Wan2.2-T2V-A14B",
  "scenes": [{
    "id": 1,
    "narration": "一句或两句旁白词",
    "visual_zh": "画面中文描述（给人看）",
    "visual_prompt_en": "english prompt（给视频模型）",
    "status": "pending | audio_done | done | failed",
    "audio_file": "clips/scene-1.mp3",
    "clip_file": "clips/scene-1.mp4",
    "audio_duration": 5.928,
    "error": ""
  }]
}
```

三条设计规则：

1. **原子落盘**：每次写盘都是"写临时文件 → `os.replace`"，进程在任何时刻被杀，
   状态文件都不会半截损坏（`save_board`，pipeline.py）。
2. **每步后立即落盘**：TTS 完成落一次、视频完成落一次。断点续跑的粒度是"半个分镜"。
3. **状态机**：`pending →(TTS) audio_done →(视频) done`，任何一步失败 → `failed` 并记
   `error`。续跑时 `scenes_todo()` 返回所有非 `done` 的分镜；`--redo N` 则把指定分镜
   重置回 `pending`（**确认通过后才落盘**，取消不留暗雷）。

## 4. 流程逐步拆解

### 第 0 步：verify（免费）

```
backend/.venv/bin/python .claude/skills/why-video/pipeline.py verify
```

逐项检查并打 ✅/❌：

| 检查项 | 实现 |
|--------|------|
| API key | env `SILICONFLOW_API_KEY` 优先，否则解析 `backend/.env.local` 的 `LLM_API_KEY=` 行；不打印 key 本身 |
| ffmpeg/ffprobe | `shutil.which`；**另查 `ffmpeg -filters` 输出含 ` subtitles `**（烧字幕需 libass，见 §8 踩坑） |
| 视频模型 | `GET /v1/models?sub_type=text-to-video` → 实测可用 `Wan-AI/Wan2.2-T2V-A14B` |
| TTS 模型 | `GET /v1/models?sub_type=text-to-speech` → 实测可用 `FunAudioLLM/CosyVoice2-0.5B` |

`--full` 额外做一句试音 + 一段测试视频（花钱，执行前有提示）。验证不过 → 停下报告，
不自行降级（不许偷偷换供应商、不许 16:9 裁剪冒充竖屏）。

### 第一幕：研究与脚本（Claude 侧，免费）

1. **研究**：WebSearch 查证，**至少两个独立来源互证**。原则：给儿童简化可以，简化到错
   不行；两来源数字打架的细节（比如"多大才会变圆"的公里数）直接不讲，规避讲错。
2. **写旁白**：4-8 岁讲故事语气——孩子熟悉的事物引入 → 层层解释 → 温暖收尾。
   每分镜 15-35 字（约 4-9 秒语音，匹配视频片段时长量级）。
3. **拆分镜**：每镜 = 旁白 + `visual_zh`（给人看）+ `visual_prompt_en`（给模型）。
   英文 prompt 统一追加 `bright, warm colors, child-friendly, gentle, soft lighting`
   ——这是防"画面阴暗吓到小孩"的第一道防线（第二道是人工看成片，第三道是单镜重做）。

### 确认关卡（硬性）

展示旁白全文 + 分镜表 + 预计时长（字数÷4.5字/秒 估算）+ 预计成本（分镜数 × 单价），
等用户修改或确认。**确认前第二幕的任何 API 都不许碰。**

### 第二幕：generate（花钱）

```
backend/.venv/bin/python .claude/skills/why-video/pipeline.py generate <项目目录> --yes
```

对每个待办分镜顺序执行：

**① TTS 先行**（`POST /v1/audio/speech`，CosyVoice2，mp3 落盘）
→ 用 **ffprobe 实测音频时长**写回 `audio_duration`。
这是整条流水线的"时长之锚"：视频片段最终都要被对齐到旁白的真实长度，
所以必须先有音频、后定视频。

**② 视频生成**（异步两段式）：
- `POST /v1/video/submit` `{model, prompt, image_size: "720x1280"}` → `requestId`
- `POST /v1/video/status` 每 10 秒轮询，900 秒超时；`Succeed` → 取 url 下载落盘，
  `Failed`/超时 → 抛 `VideoGenError`

**③ 可靠性三件套**（都有对应测试锁死）：
- **失败自动重试 1 次**（重新 submit），再失败才标 `failed`、记原因、**继续下一个分镜**，
  结尾统一汇总并退出码 1——一个分镜倒下不拖累整批。
- **TTS 需求看产物不看状态**：`音频文件不存在 or audio_duration==0` 才做 TTS。
  否则"TTS 阶段失败 → 续跑"会跳过配音直接烧视频钱、产出坏项目（终审 Critical，已修）。
- **httpx 异常收口**：`httpx.HTTPError`（连接重置、超时、HTTP 4xx/5xx）在
  `_request`/`tts_to_file`/`download` 内部统一转 `RuntimeError`，外层按分镜捕获。
  否则 15 分钟轮询里一次网络抖动会裸崩整个 generate（终审 Important，已修）。
  首条视频实测就命中：第 6 镜 TTS 遇 `Connection reset by peer` → 标 failed 继续，
  其余 7 镜照常完成，重跑一次只补第 6 镜。

### assemble：ffmpeg 合成

```
backend/.venv/bin/python .claude/skills/why-video/pipeline.py assemble <项目目录>
```

前置校验：所有分镜 `done`，否则中文报错退出。然后四步：

**① 生成字幕 `subs.srt`**（纯 Python，`build_srt`）：
- `split_lines`：标点优先断行（`，。！？…`等），超长再按"不可拆单元"硬切——
  正则 `\d+(?:\.\d+)?[^\s标点]{0,2}|[A-Za-z]+|.` 把"8000公里"、英文单词当整体，
  不会出现"它有8 / 000公里"这种断法；
- 时间轴：分镜起始时间逐镜累计（= 前面所有 `audio_duration` 之和），
  镜内各行按**字符数占比**瓜分本镜时长。

**② 逐镜归一 `align_scene`**，滤镜链逐个参数的作用：

```
scale=1080:1920:force_original_aspect_ratio=decrease   # 等比缩入 1080x1920 盒子
pad=1080:1920:(ow-iw)/2:(oh-ih)/2:color=black          # 不足处居中补黑边 → 任意输入分辨率都归一
tpad=stop_mode=clone:stop_duration=<旁白时长+1>          # 视频比旁白短 → 末帧定格补齐
fps=30,format=yuv420p                                   # 统一帧率/像素格式（为 ③ 的无损拼接做准备）
-t <旁白时长>                                            # 视频比旁白长 → 截断；输出段长 = 旁白长
-c:v libx264 -c:a aac -ar 44100 -ac 2                   # 统一编码参数
```

**③ 拼接**：concat demuxer + `-c copy`（零转码）。能 `-c copy` 的前提正是 ② 把所有段
的编码参数做齐了——这是 concat 最经典的翻车点。

**④ 烧字幕**：`subtitles=subs.srt:force_style='FontSize=15,Bold=1,...,MarginV=58'`。
两个细节：`MarginV` 以 libass 默认 `PlayResY=288` 为基准，58 ≈ 底部 1/5 处；
subtitles 滤镜的文件路径转义很麻烦（中文/冒号），**绕法是 `cwd=srt所在目录` + 相对文件名**。

### 返工

"重做第 N 段（+新要求）" → 更新该分镜的 prompt/旁白 → `generate --redo N --yes`
（只重置点名的分镜，其余 `done` 复用缓存）→ `assemble` 重新合成。

## 5. 测试策略（28 个用例）

| 层 | 手段 | 覆盖 |
|----|------|------|
| 纯函数 | 直接断言 | slug 非法字符、key 查找顺序、续跑选择、`--redo` 只重置点名镜、字幕断行（标点/数字单位/空行）、SRT 时间轴累计、原子读写 roundtrip |
| HTTP 层 | monkeypatch `_request`（全部 JSON HTTP 收敛在这一个函数，就是为了可 mock） | 轮询 Succeed/Failed/超时、超时后不再多轮询 |
| generate 编排 | 注入 fake 的 tts/submit/poll/download | 失败重试恰好 1 次、失败不拖累后续、done 不重复提交、**TTS 失败续跑必补配音**、redo 取消不落盘 |
| 异常收口 | 真 httpx 连 `127.0.0.1:9`（必拒绝） | 三个网络函数都转 RuntimeError |
| ffmpeg | 真 ffmpeg + lavfi 合成测试素材（蓝屏 640×480/2s + 正弦波 3s），无网络无成本 | 输出必为 1080×1920、时长=音频时长（±0.3s） |

原则：**凡是"算错就浪费钱"的逻辑必须有测试**；mock 点收敛到 4 个函数边界，测试完全不碰网络。

## 6. 工程决策记录（为什么这么做）

| 决策 | 理由 |
|------|------|
| 单文件 pipeline.py 而非完整模块/TDD 全家桶 | 个人工具"先跑通"；只给花钱环节上确定性+测试，是成本和稳定性的折中（用户选型） |
| 旁白由会话中的 Claude 直接写，不再过一遍 DeepSeek API | 研究上下文已在会话里，转一手 API 反而丢上下文、多一跳、多花钱 |
| TTS 先于视频 | 旁白真实时长是对齐锚，反过来做就要削旁白迁就视频 |
| 视频统一 720x1280 生成、合成时放大到 1080x1920 | Wan2.2 原生竖屏档位；放大+pad 由 ffmpeg 统一兜底，对任意分辨率鲁棒 |
| 确认关卡放在 Claude 编排层而非脚本层 | 要展示的是"给人看的"旁白+分镜表，且用户的修改意见需要被理解执行——这是模型的活 |
| 成片画面不做自动审查 | v1 范围裁剪：prompt 风格词 + 人工看片 + 单镜重做三道防线兜底 |

## 7. 实测数据（首条视频：地球为什么是圆的）

- 8 分镜，旁白 220 字；成片 55.4s / 1080×1920 / H.264+AAC / 22 MB
- TTS 实际调用 9 次（1 次网络重置失败）；视频生成 8 段全部一次成功
- 续跑验证：失败后重跑同一命令，7 个 done 分镜零重复扣费，只补了第 6 镜
- 合成（8 段归一 + 拼接 + 烧字幕）本地 ffmpeg 约几十秒

## 8. 踩坑记录

1. **Homebrew 新版 `ffmpeg` 是瘦身构建，没有 libass**（只有 8 个外部库），
   `subtitles` 滤镜不存在，烧字幕必崩。完整构建在 keg-only 的 **`ffmpeg-full`**
   （装在 `/opt/homebrew/opt/ffmpeg-full/bin`，不进 PATH）。pipeline 的 `_tool()`
   优先探测该路径、退回 PATH；verify 的指引也必须写 `ffmpeg-full`——写成 `ffmpeg`
   会让新机器陷入"装了还是缺"的死循环（终审发现的文案 bug）。
2. **`httpx` 的网络异常不是 `RuntimeError` 子类**：`ConnectError`/`ReadTimeout`/
   `HTTPStatusError` 都继承自 `httpx.HTTPError`。只 `except RuntimeError` 等于没接，
   必须在网络函数内部显式收口转换。
3. **"failed" 一个状态装不下两种失败**：TTS 失败和视频失败的续跑动作不同。
   与其扩状态机，不如让 TTS 需求判定直接看产物（文件在不在、时长是不是 0）——
   更简单且天然幂等。
4. **SRT 字幕在竖屏上的字号/边距**：`force_style` 的单位基于 libass 内部
   `PlayResY=288` 坐标系而非像素，想当然按 1920 算会大 6.7 倍。

## 9. 复现指南

本目录 `scripts/` 提供可独立运行的脚本（不依赖 Claude 会话），用 2 分镜小样本演示全流程，
视频生成花费约 ¥2：

```bash
docs/why-video/scripts/01-verify.sh          # 免费：能力验证
docs/why-video/scripts/02-new-project.sh     # 免费：用样例分镜建项目目录
docs/why-video/scripts/03-generate.sh <目录>  # 花钱：TTS + 视频生成（约 ¥2）
docs/why-video/scripts/04-assemble.sh <目录>  # 免费：本地合成 final.mp4
# 或一键全流程：
docs/why-video/scripts/run-demo.sh
```

前置条件：`backend/.venv` 已建好（含 httpx）、`backend/.env.local` 配有 `LLM_API_KEY`、
`brew install ffmpeg-full`。

日常使用不需要这些脚本——直接对 Claude 说"为什么……"触发 skill 即可，
脚本的价值是**脱离会话复现**与排障。
