"""why-video 流水线：科普短视频的验证 / 生成 / 合成。

storyboard.json schema（机器状态唯一来源，存于每个项目目录）：
{
  "question": "地球为什么是圆的",
  "slug": "地球为什么是圆的",
  "created": "YYYY-MM-DD",
  "voice": "TTS 音色",
  "video_model": "视频模型 id",
  "scenes": [{
    "id": 1,
    "narration": "一句或两句旁白词",
    "visual_zh": "画面中文描述（给 Robert 看）",
    "visual_prompt_en": "english prompt for the video model",
    "status": "pending|audio_done|done|failed",
    "audio_file": "clips/scene-1.mp3",
    "clip_file": "clips/scene-1.mp4",
    "audio_duration": 0.0,
    "error": ""
  }]
}
"""

from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import subprocess
import sys
import time
from pathlib import Path

# ---------- 常量（EST/DEFAULT 按 verify 真机结果校准） ----------

BASE_URL = "https://api.siliconflow.cn/v1"
TTS_MODEL = "FunAudioLLM/CosyVoice2-0.5B"
DEFAULT_VOICE = "FunAudioLLM/CosyVoice2-0.5B:anna"
VIDEO_MODEL_DEFAULT = "Wan-AI/Wan2.2-T2V-A14B"
VIDEO_SIZE = "720x1280"  # 9:16 竖屏
EST_PER_CLIP_YUAN = 1.0  # 单段粗估成本，verify 后按所选模型修正


def _tool(name: str) -> str:
    """ffmpeg/ffprobe 可执行路径。

    Homebrew 新版 ffmpeg 是无 libass 的瘦身构建（烧字幕需要 subtitles 滤镜），
    完整构建在 keg-only 的 ffmpeg-full 里，优先用它，退回 PATH。
    """
    full = Path("/opt/homebrew/opt/ffmpeg-full/bin") / name
    return str(full) if full.exists() else name


FFMPEG = _tool("ffmpeg")
FFPROBE = _tool("ffprobe")

# ---------- 纯逻辑层 ----------

# 中文/英文标点与空白：字幕断行与 slug 的分隔依据
_PUNCT_SPLIT = re.compile(r"[，。！？；：、…,.!?;:\s]+")
# 不可拆单元：数字(含小数)带至多两个单位字符 / 英文单词 / 单个字符
_TOKEN = re.compile(r"\d+(?:\.\d+)?[^\s\d，。！？；：、…,.!?;:]{0,2}|[A-Za-z]+|.")
_SLUG_KEEP = re.compile(r"[一-鿿A-Za-z0-9]+")


def make_slug(question: str, max_len: int = 24) -> str:
    """问题 → 安全目录名：保留中文/字母/数字，其余折叠为 -，截断。"""
    parts = _SLUG_KEEP.findall(question)
    slug = "-".join(parts)[:max_len].rstrip("-")
    return slug


def load_api_key(repo_root: Path | None = None) -> str:
    """env SILICONFLOW_API_KEY 优先，否则读 backend/.env.local 的 LLM_API_KEY。"""
    key = os.environ.get("SILICONFLOW_API_KEY", "").strip()
    if key:
        return key
    root = repo_root or Path(__file__).resolve().parents[3]
    env_file = root / "backend" / ".env.local"
    if env_file.is_file():
        for line in env_file.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if line.startswith("LLM_API_KEY=") and line.split("=", 1)[1].strip():
                return line.split("=", 1)[1].strip()
    raise RuntimeError("未找到 SiliconFlow API key（env SILICONFLOW_API_KEY 或 backend/.env.local 的 LLM_API_KEY）")


def scenes_todo(data: dict, redo_ids: list[int] | None = None) -> list[dict]:
    """待生成分镜。redo_ids 给出时仅重置并返回这些 id；否则返回未 done 的。"""
    scenes = data["scenes"]
    if redo_ids:
        picked = [s for s in scenes if s["id"] in redo_ids]
        for s in picked:
            s["status"] = "pending"
            s["error"] = ""
        return picked
    return [s for s in scenes if s["status"] != "done"]


