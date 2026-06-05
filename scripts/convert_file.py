from __future__ import annotations

import argparse
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.ai_adapter import convert_novel_to_screenplay_optional_ai
from app.exporter import EXPORT_FORMATS, export_screenplay


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Convert a 3+ chapter novel text file into structured screenplay output."
    )
    parser.add_argument("input", help="Path to a UTF-8 TXT or Markdown novel file.")
    parser.add_argument(
        "-o",
        "--output",
        help="Output file path. Defaults to '<input-name>.screenplay.<format>'.",
    )
    parser.add_argument("--title", default="", help="Screenplay title. Defaults to the input file name.")
    parser.add_argument("--characters", default="", help="Comma-separated major characters.")
    parser.add_argument("--themes", default="", help="Comma-separated themes.")
    parser.add_argument(
        "--mode",
        choices=["drama", "short", "stage"],
        default="drama",
        help="Adaptation mode: drama, short, or stage.",
    )
    parser.add_argument(
        "--density",
        choices=["compact", "balanced", "detailed"],
        default="balanced",
        help="Scene splitting density.",
    )
    parser.add_argument(
        "--engine",
        choices=["rules", "ai"],
        default="rules",
        help="Use local rules engine or optional AI enhancement.",
    )
    parser.add_argument(
        "--format",
        choices=sorted(EXPORT_FORMATS.keys()),
        default="yaml",
        help="Export format: yaml, json, or outline_md.",
    )
    return parser


def default_output_path(input_path: Path, export_format: str) -> Path:
    extension = EXPORT_FORMATS[export_format]["extension"]
    return input_path.with_name(f"{input_path.stem}.{extension}")


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    input_path = Path(args.input)
    if not input_path.exists() or not input_path.is_file():
        print(f"Input file not found: {input_path}", file=sys.stderr)
        return 2

    text = input_path.read_text(encoding="utf-8")
    result = convert_novel_to_screenplay_optional_ai(
        {
            "title": args.title or input_path.stem,
            "text": text,
            "characters": args.characters,
            "themes": args.themes,
            "mode": args.mode,
            "density": args.density,
            "engine": args.engine,
        }
    )

    exported = export_screenplay(result["script"], args.format, result["yaml"])
    output_path = Path(args.output) if args.output else default_output_path(input_path, args.format)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(exported["content"], encoding="utf-8")

    stats = result.get("stats", {})
    quality = result.get("quality", {})
    print(f"Created: {output_path}")
    print(
        "Stats: "
        f"{stats.get('chapters', 0)} chapters, "
        f"{stats.get('characters', 0)} characters, "
        f"{stats.get('scenes', 0)} scenes, "
        f"{stats.get('beats', 0)} beats"
    )
    print(f"Quality: {quality.get('score', 0)} / {quality.get('status', 'unknown')}")
    for warning in result.get("warnings", []):
        print(f"Warning: {warning}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
