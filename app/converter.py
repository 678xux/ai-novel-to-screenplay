from __future__ import annotations

import json
import re
from typing import Any

from .quality import build_quality_report
from .schema import SCRIPT_SCHEMA_VERSION

CHAPTER_PATTERN = re.compile(
    r"(?:^|\n)\s*((?:#{1,6}\s*)?(?:(?:第\s*[零〇一二三四五六七八九十百千万\d]+\s*[章节回幕卷部])|"
    r"(?:[Cc][Hh][Aa][Pp][Tt][Ee][Rr]\s+\d+)|(?:卷\s*[零〇一二三四五六七八九十百千万\d]+)|"
    r"(?:\d{1,4}\s*[.、]\s*(?:章|节|回|幕)?\s*[^\n]{0,40}))[^\n]*)"
)
DIALOGUE_PATTERN = re.compile(r"[“\"]([^”\"]{2,})[”\"]")
SPEAKER_PATTERN = re.compile(r"([\u4e00-\u9fa5A-Za-z0-9_·]{1,8})\s*(?:说|问|喊|叫|道|低声说|笑道|答道|喃喃|怒道|提醒|解释)")
LOCATION_PATTERN = re.compile(r"(客厅|书房|卧室|医院|学校|街道|巷子|办公室|咖啡馆|餐厅|车站|机场|码头|城门|宫殿|战场|森林|山洞|屋内|门外|天台|走廊|庭院|村口|河边|窗前)")
TIME_PATTERN = re.compile(r"(清晨|早晨|上午|中午|午后|下午|傍晚|黄昏|夜晚|深夜|黎明|雨夜|雪夜)")
EMOTION_PATTERN = re.compile(r"(愤怒|惊讶|沉默|犹豫|恐惧|紧张|温柔|冷静|焦急|悲伤|欣喜|坚定|疲惫|慌乱|压抑|释然)")
SCENE_SHIFT_PATTERN = re.compile(r"(来到|走进|进入|离开|转身|推开|穿过|回到|赶到|抵达|门外|窗前|走廊|街道|车站|码头|城门|办公室|医院|学校)")
TURNING_PATTERN = re.compile(r"(突然|终于|此时|与此同时|没想到|下一刻|决定|发现|揭开|出现|消失|响起|冲进|追上|停下)")
CONFLICT_PATTERN = re.compile(r"(冲突|争执|危险|秘密|误会|选择|背叛|阻止|追问|威胁|逃|追|杀|爆炸|尖叫|枪|刀)")
PROP_PATTERN = re.compile(r"(匿名信|信纸|信|钥匙|名单|录音笔|录音|档案|照片|地图|符号|手机|电话|戒指|项链|刀|枪|伞|药瓶|票据|日记|合同|令牌|玉佩)")

NON_NAME_PHRASES = {
    "压低声音",
    "沉默片刻",
    "冷静地",
    "愤怒地",
    "紧张地",
    "低声",
    "沙哑",
    "熟悉",
    "有人",
    "有人低声",
    "两人",
    "三人",
    "门外",
    "黑暗里",
    "录音里",
}


def normalize_text(text: Any = "") -> str:
    return str(text).replace("\r\n", "\n").replace("\r", "\n").replace("\u3000", " ").strip()


def clean_chapter_title(title: str) -> str:
    return re.sub(r"\s+", " ", re.sub(r"^#{1,6}\s*", "", title)).strip()


def split_chapters(text: str) -> list[dict]:
    normalized = normalize_text(text)
    matches = list(CHAPTER_PATTERN.finditer(normalized))
    if not matches:
        return [{"id": "chapter_01", "title": "未识别章节", "text": normalized}]

    chapters = []
    for index, match in enumerate(matches):
        start = match.start(1)
        end = matches[index + 1].start(1) if index + 1 < len(matches) else len(normalized)
        chunk = normalized[start:end].strip()
        lines = chunk.split("\n")
        title_line = lines[0] if lines else f"章节 {index + 1}"
        chapters.append(
            {
                "id": f"chapter_{index + 1:02d}",
                "title": clean_chapter_title(title_line),
                "text": "\n".join(lines[1:]).strip(),
            }
        )
    return chapters


