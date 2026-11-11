"""对白镜（音视同出）prompt 构建与时长取档纯函数。

prompt 模板经真机 PoC 验证（2026-11-09，kie.ai gemini-omni-video /
OpenRouter seedance-2.0-fast 双渠道双角色对白样片），此处参数化。
"""

from __future__ import annotations

_DEFAULT_VOICE_DESC = "clear friendly"


def _speaker_name(speakers_by_id: dict[int, dict], character_id: int | None) -> str | None:
    if character_id is None:
        return None
    speaker = speakers_by_id.get(character_id)
    return speaker["name"] if speaker else None


def build_dialogue_prompt(
    scene_hint: str, speakers: list[dict], dialogue: list[dict]
) -> str:
    """构建对白镜生成 prompt：风格句 + 逐角色音色句 + 按序台词 + 固定尾缀。

    speakers 元素 {"id", "name", "voice_desc"}；character_id 为 None 或查无
    对应 speaker 的台词，归为旁白（"the narrator says"，不标具体人名）。
    """
    speakers_by_id = {s["id"]: s for s in speakers}

    parts = [f"Warm children's storybook cartoon, {scene_hint}."]
    for speaker in speakers:
        voice = speaker.get("voice_desc") or _DEFAULT_VOICE_DESC
        parts.append(f"{speaker['name']} has a {voice} voice.")

    for i, line in enumerate(dialogue):
        name = _speaker_name(speakers_by_id, line["character_id"])
        speaker_label = name if name else "the narrator"
        lead_in = "" if i == 0 else "Then "
        parts.append(f'{lead_in}{speaker_label} says: "{line["en"]}"')

    parts.append(
        "Their mouths move in sync with their own lines, no background music, "
        "clear speech, gentle static camera."
    )
    return " ".join(parts)


def snap_dialogue_duration(estimate: float, ladder: tuple[int, ...]) -> int:
    """按时长档位就近向上取档；超出最大档位则取最大档位。"""
    for step in sorted(ladder):
        if estimate <= step:
            return step
    return max(ladder)
