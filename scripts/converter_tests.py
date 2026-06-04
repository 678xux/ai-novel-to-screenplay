from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.analyzer import analyze_novel_input
from app.ai_adapter import convert_novel_to_screenplay_optional_ai, get_public_ai_config
from app.converter import convert_novel_to_screenplay, split_chapters, split_scene_groups
from app.exporter import export_screenplay, sanitize_filename
from app.preprocessor import cleanup_novel_text
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

long_chapter_paragraphs = [
    "清晨，林青站在码头，看见远处的船灯。",
    "阿禾低声说：“我们得先找到名单。”",
    "两人走进街道，雨水忽然变大。",
    "突然，黑衣人从巷子里冲出来，林青决定离开。",
    "夜晚，林青抵达医院门外，发现门牌被人换过。",
    "护士提醒：“别相信办公室里的人。”",
    "黎明，阿禾回到车站，终于揭开名单背后的秘密。",
]
balanced_groups = split_scene_groups(long_chapter_paragraphs, "balanced")
detailed_groups = split_scene_groups(long_chapter_paragraphs, "detailed")
compact_groups = split_scene_groups(long_chapter_paragraphs, "compact")
assert_true(len(detailed_groups) >= len(balanced_groups) >= len(compact_groups), "scene density groups")
assert_true(len(balanced_groups) >= 2, "balanced scene boundary split")

long_scene_text = """第一章 码头
清晨，林青站在码头，看见远处的船灯。
阿禾低声说：“我们得先找到名单。”
两人走进街道，雨水忽然变大。
突然，黑衣人从巷子里冲出来，林青决定离开。

第二章 医院
夜晚，林青抵达医院门外，发现门牌被人换过。
护士提醒：“别相信办公室里的人。”
林青穿过走廊，听见办公室里传来争执声。
下一刻，档案柜突然打开，旧名单掉在地上。

第三章 车站
黎明，阿禾回到车站，终于揭开名单背后的秘密。
林青发现父亲留下的符号，决定把名单交出去。
广播突然响起，危险正在靠近。
两人离开车站，故事进入新的选择。"""
long_balanced = convert_novel_to_screenplay({"title": "Long split", "text": long_scene_text, "characters": "林青，阿禾", "density": "balanced"})
long_compact = convert_novel_to_screenplay({"title": "Long split", "text": long_scene_text, "characters": "林青，阿禾", "density": "compact"})
assert_true(long_balanced["stats"]["scenes"] > long_balanced["stats"]["chapters"], "long text creates extra scenes")
assert_true(long_balanced["stats"]["scenes"] >= long_compact["stats"]["scenes"], "density affects integrated scene count")

mode_results = {
    mode: convert_novel_to_screenplay({"title": f"Mode {mode}", "text": long_scene_text, "characters": "林青，阿禾", "mode": mode})
    for mode in ["drama", "short", "stage"]
}
for mode, result in mode_results.items():
    assert_true(validate_screenplay_script(result["script"]) == [], f"{mode} schema validation")

drama_beats = [beat for act in mode_results["drama"]["script"]["acts"] for scene in act["scenes"] for beat in scene["beats"]]
short_beats = [beat for act in mode_results["short"]["script"]["acts"] for scene in act["scenes"] for beat in scene["beats"]]
stage_beats = [beat for act in mode_results["stage"]["script"]["acts"] for scene in act["scenes"] for beat in scene["beats"]]
assert_true(any("camera" in beat for beat in drama_beats), "drama mode camera hints")
assert_true(any("hook" in beat for beat in short_beats), "short mode hook hints")
assert_true(any("stage_direction" in beat for beat in stage_beats), "stage mode stage directions")
assert_true(any("短剧钩子" in note for note in mode_results["short"]["script"]["production_notes"]["revision_suggestions"]), "short mode suggestions")
assert_true(any("舞台空间" in note for note in mode_results["stage"]["script"]["production_notes"]["revision_suggestions"]), "stage mode suggestions")

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
assert_true(all(character["goal"] for character in sample_result["script"]["characters"]), "fixture character goals")
assert_true(all(character["arc"] for character in sample_result["script"]["characters"]), "fixture character arcs")
assert_true(any(character["appearances"] for character in sample_result["script"]["characters"]), "fixture character appearances")
sample_props = {prop for act in sample_result["script"]["acts"] for scene in act["scenes"] for prop in scene["props"]}
assert_true({"匿名信", "钥匙", "名单"} & sample_props, "fixture props extracted")
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

json_export = export_screenplay(sample_result["script"], "json")
assert_true(json_export["filename"].endswith(".screenplay.json"), "json export filename")
assert_true('"script"' in json_export["content"], "json export content")
assert_true(json_export["mime_type"].startswith("application/json"), "json export mime")

outline_export = export_screenplay(sample_result["script"], "outline_md")
assert_true(outline_export["filename"].endswith(".outline.md"), "outline export filename")
assert_true("# Fixture sample" in outline_export["content"], "outline export title")
assert_true("## 角色" in outline_export["content"], "outline export characters")
assert_true("###" in outline_export["content"], "outline export scenes")
assert_true("[动作]" in outline_export["content"] or "[对白]" in outline_export["content"], "outline export beat labels")
assert_true("道具/线索" in outline_export["content"], "outline export props")

yaml_export = export_screenplay(sample_result["script"], "yaml", sample_result["yaml"])
assert_true(yaml_export["content"] == sample_result["yaml"], "yaml export preserves generated yaml")
assert_true(sanitize_filename("坏/文件 名?") == "坏_文件_名", "sanitize filename")

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

dirty_text = """最新网址：https://example.com
----------------
第一章 旧书页
林青说：「先把线索收起来。」
请收藏本站


第二章 街道
www.example.com
夜晚，林青走进街道。

第三章 车站
返回目录
黎明，阿禾终于抵达车站。"""
cleaned = cleanup_novel_text(dirty_text)
assert_true(cleaned["stats"]["removed_lines"] >= 4, "cleanup removes noise")
assert_true("最新网址" not in cleaned["text"], "cleanup removes ad text")
assert_true("https://" not in cleaned["text"], "cleanup removes url")
assert_true("“先把线索收起来。”" in cleaned["text"], "cleanup normalizes quotes")
assert_true(len(split_chapters(cleaned["text"])) == 3, "cleanup keeps chapter structure")

print("Converter tests passed.")