def split_paragraphs(text: str) -> list[str]:
    return [item.strip() for item in re.split(r"\n+", normalize_text(text)) if item.strip()]


def sentence_split(text: str) -> list[str]:
    return [item.strip() for item in re.split(r"(?<=[。！？!?；;])\s*", normalize_text(text)) if item.strip()]


def parse_name_list(value: str = "") -> list[str]:
    return [item.strip() for item in re.split(r"[,，\n、]", normalize_text(value)) if item.strip()]


def is_likely_name(value: str) -> bool:
    clean = value.strip()
    blocked = re.compile(r"(有人|声音|低声|压低|片刻|黑暗|门外|录音|电话|信纸|海风|灯光|雨水|墙上|档案|父亲|熟悉|沙哑)")
    return bool(
        clean
        and len(clean) <= 8
        and clean not in NON_NAME_PHRASES
        and "?" not in clean
        and not clean.isdigit()
        and not blocked.search(clean)
        and clean[-1:] not in {"地", "的"}
    )


def extract_speaker(paragraph: str, known_names: list[str] | None = None) -> str:
    known_names = known_names or []
    before_quote = re.split(r"[“\"]", paragraph)[0] or paragraph
    known_hits = [(name, before_quote.rfind(name)) for name in known_names]
    known_hits = [(name, idx) for name, idx in known_hits if idx >= 0]
    if known_hits:
        return sorted(known_hits, key=lambda item: item[1], reverse=True)[0][0]

    opening = re.match(r"^([\u4e00-\u9fa5A-Za-z0-9_·]{2,6})(?:从|站|望|看|接|喊|问|说|道|答|笑|走|跑|转|拿|发现|解释|提醒|决定|翻|把|没有|迅速|突然)", before_quote)
    if opening and is_likely_name(opening.group(1)):
        return opening.group(1)

    match = SPEAKER_PATTERN.search(before_quote) or SPEAKER_PATTERN.search(paragraph)
    if match and is_likely_name(match.group(1)):
        return match.group(1)
    return ""


def extract_characters(chapters: list[dict], user_characters: str = "") -> list[dict]:
    candidates: dict[str, str] = {}

    def add(name: str, source: str) -> None:
        clean = name.strip()
        if is_likely_name(clean) and clean not in candidates:
            candidates[clean] = source

    known_names = parse_name_list(user_characters)
    for name in known_names:
        add(name, "用户设定")

    if known_names:
        return [
            {
                "id": f"char_{index + 1:02d}",
                "name": name,
                "role": "主角/核心视角" if index == 0 else "角色",
                "traits": [],
                "first_appearance": "用户设定",
                "goal": "待编剧确认",
                "arc": "从原小说行动中提炼人物变化",
                "appearances": [],
            }
            for index, name in enumerate(candidates.keys())
        ]

    for chapter in chapters:
        for paragraph in split_paragraphs(chapter.get("text", "")):
            speaker = extract_speaker(paragraph, known_names)
            if speaker:
                add(speaker, chapter["title"])

    return [
        {
            "id": f"char_{index + 1:02d}",
            "name": name,
            "role": "主角/核心视角" if index == 0 else "角色",
            "traits": [],
            "first_appearance": source,
            "goal": "待编剧确认",
            "arc": "从原小说行动中提炼人物变化",
            "appearances": [],
        }
        for index, (name, source) in enumerate(list(candidates.items())[:12])
    ]


def pick_match(text: str, pattern: re.Pattern, fallback: str) -> str:
    match = pattern.search(text)
    return match.group(1) if match else fallback


