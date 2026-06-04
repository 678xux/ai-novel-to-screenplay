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


def create_beats(paragraphs: list[str], scene_id: str, known_names: list[str] | None = None) -> list[dict]:
    known_names = known_names or []
    beats = []
    for paragraph in paragraphs:
        dialogues = list(DIALOGUE_PATTERN.finditer(paragraph))
        if dialogues:
            speaker = extract_speaker(paragraph, known_names)
            action_text = DIALOGUE_PATTERN.sub("", paragraph).strip()
            if action_text:
                beats.append(
                    {
                        "id": f"{scene_id}_beat_{len(beats) + 1:02d}",
                        "type": "action",
                        "text": summarize(action_text, 120),
                        "camera": "中景",
                    }
                )
            for dialogue in dialogues:
                beats.append(
                    {
                        "id": f"{scene_id}_beat_{len(beats) + 1:02d}",
                        "type": "dialogue",
                        "speaker": speaker or "待定角色",
                        "text": dialogue.group(1).strip(),
                        "emotion": pick_match(paragraph, EMOTION_PATTERN, "待细化"),
                    }
                )
            continue

        for sentence in sentence_split(paragraph)[:3]:
            beats.append(
                {
                    "id": f"{scene_id}_beat_{len(beats) + 1:02d}",
                    "type": "narration" if re.search(r"回忆|心想|想到|意识到", sentence) else "action",
                    "text": summarize(sentence, 120),
                    "camera": "特写" if re.search(r"看见|望向|盯着|发现", sentence) else "中景",
                }
            )
    return beats[:12]


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


def chapter_to_scenes(chapter: dict, chapter_index: int, density: str, known_names: list[str]) -> list[dict]:
    paragraphs = split_paragraphs(chapter.get("text", ""))
    scenes = []
    for scene_index, group in enumerate(split_scene_groups(paragraphs, density), start=1):
        scene_text = "\n".join(group)
        scene_id = f"scene_{chapter_index + 1:02d}_{scene_index:02d}"
        scenes.append(
            {
                "id": scene_id,
                "title": f"{chapter['title']} · 场景 {scene_index}",
                "source_chapter": chapter["title"],
                "location": pick_match(scene_text, LOCATION_PATTERN, "待定地点"),
                "time": pick_match(scene_text, TIME_PATTERN, "待定时间"),
                "mood": infer_mood(scene_text),
                "summary": summarize(scene_text or chapter["title"]),
                "beats": create_beats(group, scene_id, known_names),
                "conflict": summarize((re.search(r"[^。！？!?]*(?:冲突|争执|危险|秘密|误会|选择|背叛|阻止|追问)[^。！？!?]*", scene_text) or ["本场冲突需要二次打磨。"])[0], 80),
                "turning_point": summarize((re.search(r"[^。！？!?]*(?:突然|终于|决定|发现|转身|离开|出现|揭开)[^。！？!?]*", scene_text) or ["转折点待编剧确认。"])[0], 80),
                "props": extract_props(scene_text),
                "notes": ["由小说段落与场景边界线索自动拆分，建议人工校准场景边界。"],
            }
        )
    return scenes


def build_acts(chapters: list[dict], density: str, known_names: list[str]) -> list[dict]:
    acts = []
    for index, chapter in enumerate(chapters):
        purpose = "建立人物、世界观与核心矛盾" if index == 0 else "推进高潮并留下后续打磨空间" if index == len(chapters) - 1 else "升级冲突并推动人物选择"
        acts.append(
            {
                "id": f"act_{index + 1:02d}",
                "title": chapter["title"],
                "source_chapters": [chapter["title"]],
                "purpose": purpose,
                "scenes": chapter_to_scenes(chapter, index, density, known_names),
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
    if not text:
        raise ValueError("请先输入小说文本。")

    chapters = split_chapters(text)
    known_names = parse_name_list(payload.get("characters", ""))
    characters = extract_characters(chapters, payload.get("characters", ""))
    acts = build_acts(chapters, density, known_names)
    characters = enrich_character_arcs(characters, acts)
    themes = parse_name_list(payload.get("themes", "")) or ["人物选择", "冲突升级", "情感转折"]
    script = {
        "schema_version": SCRIPT_SCHEMA_VERSION,
        "title": title,
        "source": {
            "type": "novel",
            "chapter_count": len(chapters),
            "input_language": "zh-CN",
            "adaptation_mode": payload.get("mode") or "drama",
        },
        "logline": summarize("\n".join(chapter.get("text", "") for chapter in chapters), 110),
        "themes": themes,
        "characters": characters,
        "acts": acts,
        "production_notes": {
            "estimated_runtime_minutes": max(8, round(len(chapters) * (9 if density == "detailed" else 4 if density == "compact" else 6))),
            "adaptation_warnings": [],
            "revision_suggestions": [
                "复核角色名与对白归属。",
                "把小说心理描写改写成可表演动作。",
                "为每场补充明确的场景目标、阻碍与转折。",
            ],
        },
    }
    return build_conversion_result(script, chapters, text, {"engine": "rules"})
