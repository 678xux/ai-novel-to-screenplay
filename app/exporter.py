from __future__ import annotations

import json
import re
from typing import Any

from .converter import to_yaml

EXPORT_FORMATS = {
    "yaml": {
        "extension": "screenplay.yaml",
        "mime_type": "text/yaml;charset=utf-8",
    },
    "json": {
        "extension": "screenplay.json",
        "mime_type": "application/json;charset=utf-8",
    },
    "outline_md": {
        "extension": "outline.md",
        "mime_type": "text/markdown;charset=utf-8",
    },
}


def sanitize_filename(value: str = "") -> str:
    clean = re.sub(r'[\\/:*?"<>|\s]+', "_", str(value or "").strip())
    clean = clean.strip("._")
    return clean[:80] or "screenplay"


def _list_line(value: str, indent: int = 0) -> str:
    return f"{' ' * indent}- {value}"


def beat_type_label(value: str = "") -> str:
    labels = {
        "action": "动作",
        "dialogue": "对白",
        "narration": "旁白",
        "transition": "转场",
    }
    return labels.get(value, value or "节拍")


def render_markdown_outline(script: dict[str, Any]) -> str:
    title = script.get("title") or "未命名剧本"
    lines = [f"# {title}", ""]

    if script.get("logline"):
        lines.extend(["## 故事梗概", str(script["logline"]), ""])

    themes = script.get("themes") or []
    if themes:
        lines.append("## 主题")
        lines.extend(_list_line(str(theme)) for theme in themes)
        lines.append("")

    characters = script.get("characters") or []
    if characters:
        lines.append("## 角色")
        for character in characters:
            role = character.get("role") or "角色"
            first = character.get("first_appearance") or "待确认"
            lines.append(_list_line(f"{character.get('name', '未命名角色')}：{role}，首次出现：{first}"))
        lines.append("")

    for act in script.get("acts") or []:
        lines.extend([f"## {act.get('title') or act.get('id') or '未命名幕'}", ""])
        if act.get("purpose"):
            lines.extend([f"**结构功能：** {act['purpose']}", ""])
        if act.get("estimated_runtime_minutes"):
            lines.extend([f"**预计时长：** {act['estimated_runtime_minutes']} 分钟", ""])
        for scene in act.get("scenes") or []:
            scene_title = scene.get("title") or scene.get("id") or "未命名场景"
            lines.extend([f"### {scene_title}", ""])
            meta = [
                f"地点：{scene.get('location') or '待定'}",
                f"时间：{scene.get('time') or '待定'}",
                f"情绪：{scene.get('mood') or '待定'}",
                f"来源：{scene.get('source_chapter') or '待定'}",
            ]
            if scene.get("estimated_runtime_minutes"):
                meta.append(f"预计时长：{scene['estimated_runtime_minutes']} 分钟")
            lines.extend([_list_line(item) for item in meta])
            if scene.get("summary"):
                lines.append(_list_line(f"摘要：{scene['summary']}"))
            if scene.get("objective"):
                lines.append(_list_line(f"目标：{scene['objective']}"))
            if scene.get("obstacle"):
                lines.append(_list_line(f"阻碍：{scene['obstacle']}"))
            if scene.get("outcome"):
                lines.append(_list_line(f"结果：{scene['outcome']}"))
            if scene.get("conflict"):
                lines.append(_list_line(f"冲突：{scene['conflict']}"))
            if scene.get("turning_point"):
                lines.append(_list_line(f"转折：{scene['turning_point']}"))
            if scene.get("props"):
                lines.append(_list_line(f"道具/线索：{'、'.join(str(prop) for prop in scene['props'])}"))
            beats = scene.get("beats") or []
            if beats:
                lines.append(_list_line("节拍："))
                for beat in beats[:12]:
                    beat_type = beat_type_label(beat.get("type"))
                    speaker = f"{beat.get('speaker')}：" if beat.get("speaker") else ""
                    lines.append(_list_line(f"[{beat_type}] {speaker}{beat.get('text', '')}", 2))
            lines.append("")

    production_notes = script.get("production_notes") or {}
    source_coverage = production_notes.get("source_coverage") or []
    if source_coverage:
        lines.append("## 来源覆盖")
        for item in source_coverage:
            status = "已覆盖" if item.get("covered") else "需检查"
            scene_ids = "、".join(str(scene_id) for scene_id in item.get("scene_ids", [])) or "暂无场景"
            detail = (
                f"{item.get('chapter') or '未命名章节'}：{status}，"
                f"{item.get('scene_count', 0)} 场 / {item.get('beat_count', 0)} 节拍，场景：{scene_ids}"
            )
            lines.append(_list_line(detail))
            extras = []
            if item.get("character_names"):
                extras.append(f"角色：{'、'.join(str(name) for name in item['character_names'])}")
            if item.get("props"):
                extras.append(f"道具/线索：{'、'.join(str(prop) for prop in item['props'])}")
            if item.get("coverage_note"):
                extras.append(str(item["coverage_note"]))
            for extra in extras:
                lines.append(_list_line(extra, 2))
        lines.append("")

    runtime_plan = production_notes.get("runtime_plan") or {}
    if production_notes.get("estimated_runtime_minutes") or runtime_plan:
        lines.append("## 篇幅规划")
        if production_notes.get("estimated_runtime_minutes"):
            lines.append(_list_line(f"总预计时长：{production_notes['estimated_runtime_minutes']} 分钟"))
        if runtime_plan.get("average_scene_minutes"):
            lines.append(_list_line(f"平均场景时长：{runtime_plan['average_scene_minutes']} 分钟"))
        if runtime_plan.get("shortest_scene_minutes") or runtime_plan.get("longest_scene_minutes"):
            lines.append(_list_line(f"场景时长范围：{runtime_plan.get('shortest_scene_minutes', 0)} - {runtime_plan.get('longest_scene_minutes', 0)} 分钟"))
        if runtime_plan.get("pacing"):
            lines.append(_list_line(f"节奏判断：{runtime_plan['pacing']}"))
        for note in runtime_plan.get("notes") or []:
            lines.append(_list_line(str(note)))
        lines.append("")

    notes = production_notes.get("revision_suggestions") or []
    if notes:
        lines.append("## 修改建议")
        lines.extend(_list_line(str(note)) for note in notes)
        lines.append("")

    return "\n".join(lines).strip() + "\n"


def export_screenplay(script: dict[str, Any], export_format: str = "yaml", yaml_text: str = "") -> dict:
    if export_format not in EXPORT_FORMATS:
        raise ValueError("不支持的导出格式。")
    if not isinstance(script, dict) or not script:
        raise ValueError("请先完成转换，再导出剧本。")

    title = sanitize_filename(script.get("title") or "screenplay")
    config = EXPORT_FORMATS[export_format]

    if export_format == "yaml":
        content = yaml_text or to_yaml({"script": script})
    elif export_format == "json":
        content = json.dumps({"script": script}, ensure_ascii=False, indent=2)
    else:
        content = render_markdown_outline(script)

    return {
        "ok": True,
        "format": export_format,
        "filename": f"{title}.{config['extension']}",
        "mime_type": config["mime_type"],
        "content": content,
    }