def infer_mood(text: str) -> str:
    emotion = pick_match(text, EMOTION_PATTERN, "")
    if emotion:
        return emotion
    if re.search(r"追|逃|爆炸|冲|杀|危险|尖叫|枪|刀", text):
        return "紧张"
    if re.search(r"回忆|想起|沉默|雨|夜|离开", text):
        return "压抑"
    if re.search(r"笑|阳光|拥抱|重逢|庆祝", text):
        return "温暖"
    return "克制"


def summarize(text: str, max_length: int = 92) -> str:
    first = (sentence_split(text) or [normalize_text(text)])[0]
    return first if len(first) <= max_length else f"{first[: max_length - 1]}…"


def extract_props(text: str) -> list[str]:
    props = []
    for match in PROP_PATTERN.finditer(text):
        prop = match.group(1)
        if prop == "信" and any(item in props for item in ("匿名信", "信纸")):
            continue
        if prop == "录音" and "录音笔" in props:
            continue
        if prop not in props:
            props.append(prop)
    return props[:8]


def compact_text_length(text: str = "") -> int:
    return len("".join(str(text).split()))


def infer_scene_objective(scene_text: str, chapter_title: str) -> str:
    first_sentence = summarize(scene_text or chapter_title, 70)
    if re.search(r"寻找|找到|追寻|调查|揭开|知道|确认|保护", scene_text):
        return f"推动人物完成关键行动：{first_sentence}"
    return f"推进“{chapter_title}”中的人物选择与信息揭示"


def infer_scene_obstacle(scene_text: str, conflict: str) -> str:
    if conflict and "需要二次打磨" not in conflict:
        return conflict
    if re.search(r"危险|追|逃|阻止|争执|威胁", scene_text):
        return "外部压力阻碍角色达成目标"
    if re.search(r"秘密|误会|隐瞒|不相信", scene_text):
        return "信息不完整或互不信任造成阻碍"
    return "阻碍需要编剧在二次打磨时明确"


def infer_scene_outcome(scene_text: str, turning_point: str) -> str:
    if turning_point and "待编剧确认" not in turning_point:
        return turning_point
    if re.search(r"决定|离开|出现|发现|揭开|终于", scene_text):
        return summarize((re.search(r"[^。！？!?]*(?:决定|离开|出现|发现|揭开|终于)[^。！？!?]*", scene_text) or [scene_text])[0], 80)
    return "本场结果需要人工确认，并连接下一场行动"


def mode_hint_fields(mode: str, text: str, beat_type: str) -> dict:
    if mode == "short":
        return {"hook": "保留反转/悬念，适合短剧卡点"} if re.search(r"突然|发现|危险|秘密|决定|出现|揭开", text) else {"hook": "压缩信息，推进下一场"}
    if mode == "stage":
        return {"stage_direction": "用灯光、走位和停顿呈现"} if beat_type != "dialogue" else {"stage_direction": "对白后保留表演停顿"}
    return {"camera": "特写" if re.search(r"看见|望向|盯着|发现", text) else "中景"}


def create_beats(paragraphs: list[str], scene_id: str, known_names: list[str] | None = None, mode: str = "drama") -> list[dict]:
    known_names = known_names or []
    beats = []
    for paragraph in paragraphs:
        dialogues = list(DIALOGUE_PATTERN.finditer(paragraph))
        if dialogues:
            speaker = extract_speaker(paragraph, known_names)
            action_text = DIALOGUE_PATTERN.sub("", paragraph).strip()
            if action_text:
                action_summary = summarize(action_text, 120)
                beats.append(
                    {
                        "id": f"{scene_id}_beat_{len(beats) + 1:02d}",
                        "type": "action",
                        "text": action_summary,
                        **mode_hint_fields(mode, action_summary, "action"),
                    }
                )
            for dialogue in dialogues:
                dialogue_text = dialogue.group(1).strip()
                beats.append(
                    {
                        "id": f"{scene_id}_beat_{len(beats) + 1:02d}",
                        "type": "dialogue",
                        "speaker": speaker or "待定角色",
                        "text": dialogue_text,
                        "emotion": pick_match(paragraph, EMOTION_PATTERN, "待细化"),
                        **mode_hint_fields(mode, dialogue_text, "dialogue"),
                    }
                )
            continue

        for sentence in sentence_split(paragraph)[:3]:
            beat_type = "narration" if re.search(r"回忆|心想|想到|意识到", sentence) else "action"
            sentence_summary = summarize(sentence, 120)
            beats.append(
                {
                    "id": f"{scene_id}_beat_{len(beats) + 1:02d}",
                    "type": beat_type,
                    "text": sentence_summary,
                    **mode_hint_fields(mode, sentence_summary, beat_type),
                }
            )
    return beats[:12]


