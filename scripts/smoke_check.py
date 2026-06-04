from pathlib import Path
import json
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.converter import convert_novel_to_screenplay

sample = Path("examples/three-chapter-novel.txt").read_text(encoding="utf-8")
result = convert_novel_to_screenplay(
    {
        "title": "烟雾测试",
        "text": sample,
        "characters": "林澈，沈雾，周栩",
        "themes": "真相，选择",
    }
)

required_fragments = [
    "schema_version: 1.0.0",
    "chapter_count: 3",
    "acts:",
    "scenes:",
    "beats:",
    "characters:",
]
missing = [fragment for fragment in required_fragments if fragment not in result["yaml"]]
if missing:
    raise SystemExit(f"Smoke check failed. Missing: {', '.join(missing)}")
if result["stats"]["chapters"] < 3 or result["stats"]["scenes"] < 3 or result["stats"]["beats"] < 3:
    raise SystemExit("Smoke check failed. Generated structure is too small.")

print("Smoke check passed.")
print(json.dumps(result["stats"], ensure_ascii=False, indent=2))
print(json.dumps(result["meta"], ensure_ascii=False, indent=2))
