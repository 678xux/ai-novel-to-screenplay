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
    ]
    return checks


def build_quality_report(chapters: list[dict], script: dict, raw_text: str) -> dict:
    acts = script.get("acts") or []
    scenes = [scene for act in acts for scene in act.get("scenes", [])]
    beats = [beat for scene in scenes for beat in scene.get("beats", [])]
    dialogue_beats = [beat for beat in beats if beat.get("type") == "dialogue"]
    chapter_lengths = [text_length(chapter.get("text", "")) for chapter in chapters]
    total_length = text_length(raw_text)
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

    average_chapter_chars = round(sum(chapter_lengths) / len(chapter_lengths)) if chapter_lengths else 0
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
        },
        "checks": checks,
        "suggestions": suggestions,
    }