def runtime_weights(mode: str) -> dict[str, float]:
    if mode == "short":
        return {
            "base": 0.35,
            "action": 0.18,
            "dialogue": 0.15,
            "narration": 0.12,
            "transition": 0.08,
            "chars_per_minute": 460,
        }
    if mode == "stage":
        return {
            "base": 1.0,
            "action": 0.45,
            "dialogue": 0.38,
            "narration": 0.3,
            "transition": 0.16,
            "chars_per_minute": 280,
        }
    return {
        "base": 0.75,
        "action": 0.32,
        "dialogue": 0.28,
        "narration": 0.22,
        "transition": 0.12,
        "chars_per_minute": 350,
    }


def runtime_density_multiplier(density: str) -> float:
    if density == "compact":
        return 0.9
    if density == "detailed":
        return 1.05
    return 1.0


def round_runtime(value: float) -> float:
    rounded = round(value, 1)
    return int(rounded) if rounded.is_integer() else rounded


def estimate_scene_runtime_minutes(scene_text: str, beats: list[dict], mode: str = "drama", density: str = "balanced") -> float:
    weights = runtime_weights(mode)
    beat_minutes = sum(weights.get(str(beat.get("type") or "action"), weights["action"]) for beat in beats)
    text_minutes = compact_text_length(scene_text) / weights["chars_per_minute"]
    estimated = (weights["base"] + beat_minutes + min(text_minutes, 2.4)) * runtime_density_multiplier(density)
    return round_runtime(max(0.5, estimated))


def scene_density_limits(density: str) -> tuple[int, int]:
    if density == "detailed":
        return 2, 4
    if density == "compact":
        return 4, 8
    return 3, 6


def boundary_score(previous: str, current: str) -> int:
    score = 0
    previous_location = pick_match(previous, LOCATION_PATTERN, "")
    current_location = pick_match(current, LOCATION_PATTERN, "")
    previous_time = pick_match(previous, TIME_PATTERN, "")
    current_time = pick_match(current, TIME_PATTERN, "")
    if previous_location and current_location and previous_location != current_location:
        score += 2
    if previous_time and current_time and previous_time != current_time:
        score += 2
    if SCENE_SHIFT_PATTERN.search(current):
        score += 1
    if TURNING_PATTERN.search(current):
        score += 1
    if CONFLICT_PATTERN.search(current):
        score += 1
    if DIALOGUE_PATTERN.search(previous) and not DIALOGUE_PATTERN.search(current):
        score += 1
    return score


def split_scene_groups(paragraphs: list[str], density: str) -> list[list[str]]:
    if not paragraphs:
        return [[]]

    min_size, max_size = scene_density_limits(density)
    groups: list[list[str]] = []
    current: list[str] = []
    for paragraph in paragraphs:
        if current:
            should_split = len(current) >= max_size or (len(current) >= min_size and boundary_score(current[-1], paragraph) >= 2)
            if should_split:
                groups.append(current)
                current = []
        current.append(paragraph)
    if current:
        groups.append(current)
    return groups


def mode_scene_note(mode: str) -> str:
    if mode == "short":
        return "短剧模式：每场建议保留一个强钩子或反转点。"
    if mode == "stage":
        return "舞台剧模式：关注舞台调度、灯光和演员走位。"
    return "影视剧模式：关注镜头、场面调度和可视化动作。"


