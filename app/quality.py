from .schema import validate_screenplay_script


def text_length(text: str = "") -> int:
    return len("".join(str(text).split()))


def make_check(check_id: str, label: str, passed: bool, severity: str, message: str) -> dict:
    return {
        "id": check_id,
        "label": label,
        "passed": passed,
        "severity": severity,
        "message": message,
    }


def validate_screenplay_structure(script: dict) -> list[dict]:
    source = script.get("source") or {}
    acts = script.get("acts") or []
    scenes = [scene for act in acts for scene in act.get("scenes", [])]
    production_notes = script.get("production_notes") or {}
    source_coverage = production_notes.get("source_coverage") or []
    revision_tasks = production_notes.get("revision_tasks") or []
    schema_errors = validate_screenplay_script(script)

    checks = [
        make_check(
            "schema_contract",
            "Schema 合规",
            not schema_errors,
            "error",
            "输出必须符合 docs/yaml-schema.md 中定义的 YAML Schema。"
            if not schema_errors
            else "；".join(error["message"] for error in schema_errors[:4]),
        ),
        make_check(
            "schema_version",
            "Schema 版本",
            bool(script.get("schema_version")),
            "error",
            "输出应包含 schema_version，方便后续升级和校验。",
        ),
        make_check(
            "minimum_chapters",
            "章节数量",
            int(source.get("chapter_count") or 0) >= 3,
            "error",
            "题目要求输入 3 个章节以上的小说文本。",
        ),
        make_check(
            "characters",
            "角色列表",
            bool(script.get("characters")),
            "warning",
            "建议提供或识别至少 1 个主要角色。",
        ),
        make_check("acts", "幕结构", bool(acts), "error", "输出应包含 acts，作为剧本的章节/幕骨架。"),
        make_check("scenes", "场景结构", bool(scenes), "error", "输出应包含 scenes，作为剧本的核心编辑单位。"),
        make_check(
            "beats",
            "场景节拍",
            any(scene.get("beats") for scene in scenes),
            "error",
            "每个场景应尽量拆出动作、对白或旁白节拍。",
        ),
        make_check(
            "traceability",
            "来源追溯",
            all(scene.get("source_chapter") for scene in scenes),
            "warning",
            "每个场景应保留 source_chapter，便于回到原小说核对。",
        ),
        make_check(
            "runtime_plan",
            "篇幅规划",
            bool(production_notes.get("estimated_runtime_minutes")) and bool(production_notes.get("runtime_plan")),
            "info",
            "应提供总时长、场均时长和节奏建议，方便作者判断初稿篇幅。",
        ),
        make_check(
            "source_coverage",
            "章节覆盖",
            bool(source_coverage) and all(item.get("covered") for item in source_coverage),
            "warning",
            "每个来源章节都应至少生成一个带节拍的可编辑场景。",
        ),
        make_check(
            "revision_tasks",
            "修订任务",
            bool(revision_tasks),
            "info",
            "应生成结构化修订任务，帮助作者继续打磨初稿。",
        ),
    ]
    return checks


def build_quality_report(chapters: list[dict], script: dict, raw_text: str) -> dict:
    acts = script.get("acts") or []
    scenes = [scene for act in acts for scene in act.get("scenes", [])]
    beats = [beat for scene in scenes for beat in scene.get("beats", [])]
    dialogue_beats = [beat for beat in beats if beat.get("type") == "dialogue"]
    chapter_lengths = [text_length(chapter.get("text", "")) for chapter in chapters]
    total_length = text_length(raw_text)
    production_notes = script.get("production_notes") or {}
    runtime_plan = production_notes.get("runtime_plan") or {}
    source_coverage = production_notes.get("source_coverage") or []
    revision_tasks = production_notes.get("revision_tasks") or []
    checks = validate_screenplay_structure(script)

    checks.append(
        make_check(
            "input_volume",
            "输入体量",
            total_length >= 300,
            "warning",
            "输入文本较短时，生成结果更像提纲；真实测试建议使用完整章节。",
        )
    )
    checks.append(
        make_check(
            "dialogue_balance",
            "对白覆盖",
            bool(dialogue_beats),
            "info",
            "未识别到对白时，工具会先生成动作/旁白节拍，后续可人工补对白。",
        )
    )
    checks.append(
        make_check(
            "scene_density",
            "场景密度",
            len(scenes) >= len(chapters),
            "info",
            "通常每章至少应生成 1 个场景；长章节可使用“细分”密度。",
        )
    )

    failed_critical = len([check for check in checks if not check["passed"] and check["severity"] == "error"])
    failed_warning = len([check for check in checks if not check["passed"] and check["severity"] == "warning"])
    failed_info = len([check for check in checks if not check["passed"] and check["severity"] == "info"])
    score = max(0, 100 - failed_critical * 28 - failed_warning * 12 - failed_info * 6)

    suggestions = []
    if script.get("source", {}).get("chapter_count", 0) < 3:
        suggestions.append("补充到至少 3 个章节后再提交比赛测试。")
    if not script.get("characters"):
        suggestions.append("在主要角色输入框填写主角和关键配角，提高对白归属准确率。")
    if total_length < 300:
        suggestions.append("使用更完整的章节文本，避免只输入梗概。")
    if not dialogue_beats:
        suggestions.append("原文对白较少时，可在生成后人工添加角色对白。")
    if len(scenes) < len(chapters):
        suggestions.append("把输出密度切换为“细分”，让长章节拆出更多场景。")
    if runtime_plan.get("pacing"):
        suggestions.append(str(runtime_plan["pacing"]))
    uncovered_chapters = [item.get("chapter", "") for item in source_coverage if not item.get("covered")]
    if uncovered_chapters:
        suggestions.append(f"检查未充分转换的章节：{'、'.join(uncovered_chapters[:5])}。")

    average_chapter_chars = round(sum(chapter_lengths) / len(chapter_lengths)) if chapter_lengths else 0
    coverage_rate = round(
        len([item for item in source_coverage if item.get("covered")]) / len(source_coverage) * 100
    ) if source_coverage else 0
    high_priority_tasks = len([item for item in revision_tasks if item.get("priority") == "high"])
    return {
        "score": score,
        "status": "needs_fix" if failed_critical else "review" if failed_warning else "ready",
        "metrics": {
            "input_chars": total_length,
            "chapter_count": len(chapters),
            "average_chapter_chars": average_chapter_chars,
            "scene_count": len(scenes),
            "beat_count": len(beats),
            "dialogue_beat_count": len(dialogue_beats),
            "estimated_runtime_minutes": production_notes.get("estimated_runtime_minutes", 0),
            "average_scene_minutes": runtime_plan.get("average_scene_minutes", 0),
            "source_coverage_rate": coverage_rate,
            "revision_task_count": len(revision_tasks),
            "high_priority_revision_tasks": high_priority_tasks,
        },
        "checks": checks,
        "suggestions": suggestions,
    }