def split_lines(text: str, max_chars: int = 14) -> list[str]:
    """旁白 → 字幕行：标点优先断行，超长按不可拆单元硬切，无空行。"""
    lines: list[str] = []
    for seg in _PUNCT_SPLIT.split(text):
        if not seg:
            continue
        if len(seg) <= max_chars:
            lines.append(seg)
            continue
        current = ""
        for token in _TOKEN.findall(seg):
            if current and len(current) + len(token) > max_chars:
                lines.append(current)
                current = token
            else:
                current += token
        if current:
            lines.append(current)
    return lines


def _srt_timestamp(seconds: float) -> str:
    ms = round(seconds * 1000)
    h, rem = divmod(ms, 3_600_000)
    m, rem = divmod(rem, 60_000)
    s, ms = divmod(rem, 1000)
    return f"{h:02d}:{m:02d}:{s:02d},{ms:03d}"


def build_srt(scenes: list[dict]) -> str:
    """全部分镜 → SRT 文本。分镜起始时间累计，镜内各行按字符数占比分配时长。"""
    entries: list[str] = []
    cursor = 0.0
    index = 1
    for scene in scenes:
        duration = float(scene["audio_duration"])
        lines = split_lines(scene["narration"])
        total_chars = sum(len(line) for line in lines) or 1
        start = cursor
        for line in lines:
            end = start + duration * len(line) / total_chars
            entries.append(f"{index}\n{_srt_timestamp(start)} --> {_srt_timestamp(end)}\n{line}\n")
            start = end
            index += 1
        cursor += duration
    return "\n".join(entries)


def save_board(path: Path, data: dict) -> None:
    """原子写 storyboard.json：临时文件 + rename，中断不损坏状态。"""
    tmp = path.with_suffix(".json.tmp")
    tmp.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    os.replace(tmp, path)