def chapter_to_scenes(chapter: dict, chapter_index: int, density: str, known_names: list[str], mode: str) -> list[dict]:
    paragraphs = split_paragraphs(chapter.get("text", ""))
    scenes = []
    for scene_index, group in enumerate(split_scene_groups(paragraphs, density), start=1):
        scene_text = "\n".join(group)
        scene_id = f"scene_{chapter_index + 1:02d}_{scene_index:02d}"
        conflict = summarize((re.search(r"[^。！？!?]*(?:冲突|争执|危险|秘密|误会|选择|背叛|阻止|追问)[^。！？!?]*", scene_text) or ["本场冲突需要二次打磨。"])[0], 80)
        turning_point = summarize((re.search(r"[^。！？!?]*(?:突然|终于|决定|发现|转身|离开|出现|揭开)[^。！？!?]*", scene_text) or ["转折点待编剧确认。"])[0], 80)
        beats = create_beats(group, scene_id, known_names, mode)
        scenes.append(
            {
                "id": scene_id,
                "title": f"{chapter['title']} · 场景 {scene_index}",
                "source_chapter": chapter["title"],
                "location": pick_match(scene_text, LOCATION_PATTERN, "待定地点"),
                "time": pick_match(scene_text, TIME_PATTERN, "待定时间"),
                "mood": infer_mood(scene_text),
                "summary": summarize(scene_text or chapter["title"]),
                "estimated_runtime_minutes": estimate_scene_runtime_minutes(scene_text, beats, mode, density),
                "objective": infer_scene_objective(scene_text, chapter["title"]),
                "obstacle": infer_scene_obstacle(scene_text, conflict),
                "outcome": infer_scene_outcome(scene_text, turning_point),
                "beats": beats,
                "conflict": conflict,
                "turning_point": turning_point,
                "props": extract_props(scene_text),
                "notes": ["由小说段落与场景边界线索自动拆分，建议人工校准场景边界。", mode_scene_note(mode)],
            }
        )
    return scenes


def build_acts(chapters: list[dict], density: str, known_names: list[str], mode: str) -> list[dict]:
    acts = []
    for index, chapter in enumerate(chapters):
        purpose = "建立人物、世界观与核心矛盾" if index == 0 else "推进高潮并留下后续打磨空间" if index == len(chapters) - 1 else "升级冲突并推动人物选择"
        scenes = chapter_to_scenes(chapter, index, density, known_names, mode)
        acts.append(
            {
                "id": f"act_{index + 1:02d}",
                "title": chapter["title"],
                "source_chapters": [chapter["title"]],
                "purpose": purpose,
                "estimated_runtime_minutes": round_runtime(sum(float(scene.get("estimated_runtime_minutes") or 0) for scene in scenes)),
                "scenes": scenes,
            }
        )
    return acts


def scene_mentions_character(scene: dict, character_name: str) -> bool:
    if not character_name:
        return False
    if character_name in str(scene.get("summary", "")):
        return True
    if character_name in str(scene.get("conflict", "")) or character_name in str(scene.get("turning_point", "")):
        return True
    return any(character_name == beat.get("speaker") or character_name in str(beat.get("text", "")) for beat in scene.get("beats", []))


def enrich_character_arcs(characters: list[dict], acts: list[dict]) -> list[dict]:
    for character in characters:
        appearances = []
        for act in acts:
            for scene in act.get("scenes", []):
                if scene_mentions_character(scene, character.get("name", "")):
                    appearances.append(scene.get("id", ""))

        if appearances:
            character["appearances"] = appearances
            if character.get("first_appearance") == "用户设定":
                for act in acts:
                    matched = next((scene for scene in act.get("scenes", []) if scene.get("id") == appearances[0]), None)
                    if matched:
                        character["first_appearance"] = matched.get("source_chapter", character["first_appearance"])
                        break
        else:
            character["appearances"] = []

        if character.get("role") == "主角/核心视角":
            character["goal"] = "追寻核心真相并推动主要选择"
            character["arc"] = "从被动卷入事件，到主动做出关键选择"
        elif appearances:
            character["goal"] = "影响主角选择或推动冲突升级"
            character["arc"] = "围绕主线冲突呈现立场变化"
        else:
            character["goal"] = "待编剧确认"
            character["arc"] = "待补充人物功能和变化"
    return characters


