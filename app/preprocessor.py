from __future__ import annotations

import re
from typing import Any

from .converter import normalize_text

NOISE_PATTERNS = [
    re.compile(r"最新网址|最新章节|手机阅读|加入书签|返回目录|点击下载|本章未完|请收藏|求推荐|求月票"),
    re.compile(r"https?://\S+|www\.\S+", re.I),
    re.compile(r"^[-_=*·•—]{4,}$"),
    re.compile(r"^\s*(目录|正文|上一章|下一章|返回书页|书友群|作者有话说)\s*$"),
    re.compile(r"^\s*第\s*[零〇一二三四五六七八九十百千万\d]+\s*页\s*$"),
]


def normalize_quotes(text: str) -> str:
    return (
        text.replace("「", "“")
        .replace("」", "”")
        .replace("『", "“")
        .replace("』", "”")
        .replace("＂", '"')
        .replace("“ ", "“")
        .replace(" ”", "”")
    )


def is_noise_line(line: str) -> bool:
    stripped = line.strip()
    if not stripped:
        return False
    if len(stripped) <= 2 and not re.search(r"[\u4e00-\u9fa5A-Za-z0-9]", stripped):
        return True
    return any(pattern.search(stripped) for pattern in NOISE_PATTERNS)


def cleanup_novel_text(text: Any = "") -> dict:
    original = normalize_text(text)
    normalized = normalize_quotes(original)
    raw_lines = normalized.split("\n") if normalized else []
    kept_lines: list[str] = []
    removed_lines: list[str] = []
    previous_blank = False

    for raw_line in raw_lines:
        line = re.sub(r"[ \t]+", " ", raw_line).strip()
        if is_noise_line(line):
            removed_lines.append(raw_line)
            continue

        if not line:
            if previous_blank:
                continue
            previous_blank = True
            kept_lines.append("")
            continue

        previous_blank = False
        kept_lines.append(line)

    cleaned = "\n".join(kept_lines).strip()
    return {
        "ok": True,
        "text": cleaned,
        "stats": {
            "original_chars": len(original),
            "cleaned_chars": len(cleaned),
            "original_lines": len(raw_lines),
            "cleaned_lines": len([line for line in kept_lines if line.strip()]),
            "removed_lines": len(removed_lines),
        },
        "removed_samples": [line.strip() for line in removed_lines[:6] if line.strip()],
    }