def load_board(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


# ---------- SiliconFlow API ----------


class VideoGenError(RuntimeError):
    """视频生成失败 / 超时。"""


def _request(method: str, path: str, api_key: str, json_body: dict | None = None) -> dict:
    """全部 JSON HTTP 收敛于此（便于测试 mock）。"""
    import httpx

    headers = {"Authorization": f"Bearer {api_key}"}
    try:
        with httpx.Client(base_url=BASE_URL, timeout=60) as client:
            resp = client.request(method, path, headers=headers, json=json_body)
    except httpx.HTTPError as e:  # 网络异常收口，让调用方能标 failed 继续
        raise RuntimeError(f"SiliconFlow 请求失败（{path}）: {e}") from e
    if resp.status_code >= 400:
        raise RuntimeError(f"SiliconFlow HTTP {resp.status_code}: {resp.text[:300]}")
    return resp.json()


def list_models(api_key: str, sub_type: str) -> list[str]:
    data = _request("GET", f"/models?sub_type={sub_type}", api_key)
    return [m.get("id", "") for m in data.get("data") or [] if m.get("id")]


def audio_duration(path: Path) -> float:
    out = subprocess.run(
        [FFPROBE, "-v", "error", "-show_entries", "format=duration",
         "-of", "csv=p=0", str(path)],
        check=True, capture_output=True, text=True,
    ).stdout.strip()
    return float(out)


def tts_to_file(api_key: str, text: str, voice: str, out_path: Path, model: str = TTS_MODEL) -> float:
    """TTS 落盘 mp3，返回 ffprobe 实测时长（秒）——视频片段长度以此为锚。"""
    import httpx

    try:
        with httpx.Client(base_url=BASE_URL, timeout=120) as client:
            resp = client.post(
                "/audio/speech",
                headers={"Authorization": f"Bearer {api_key}"},
                json={"model": model, "input": text, "voice": voice, "response_format": "mp3"},
            )
    except httpx.HTTPError as e:
        raise RuntimeError(f"TTS 请求失败: {e}") from e
    if resp.status_code >= 400:
        raise RuntimeError(f"TTS 失败 HTTP {resp.status_code}: {resp.text[:300]}")
    out_path.write_bytes(resp.content)
    return audio_duration(out_path)


def submit_video(api_key: str, prompt: str, model: str, image_size: str) -> str:
    data = _request("POST", "/video/submit", api_key,
                    {"model": model, "prompt": prompt, "image_size": image_size})
    request_id = data.get("requestId") or data.get("request_id")
    if not request_id:
        raise VideoGenError(f"提交视频任务未返回 requestId: {data}")
    return request_id


def poll_video(api_key: str, request_id: str, timeout_s: int = 900, interval_s: int = 10) -> str:
    """轮询直到 Succeed 返回视频 url；Failed / 超时抛 VideoGenError。"""
    deadline = time.monotonic() + timeout_s
    while True:
        data = _request("POST", "/video/status", api_key, {"requestId": request_id})
        status = data.get("status", "")
        if status == "Succeed":
            videos = (data.get("results") or {}).get("videos") or []
            if not videos or not videos[0].get("url"):
                raise VideoGenError(f"生成结果缺少视频 url: {data}")
            return videos[0]["url"]
        if status in ("Failed", "Fail"):
            raise VideoGenError(f"视频生成失败: {data.get('reason', data)}")
        if time.monotonic() >= deadline:
            raise VideoGenError(f"视频生成超时（>{timeout_s}s），requestId={request_id}")
        time.sleep(interval_s)


def download(url: str, out_path: Path) -> None:
    import httpx

    try:
        with httpx.Client(timeout=300, follow_redirects=True) as client:
            resp = client.get(url)
            resp.raise_for_status()
    except httpx.HTTPError as e:
        raise RuntimeError(f"下载视频失败: {e}") from e
    out_path.write_bytes(resp.content)


# ---------- ffmpeg 合成 ----------


def _ffmpeg(args: list[str]) -> None:
    cmd = [FFMPEG, "-y", "-loglevel", "error", *args]
    print("$", " ".join(cmd))
    subprocess.run(cmd, check=True)


def align_scene(clip: Path, audio: Path, audio_duration_s: float, out: Path) -> None:
    """单分镜归一：任意分辨率 → 1080x1920；视频短于旁白则末帧定格，长则截断。"""
    vf = (
        "scale=1080:1920:force_original_aspect_ratio=decrease,"
        "pad=1080:1920:(ow-iw)/2:(oh-ih)/2:color=black,"
        f"tpad=stop_mode=clone:stop_duration={audio_duration_s + 1:.2f},"
        "fps=30,format=yuv420p"
    )
    _ffmpeg([
        "-i", str(clip), "-i", str(audio),
        "-vf", vf, "-t", f"{audio_duration_s:.3f}",
        "-map", "0:v:0", "-map", "1:a:0",
        "-c:v", "libx264", "-preset", "veryfast",
        "-c:a", "aac", "-ar", "44100", "-ac", "2",
        str(out),
    ])


def concat_scenes(segments: list[Path], out: Path) -> None:
    lst = out.parent / "concat.txt"
    lst.write_text("".join(f"file '{p.resolve()}'\n" for p in segments), encoding="utf-8")
    _ffmpeg(["-f", "concat", "-safe", "0", "-i", str(lst), "-c", "copy", str(out)])


def burn_subtitles(video: Path, srt: Path, out: Path) -> None:
    # MarginV 以 libass 默认 PlayResY=288 计：288/5 ≈ 58 → 字幕位于底部约 1/5 处
    style = "FontSize=15,Bold=1,PrimaryColour=&HFFFFFF&,OutlineColour=&H000000&,Outline=2,MarginV=58"
    # subtitles 滤镜的路径转义麻烦：切到 srt 所在目录、用相对文件名
    cmd = [FFMPEG, "-y", "-loglevel", "error",
           "-i", str(video.resolve()),
           "-vf", f"subtitles={srt.name}:force_style='{style}'",
           "-c:a", "copy", str(out.resolve())]
    print("$", " ".join(cmd))
    subprocess.run(cmd, check=True, cwd=srt.parent)


# ---------- 子命令 ----------


def cmd_verify(full: bool = False) -> int:
    ok = True
    try:
        api_key = load_api_key()
        print("✅ API key 已找到")
    except RuntimeError as e:
        print(f"❌ {e}")
        return 1

    missing = [n for n, p in (("ffmpeg", FFMPEG), ("ffprobe", FFPROBE)) if shutil.which(p) is None]
    if not missing:
        filters = subprocess.run([FFMPEG, "-hide_banner", "-filters"],
                                 capture_output=True, text=True).stdout
        if " subtitles " not in filters:
            missing.append("ffmpeg 的 subtitles 滤镜（libass）")
    if missing:
        print(f"❌ 缺少: {', '.join(missing)} —— 安装: brew install ffmpeg-full"
              "（瘦身版 ffmpeg 无 libass，烧字幕必须完整版）")
        ok = False
    else:
        print("✅ ffmpeg / ffprobe / subtitles 滤镜可用")

    try:
        video_models = list_models(api_key, "text-to-video")
        if video_models:
            print(f"✅ 可用视频模型 ({len(video_models)}): {', '.join(video_models)}")
        else:
            print("❌ 账号下没有可用的文生视频模型")
            ok = False
    except Exception as e:
        print(f"❌ 获取视频模型清单失败: {e}")
        ok = False

    try:
        tts_models = list_models(api_key, "text-to-speech")
        print(f"{'✅' if tts_models else '❌'} 可用 TTS 模型 ({len(tts_models)}): {', '.join(tts_models)}")
        ok = ok and bool(tts_models)
    except Exception as e:
        print(f"❌ 获取 TTS 模型清单失败: {e}")
        ok = False

    if full and ok:
        print("⚠️  --full 会产生真实费用（一句试音 + 一段测试视频）")
        tmp = Path("output/why-videos/_verify")
        tmp.mkdir(parents=True, exist_ok=True)
        dur = tts_to_file(api_key, "你好呀，小朋友！", DEFAULT_VOICE, tmp / "tts.mp3")
        print(f"✅ TTS 试音成功，时长 {dur:.1f}s → {tmp / 'tts.mp3'}")
        req = submit_video(api_key, "a cute cartoon sun rising over green hills, bright, warm, child-friendly",
                           VIDEO_MODEL_DEFAULT, VIDEO_SIZE)
        print(f"视频任务已提交（{VIDEO_MODEL_DEFAULT}, {VIDEO_SIZE}），轮询中 ...")
        url = poll_video(api_key, req)
        download(url, tmp / "clip.mp4")
        print(f"✅ 测试视频生成成功 → {tmp / 'clip.mp4'}")

    print("验证通过 ✅" if ok else "验证未通过 ❌（见上）")
    return 0 if ok else 1


def cmd_generate(project_dir: Path, redo_ids: list[int] | None = None, assume_yes: bool = False) -> int:
    project_dir = Path(project_dir)
    board_path = project_dir / "storyboard.json"
    data = load_board(board_path)
    todo = scenes_todo(data, redo_ids)
    if not todo:
        print("没有待生成的分镜。")
        return 0

    est = len(todo) * EST_PER_CLIP_YUAN
    print(f"待生成 {len(todo)} 段 × 约 ¥{EST_PER_CLIP_YUAN:.1f}/段 ≈ ¥{est:.1f}（真实花费，以账单为准）")
    if not assume_yes and input("确认开始生成？(y/N) ").strip().lower() != "y":
        print("已取消。")
        return 0
    if redo_ids:
        save_board(board_path, data)  # --redo 的状态重置，确认通过后才落盘

    api_key = load_api_key()
    voice = data.get("voice") or DEFAULT_VOICE
    model = data.get("video_model") or VIDEO_MODEL_DEFAULT
    (project_dir / "clips").mkdir(exist_ok=True)

    for scene in todo:
        sid = scene["id"]
        try:
            # TTS 需求看产物不看状态：failed 可能失败在 TTS 阶段，跳过会烧出废片
            audio_path = project_dir / scene["audio_file"]
            if not audio_path.is_file() or not scene["audio_duration"]:
                print(f"[分镜 {sid}] 旁白 TTS ...")
                scene["audio_duration"] = tts_to_file(
                    api_key, scene["narration"], voice, project_dir / scene["audio_file"])
                scene["status"] = "audio_done"
                scene["error"] = ""
                save_board(board_path, data)
            print(f"[分镜 {sid}] 视频生成 ...")
            last_err: VideoGenError | None = None
            for attempt in range(2):  # 失败自动重试 1 次
                try:
                    req = submit_video(api_key, scene["visual_prompt_en"], model, VIDEO_SIZE)
                    url = poll_video(api_key, req)
                    download(url, project_dir / scene["clip_file"])
                    last_err = None
                    break
                except VideoGenError as e:
                    last_err = e
                    if attempt == 0:
                        print(f"[分镜 {sid}] 失败：{e} —— 自动重试一次")
            if last_err is not None:
                raise last_err
            scene["status"] = "done"
            save_board(board_path, data)
            print(f"[分镜 {sid}] 完成（旁白 {scene['audio_duration']:.1f}s）")
        except (VideoGenError, RuntimeError) as e:
            scene["status"] = "failed"
            scene["error"] = str(e)
            save_board(board_path, data)
            print(f"[分镜 {sid}] 标记为 failed：{e}")

    done = sum(1 for s in data["scenes"] if s["status"] == "done")
    failed = [s["id"] for s in data["scenes"] if s["status"] == "failed"]
    print(f"完成 {done}/{len(data['scenes'])} 段"
          + (f"，失败分镜 {failed}（修改后可用 --redo {','.join(map(str, failed))} 重试）" if failed else ""))
    return 1 if failed else 0


def cmd_assemble(project_dir: Path) -> int:
    project_dir = Path(project_dir)
    data = load_board(project_dir / "storyboard.json")
    not_done = [s["id"] for s in data["scenes"] if s["status"] != "done"]
    if not_done:
        print(f"还有未完成的分镜: {not_done}，请先运行 generate。")
        return 1

    srt_path = project_dir / "subs.srt"
    srt_path.write_text(build_srt(data["scenes"]), encoding="utf-8")

    segments: list[Path] = []
    for scene in data["scenes"]:
        seg = project_dir / "clips" / f"seg-{scene['id']}.mp4"
        align_scene(project_dir / scene["clip_file"], project_dir / scene["audio_file"],
                    float(scene["audio_duration"]), seg)
        segments.append(seg)

    merged = project_dir / "merged.mp4"
    concat_scenes(segments, merged)
    final = project_dir / "final.mp4"
    burn_subtitles(merged, srt_path, final)

    total = sum(float(s["audio_duration"]) for s in data["scenes"])
    print(f"成片完成: {final}（{len(segments)} 个分镜，总时长约 {total:.1f}s）")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="why-video 流水线")
    sub = parser.add_subparsers(dest="command", required=True)

    p_verify = sub.add_parser("verify", help="能力验证（默认只做免费检查）")
    p_verify.add_argument("--full", action="store_true", help="附带试音 + 测试视频（花钱）")

    p_gen = sub.add_parser("generate", help="第二幕：TTS + 视频生成（断点续跑）")
    p_gen.add_argument("project_dir", type=Path)
    p_gen.add_argument("--redo", default="", help="仅重做这些分镜 id，如 1,3")
    p_gen.add_argument("--yes", action="store_true", help="跳过交互确认")

    p_asm = sub.add_parser("assemble", help="合成 final.mp4")
    p_asm.add_argument("project_dir", type=Path)

    args = parser.parse_args()
    if args.command == "verify":
        return cmd_verify(full=args.full)
    if args.command == "generate":
        redo = [int(x) for x in args.redo.split(",") if x.strip()] or None
        return cmd_generate(args.project_dir, redo_ids=redo, assume_yes=args.yes)
    return cmd_assemble(args.project_dir)


if __name__ == "__main__":
    sys.exit(main())