def mode_revision_suggestions(mode: str) -> list[str]:
    common = [
        "复核角色名与对白归属。",
        "把小说心理描写改写成可表演动作。",
        "为每场补充明确的场景目标、阻碍与转折。",
    ]
    if mode == "short":
        return common + ["检查每场结尾是否有短剧钩子、反转或追看点。"]
    if mode == "stage":
        return common + ["补充舞台空间、灯光变化、演员走位和上下场调度。"]
    return common + ["补充镜头景别、场面调度和可视化动作细节。"]


def runtime_pacing_label(mode: str, average_scene_minutes: float) -> str:
    if mode == "short":
        if average_scene_minutes > 1.6:
            return "短剧节奏偏长，建议压缩铺垫并强化场尾钩子。"
        return "短剧节奏紧凑，适合按强情节点推进。"
    if mode == "stage":
        if average_scene_minutes < 1.6:
            return "舞台段落偏短，建议合并相近场景以保留表演停顿。"
        return "舞台节奏较完整，可继续补充走位和灯光变化。"
    if average_scene_minutes < 1.2:
        return "场景偏碎，适合合并相邻信息场。"
    if average_scene_minutes > 3.5:
        return "场景偏长，建议拆出新的地点、时间或冲突转折。"
    return "场景时长较均衡，适合作为剧本初稿继续打磨。"


def runtime_revision_notes(mode: str, density: str, average_scene_minutes: float) -> list[str]:
    notes = ["根据节拍数量、对白/动作类型和文本体量估算时长，提交前仍需人工朗读校准。"]
    if density == "compact":
        notes.append("紧凑密度会压缩场景数量，适合先得到总览版剧本。")
    elif density == "detailed":
        notes.append("细分密度会生成更多短场景，适合进一步拆分分镜或舞台调度。")
    if mode == "short":
        notes.append("短剧模式建议每 1 分钟左右出现一次明确钩子或反转。")
    elif mode == "stage":
        notes.append("舞台剧模式需额外预留换景、停顿和上下场时间。")
    elif average_scene_minutes > 3.5:
        notes.append("部分影视场景时长较长，可按地点变化或冲突升级继续拆分。")
    return notes


def build_runtime_plan(acts: list[dict], mode: str, density: str) -> dict:
    scene_minutes = [
        float(scene.get("estimated_runtime_minutes") or 0)
        for act in acts
        for scene in act.get("scenes", [])
        if float(scene.get("estimated_runtime_minutes") or 0) > 0
    ]
    if not scene_minutes:
        return {
            "average_scene_minutes": 0,
            "shortest_scene_minutes": 0,
            "longest_scene_minutes": 0,
            "pacing": "尚未形成可估算的场景节奏。",
            "notes": ["补充章节正文后再进行时长估算。"],
        }

    average_scene_minutes = round_runtime(sum(scene_minutes) / len(scene_minutes))
    return {
        "average_scene_minutes": average_scene_minutes,
        "shortest_scene_minutes": round_runtime(min(scene_minutes)),
        "longest_scene_minutes": round_runtime(max(scene_minutes)),
        "pacing": runtime_pacing_label(mode, float(average_scene_minutes)),
        "notes": runtime_revision_notes(mode, density, float(average_scene_minutes)),
    }


def unique_values(values: list[Any], limit: int = 8) -> list[str]:
    items: list[str] = []
    for value in values:
        text = normalize_text(value)
        if text and text not in items:
            items.append(text)
        if len(items) >= limit:
            break
    return items


