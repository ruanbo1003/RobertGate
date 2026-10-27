---
name: why-video
description: 把小朋友的"为什么"问题变成可发布的竖屏科普短视频。触发词：为什么、科普视频、给小朋友讲、why-video。流程：联网查证 → 写儿童旁白与分镜 → Robert 确认 → SiliconFlow 生成视频+TTS → ffmpeg 合成 MP4。
---

# why-video：小朋友科普视频生成

把一个"为什么"问题（如"地球为什么是圆的"）变成 9:16 竖屏科普短视频，
手机可播、可发自媒体。两幕式：第一幕免费（研究+写稿），第二幕花钱（生成+合成），
**中间有一道硬性确认关卡**。

所有命令在仓库根目录执行，统一用：
`backend/.venv/bin/python .claude/skills/why-video/pipeline.py <子命令>`

## 第 0 步：能力验证（首次使用，或上次验证失败后）

```
backend/.venv/bin/python .claude/skills/why-video/pipeline.py verify
```

不通过则**停下向 Robert 报告**，不得继续。缺 ffmpeg 时给出指引：
`brew install ffmpeg-full`（注意：瘦身版 ffmpeg 没有烧字幕所需的 libass）。
不得自行换 AI 供应商或把竖屏降级为 16:9 裁剪——那是 Robert 的拍板项。

## 第一幕：研究与脚本（免费）

1. **研究**：用 WebSearch 查证问题的科学解释，**至少两个来源互证**。
   给儿童简化可以，简化到错不行；拿不准的细节宁可不讲。
2. **写旁白**：面向 4-8 岁孩子的讲故事语气——先用孩子熟悉的事物引入
   （提问或场景），层层解释，温暖收尾。长度以讲清楚为准，不设上限；
   每个分镜的旁白约 15-35 字（一两句话）。
3. **拆分镜**：每镜 = 旁白词 + `visual_zh`（给 Robert 看的画面中文描述）+
   `visual_prompt_en`（给视频模型的英文 prompt）。prompt 末尾统一追加：
   `bright, warm colors, child-friendly, gentle, soft lighting`，
   规避黑暗、恐怖、灾难类意象。画面要具体（镜头运动、场景、主体）。

## 确认关卡（硬性，不可跳过）

向 Robert 展示：**旁白全文 + 分镜表（每镜旁白/画面描述）+ 预计时长 +
预计成本（分镜数 × 约 ¥1/段）**，等待修改或确认。
Robert 可改旁白、改画面、增删分镜。**未得到明确确认前，禁止任何生成调用。**

## 第二幕：生成与合成（花钱）

确认后：

1. 创建项目目录 `output/why-videos/<YYYYMMDD>-<slug>/`（slug 用
   `pipeline.make_slug` 的规则：中文/字母/数字，其余转 `-`）。
2. 写入 `script.md`（确认版旁白全文 + 分镜表）和 `storyboard.json`
   （schema 见 pipeline.py 模块 docstring；所有 scene `status: "pending"`、
   `audio_file: "clips/scene-N.mp3"`、`clip_file: "clips/scene-N.mp4"`）。
3. 运行生成（断点续跑：中断后重跑同一命令，已完成分镜自动跳过）：
   ```
   backend/.venv/bin/python .claude/skills/why-video/pipeline.py generate output/why-videos/<目录> --yes
   ```
   （交互确认已在确认关卡完成，故带 `--yes`；脚本失败自动重试 1 次，
   仍失败标记 failed 并继续其余分镜。）
4. 有 failed 分镜时：把失败原因报告 Robert，按指示 `--redo <id>` 重试。
5. 合成：
   ```
   backend/.venv/bin/python .claude/skills/why-video/pipeline.py assemble output/why-videos/<目录>
   ```

## 交付

报告 Robert：`final.mp4` 路径、总时长、实际消耗（生成几段、几次失败重试）。

## 返工

Robert 说"重做第 N 段"（可附新要求）时：
1. 按要求更新 `storyboard.json` 里该分镜的 `visual_prompt_en` / `narration`
   （同步更新 `script.md`）；
2. `generate <目录> --redo N --yes` → `assemble <目录>`；
3. 只有被点名的分镜会重新生成，其余复用缓存。

## 注意

- 全程对 Robert 用中文。
- API key 自动从 `backend/.env.local` 读取（env `SILICONFLOW_API_KEY` 可覆盖），
  不要打印。
- 费用提醒：每段视频是真实花费；除确认关卡外不要擅自追加生成。
