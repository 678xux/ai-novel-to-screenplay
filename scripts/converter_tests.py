from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.analyzer import analyze_novel_input
from app.ai_adapter import convert_novel_to_screenplay_optional_ai, get_public_ai_config
from app.converter import convert_novel_to_screenplay, split_chapters
from app.schema import validate_screenplay_script


CASES = [
    {
        "name": "Chinese chapter markers",
        "text": """第一章 风起
林青说：“走。”

第二章 入城
夜晚，林青到了城门。

第三章 选择
黎明，林青决定留下。""",
        "expected_chapters": 3,
    },
    {
        "name": "English Chapter markers",
        "text": """Chapter 1 The Call
Mina said, "I have to go."

Chapter 2 The Door
At night, the old door opened.

Chapter 3 The List
Mina found the list before dawn.""",
        "expected_chapters": 3,
    },
    {
        "name": "Numbered markdown-like markers",
        "text": """1. 雨夜
阿禾说：“别回头。”

2. 地下室
阿禾发现墙上的地图。

3. 出口
清晨，阿禾推开门。""",
        "expected_chapters": 3,
    },
]


def assert_true(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


for item in CASES:
    chapters = split_chapters(item["text"])
    assert_true(len(chapters) == item["expected_chapters"], item["name"])
    result = convert_novel_to_screenplay(
        {
            "title": item["name"],
            "text": item["text"],
            "characters": "林青，Mina，阿禾",
        }
    )
    assert_true(result["ok"] is True, item["name"])
    assert_true(result["stats"]["chapters"] == item["expected_chapters"], item["name"])
    assert_true(result["stats"]["scenes"] >= item["expected_chapters"], item["name"])
    assert_true("script:" in result["yaml"], item["name"])
    assert_true("acts:" in result["yaml"], item["name"])
    assert_true(result["quality"]["score"] > 0, item["name"])
    assert_true(result["quality"]["metrics"]["chapter_count"] == item["expected_chapters"], item["name"])
    assert_true(validate_screenplay_script(result["script"]) == [], f"{item['name']} schema validation")
    assert_true(
        any(check["id"] == "schema_contract" and check["passed"] for check in result["quality"]["checks"]),
        f"{item['name']} quality schema check",
    )

short_result = convert_novel_to_screenplay({"title": "Short input", "text": "第一章 只有一章\n主角说：“还不够。”"})
assert_true(short_result["stats"]["chapters"] == 1, "short chapter count")
assert_true(any("少于 3" in warning for warning in short_result["warnings"]), "short warning")
assert_true(short_result["quality"]["status"] == "needs_fix", "short quality")

fallback_result = convert_novel_to_screenplay_optional_ai(
    {
        "title": "AI fallback",
        "engine": "ai",
        "text": CASES[0]["text"],
        "characters": "林青",
    },
    env={},
)
assert_true(fallback_result["ok"] is True, "AI fallback ok")
assert_true(fallback_result["meta"]["engine"] == "rules", "AI fallback engine")
assert_true(fallback_result["meta"]["ai"]["requested"] is True, "AI fallback requested")
assert_true(fallback_result["meta"]["ai"]["used"] is False, "AI fallback used")

public_config_without_key = get_public_ai_config({})
assert_true(public_config_without_key["enabled"] is False, "public config disabled")
assert_true(public_config_without_key["model"] == "", "public config empty model")

public_config_with_key = get_public_ai_config(
    {
        "OPENAI_API_KEY": "test-key",
        "OPENAI_MODEL": "test-model",
        "OPENAI_BASE_URL": "https://example.com/v1",
    }
)
assert_true(public_config_with_key["enabled"] is True, "public config enabled")
assert_true(public_config_with_key["model"] == "test-model", "public config model")
assert_true(public_config_with_key["provider"] == "example.com", "public config provider")

sample_text = Path("examples/three-chapter-novel.txt").read_text(encoding="utf-8")
sample_result = convert_novel_to_screenplay(
    {
        "title": "Fixture sample",
        "text": sample_text,
        "characters": "林澈，沈雾，周栩",
        "themes": "信任，真相，成长",
    }
)
assert_true(sample_result["stats"]["characters"] == 3, "fixture sample character count")
assert_true([character["name"] for character in sample_result["script"]["characters"]] == ["林澈", "沈雾", "周栩"], "fixture sample characters")
assert_true(validate_screenplay_script(sample_result["script"]) == [], "fixture sample schema validation")

broken_script = {
    **sample_result["script"],
    "acts": [
        {
            **sample_result["script"]["acts"][0],
            "scenes": [
                {
                    **sample_result["script"]["acts"][0]["scenes"][0],
                    "beats": [
                        {
                            **sample_result["script"]["acts"][0]["scenes"][0]["beats"][0],
                            "type": "inner_monologue",
                        }
                    ],
                }
            ],
        }
    ],
}
schema_errors = validate_screenplay_script(broken_script)
assert_true(bool(schema_errors), "schema catches invalid beat type")
assert_true("script.acts[0].scenes[0].beats[0].type" in schema_errors[0]["path"], "schema error path")

missing_required = {key: value for key, value in sample_result["script"].items() if key != "production_notes"}
missing_errors = validate_screenplay_script(missing_required)
assert_true(any(error["path"] == "script.production_notes" for error in missing_errors), "schema catches missing production notes")

sample_analysis = analyze_novel_input({"text": sample_text, "characters": "林澈，沈雾，周栩"})
assert_true(sample_analysis["summary"]["chapter_count"] == 3, "analysis chapter count")
assert_true(sample_analysis["summary"]["dialogues"] >= 3, "analysis dialogue count")
assert_true(sample_analysis["status"] == "ready", "analysis ready")

short_analysis = analyze_novel_input({"text": "第一章 起点\n主角说：“开始。”"})
assert_true(short_analysis["status"] == "needs_fix", "short analysis status")
assert_true(any("少于 3" in warning for warning in short_analysis["warnings"]), "short analysis warning")

untitled_analysis = analyze_novel_input({"text": "没有章节标题的正文。\n角色说：“这不够清楚。”"})
assert_true(untitled_analysis["chapters"][0]["title"] == "未识别章节", "untitled chapter title")
assert_true(any("未识别到明确章节标题" in warning for warning in untitled_analysis["warnings"]), "untitled warning")

print("Converter tests passed.")