def build_source_coverage(chapters: list[dict], acts: list[dict], characters: list[dict]) -> list[dict]:
    known_character_names = [character.get("name", "") for character in characters if character.get("name")]
    scenes_by_chapter: dict[str, list[dict]] = {}
    fallback_scenes_by_chapter: dict[str, list[dict]] = {}

    for act in acts:
        source_chapters = unique_values(act.get("source_chapters") or [act.get("title", "")], 20)
        act_scenes = act.get("scenes") or []
        for scene in act_scenes:
            source_chapter = normalize_text(scene.get("source_chapter"))
            if source_chapter:
                scenes_by_chapter.setdefault(source_chapter, []).append(scene)
        for chapter_title in source_chapters:
            fallback_scenes_by_chapter.setdefault(chapter_title, []).extend(act_scenes)

    coverage = []
    for chapter in chapters:
        chapter_title = normalize_text(chapter.get("title")) or "未命名章节"
        chapter_scenes = scenes_by_chapter.get(chapter_title) or fallback_scenes_by_chapter.get(chapter_title) or []
        scene_ids = unique_values([scene.get("id", "") for scene in chapter_scenes], 20)
        props = unique_values([prop for scene in chapter_scenes for prop in scene.get("props", [])], 10)
        character_names = unique_values(
            [
                name
                for scene in chapter_scenes
                for name in known_character_names
                if scene_mentions_character(scene, name)
            ],
            10,
        )
        beat_count = sum(len(scene.get("beats", [])) for scene in chapter_scenes)
        coverage.append(
            {
                "chapter": chapter_title,
                "source_chars": compact_text_length(chapter.get("text", "")),
                "scene_ids": scene_ids,
                "scene_count": len(chapter_scenes),
                "beat_count": beat_count,
                "character_names": character_names,
                "props": props,
                "covered": bool(chapter_scenes and beat_count),
                "coverage_note": "已转换为可编辑场景" if chapter_scenes and beat_count else "未生成可编辑场景，建议检查章节标题或正文长度",
            }
        )
    return coverage


def ensure_runtime_plan(script: dict, mode: str = "drama", density: str = "balanced") -> dict:
    acts = script.get("acts") or []
    for act in acts:
        for scene in act.get("scenes", []) or []:
            runtime = scene.get("estimated_runtime_minutes")
            if not isinstance(runtime, (int, float)) or isinstance(runtime, bool) or runtime <= 0:
                scene_text = "\n".join(str(beat.get("text", "")) for beat in scene.get("beats", []))
                scene["estimated_runtime_minutes"] = estimate_scene_runtime_minutes(scene_text or scene.get("summary", ""), scene.get("beats", []), mode, density)
        act["estimated_runtime_minutes"] = round_runtime(
            sum(float(scene.get("estimated_runtime_minutes") or 0) for scene in act.get("scenes", []) or [])
        )

    production_notes = script.setdefault("production_notes", {})
    total_runtime = round_runtime(sum(float(act.get("estimated_runtime_minutes") or 0) for act in acts))
    production_notes["estimated_runtime_minutes"] = total_runtime
    production_notes["runtime_plan"] = build_runtime_plan(acts, mode, density)
    return script


def yaml_scalar(value: Any) -> str:
    if value is None:
        return "''"
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, (int, float)):
        return str(value)
    text = str(value)
    if not text:
        return "''"
    if re.match(r"^[A-Za-z0-9_\-./: ]+$", text) and not re.match(r"^(true|false|null|yes|no)$", text, re.I):
        return text
    return json.dumps(text, ensure_ascii=False)


