from __future__ import annotations

import re
from collections import Counter

from .converter import extract_speaker, normalize_text, split_chapters, split_paragraphs


def text_length(text: str) -> int:
    return len("".join(str(text or "").split()))


def detect_dialogue_count(text: str) -> int:
    return len(re.findall(r"[“\"]([^”\"]{2,})[”\"]", text or ""))


def candidate_characters(chapters: list[dict], known_names: list[str] | None = None) -> list[dict]:
    known_names = known_names or []
    counter: Counter[str] = Counter()
    first_seen: dict[str, str] = {}
    for chapter in chapters:
        for paragraph in split_paragraphs(chapter.get("text", "")):
            speaker = extract_speaker(paragraph, known_names)
            if not speaker:
                continue
            counter[speaker] += 1
            first_seen.setdefault(speaker, chapter.get("title", ""))

    return [
        {
            "name": name,
            "mentions": count,
            "first_appearance": first_seen.get(name, ""),
        }
        for name, count in counter.most_common(12)
    ]


def analyze_novel_input(payload: dict | None = None) -> dict:
    payload = payload or {}
    text = normalize_text(payload.get("text", ""))
    known_names = [item.strip() for item in re.split(r"[,，、\n]", normalize_text(payload.get("characters", ""))) if item.strip()]
    chapters = split_chapters(text)
    total_chars = text_length(text)
    chapter_summaries = []

    for index, chapter in enumerate(chapters, start=1):
        chapter_text = chapter.get("text", "")
        paragraphs = split_paragraphs(chapter_text)
        chapter_summaries.append(
            {
                "id": chapter.get("id") or f"chapter_{index:02d}",
                "title": chapter.get("title") or f"章节 {index}",
                "chars": text_length(chapter_text),
                "paragraphs": len(paragraphs),
                "dialogues": detect_dialogue_count(chapter_text),
            }
        )

    warnings = []
    if not text:
        warnings.append("请先输入或导入小说文本。")
    if len(chapters) < 3:
        warnings.append("当前识别章节少于 3 个，不满足题目要求。")
    if chapters and chapters[0].get("title") == "未识别章节":
        warnings.append("未识别到明确章节标题，建议使用“第一章 / Chapter 1 / 1. 标题”等格式。")
    if total_chars < 300:
        warnings.append("输入文本较短，生成结果可能更像提纲。")
    if not any(item["dialogues"] for item in chapter_summaries):
        warnings.append("未识别到对白，后续可能需要人工补充角色对白。")

    status = "ready" if len(chapters) >= 3 and not warnings else "review"
    if not text or len(chapters) < 3:
        status = "needs_fix"

    return {
        "ok": True,
        "status": status,
        "summary": {
            "chapter_count": len(chapters),
            "chars": total_chars,
            "paragraphs": sum(item["paragraphs"] for item in chapter_summaries),
            "dialogues": sum(item["dialogues"] for item in chapter_summaries),
        },
        "chapters": chapter_summaries,
        "character_candidates": candidate_characters(chapters, known_names),
        "warnings": warnings,
    }