def to_yaml(value: Any, indent: int = 0) -> str:
    pad = " " * indent
    if isinstance(value, list):
        if not value:
            return f"{pad}[]"
        lines = []
        for item in value:
            if isinstance(item, dict):
                entries = list(item.items())
                if not entries:
                    lines.append(f"{pad}- {{}}")
                    continue
                first_key, first_value = entries[0]
                first_rendered = "\n" + to_yaml(first_value, indent + 4) if isinstance(first_value, (dict, list)) else yaml_scalar(first_value)
                lines.append(f"{pad}- {first_key}: {first_rendered}")
                for key, child in entries[1:]:
                    rendered = "\n" + to_yaml(child, indent + 4) if isinstance(child, (dict, list)) else yaml_scalar(child)
                    lines.append(f"{pad}  {key}: {rendered}")
            else:
                rendered = "\n" + to_yaml(item, indent + 2) if isinstance(item, (dict, list)) else yaml_scalar(item)
                lines.append(f"{pad}- {rendered}")
        return "\n".join(lines)
    if isinstance(value, dict):
        return "\n".join(
            f"{pad}{key}: {chr(10) + to_yaml(child, indent + 2) if isinstance(child, (dict, list)) else yaml_scalar(child)}"
            for key, child in value.items()
        )
    return f"{pad}{yaml_scalar(value)}"


def validate(script: dict) -> list[str]:
    warnings = []
    if script.get("source", {}).get("chapter_count", 0) < 3:
        warnings.append("输入章节少于 3 个，不满足比赛题目要求。")
    if not script.get("acts"):
        warnings.append("未生成幕/章节结构。")
    if not any(act.get("scenes") for act in script.get("acts", [])):
        warnings.append("未生成场景。")
    if not script.get("characters"):
        warnings.append("未识别到角色，建议在角色输入框中补充主要人物。")
    return warnings


def build_conversion_result(script: dict, chapters: list[dict], raw_text: str, meta: dict | None = None) -> dict:
    source = script.get("source") if isinstance(script.get("source"), dict) else {}
    mode = source.get("adaptation_mode") or (meta or {}).get("mode") or "drama"
    density = (meta or {}).get("density") or "balanced"
    ensure_runtime_plan(script, mode, density)
    script["production_notes"]["source_coverage"] = build_source_coverage(chapters, script.get("acts", []), script.get("characters", []))
    warnings = validate(script)
    script["production_notes"]["adaptation_warnings"] = warnings
    quality = build_quality_report(chapters, script, raw_text)
    return {
        "ok": True,
        "yaml": to_yaml({"script": script}),
        "script": script,
        "quality": quality,
        "warnings": warnings,
        "stats": {
            "chapters": script["source"]["chapter_count"],
            "characters": len(script["characters"]),
            "scenes": sum(len(act.get("scenes", [])) for act in script["acts"]),
            "beats": sum(len(scene.get("beats", [])) for act in script["acts"] for scene in act.get("scenes", [])),
        },
        "meta": meta or {},
    }


def convert_novel_to_screenplay(payload: dict | None = None) -> dict:
    payload = payload or {}
    title = normalize_text(payload.get("title")) or "未命名小说改编"
    text = normalize_text(payload.get("text"))
    density = payload.get("density") or "balanced"
    mode = payload.get("mode") or "drama"
    if not text:
        raise ValueError("请先输入小说文本。")

    chapters = split_chapters(text)
    known_names = parse_name_list(payload.get("characters", ""))
    characters = extract_characters(chapters, payload.get("characters", ""))
    acts = build_acts(chapters, density, known_names, mode)
    characters = enrich_character_arcs(characters, acts)
    themes = parse_name_list(payload.get("themes", "")) or ["人物选择", "冲突升级", "情感转折"]
    script = {
        "schema_version": SCRIPT_SCHEMA_VERSION,
        "title": title,
        "source": {
            "type": "novel",
            "chapter_count": len(chapters),
            "input_language": "zh-CN",
            "adaptation_mode": mode,
        },
        "logline": summarize("\n".join(chapter.get("text", "") for chapter in chapters), 110),
        "themes": themes,
        "characters": characters,
        "acts": acts,
        "production_notes": {
            "estimated_runtime_minutes": 0,
            "runtime_plan": build_runtime_plan(acts, mode, density),
            "source_coverage": [],
            "adaptation_warnings": [],
            "revision_suggestions": mode_revision_suggestions(mode),
        },
    }
    return build_conversion_result(script, chapters, text, {"engine": "rules", "density": density, "mode": mode})
