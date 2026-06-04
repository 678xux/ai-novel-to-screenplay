from __future__ import annotations

import json
import os
import urllib.error
import urllib.request
from typing import Any

from .converter import build_conversion_result, convert_novel_to_screenplay, split_chapters
from .schema import SCREENPLAY_SCHEMA

DEFAULT_MODEL = "gpt-4.1-mini"
DEFAULT_BASE_URL = "https://api.openai.com/v1"
DEFAULT_INPUT_CHAR_LIMIT = 24000


def get_ai_config(env: dict[str, str] | None = None) -> dict:
    env = env or os.environ
    api_key = env.get("OPENAI_API_KEY") or env.get("AI_API_KEY") or ""
    return {
        "enabled": bool(api_key),
        "api_key": api_key,
        "base_url": (env.get("OPENAI_BASE_URL") or env.get("AI_BASE_URL") or DEFAULT_BASE_URL).rstrip("/"),
        "model": env.get("OPENAI_MODEL") or env.get("AI_MODEL") or DEFAULT_MODEL,
        "input_char_limit": int(env.get("AI_INPUT_CHAR_LIMIT") or DEFAULT_INPUT_CHAR_LIMIT),
    }


def get_public_ai_config(env: dict[str, str] | None = None) -> dict:
    config = get_ai_config(env)
    provider = ""
    if config["enabled"]:
        provider = config["base_url"].replace("https://", "").replace("http://", "").split("/")[0]
    return {
        "enabled": config["enabled"],
        "model": config["model"] if config["enabled"] else "",
        "provider": provider,
    }


def compact_novel_text(text: str, limit: int) -> str:
    normalized = str(text or "").strip()
    if len(normalized) <= limit:
        return normalized
    half = limit // 2
    return f"{normalized[:half]}\n\n[...中间内容已截断，规则引擎初稿仍保留完整结构...]\n\n{normalized[-half:]}"


def build_messages(payload: dict, rule_script: dict, raw_text: str, config: dict) -> list[dict]:
    return [
        {
            "role": "system",
            "content": "\n".join(
                [
                    "你是专业的小说改编剧本助手。",
                    "任务：在不改变 YAML Schema 的前提下，增强规则引擎生成的剧本结构。",
                    "只返回 JSON，格式必须是 {\"script\": {...}}，不要 Markdown，不要解释。",
                    "重点：把小说叙述转成可表演动作、对白、场景冲突和转折；保留 source_chapter 追溯信息。",
                    "不要生成超出原文事实太远的新剧情，可以补充合理的剧作表达。",
                ]
            ),
        },
        {
            "role": "user",
            "content": json.dumps(
                {
                    "requested_title": payload.get("title", ""),
                    "adaptation_mode": payload.get("mode", "drama"),
                    "density": payload.get("density", "balanced"),
                    "user_characters": payload.get("characters", ""),
                    "user_themes": payload.get("themes", ""),
                    "schema": SCREENPLAY_SCHEMA,
                    "rule_engine_draft": rule_script,
                    "novel_text_for_reference": compact_novel_text(raw_text, config["input_char_limit"]),
                },
                ensure_ascii=False,
                indent=2,
            ),
        },
    ]


def extract_json_object(text: str) -> dict:
    trimmed = str(text or "").strip()
    if not trimmed:
        raise ValueError("AI 返回为空。")
    if trimmed.startswith("{"):
        return json.loads(trimmed)
    if "```" in trimmed:
        fenced = trimmed.split("```", 2)[1]
        if fenced.strip().lower().startswith("json"):
            fenced = fenced.strip()[4:]
        return json.loads(fenced)
    start = trimmed.find("{")
    end = trimmed.rfind("}")
    if start >= 0 and end > start:
        return json.loads(trimmed[start : end + 1])
    raise ValueError("AI 返回不是 JSON。")


def ensure_list(value: Any, fallback: list) -> list:
    return value if isinstance(value, list) else fallback


def normalize_ai_script(candidate: Any, fallback: dict) -> dict:
    script = candidate if isinstance(candidate, dict) else {}
    source = script.get("source") if isinstance(script.get("source"), dict) else {}
    production_notes = script.get("production_notes") if isinstance(script.get("production_notes"), dict) else {}
    fallback_notes = fallback.get("production_notes", {})
    return {
        **fallback,
        **script,
        "schema_version": fallback["schema_version"],
        "title": script.get("title") or fallback["title"],
        "source": {
            **fallback["source"],
            **source,
            "type": "novel",
            "chapter_count": fallback["source"]["chapter_count"],
            "input_language": fallback["source"]["input_language"],
        },
        "themes": ensure_list(script.get("themes"), fallback.get("themes", [])),
        "characters": ensure_list(script.get("characters"), fallback.get("characters", [])),
        "acts": ensure_list(script.get("acts"), fallback.get("acts", [])),
        "production_notes": {
            **fallback_notes,
            **production_notes,
            "adaptation_warnings": ensure_list(production_notes.get("adaptation_warnings"), fallback_notes.get("adaptation_warnings", [])),
            "revision_suggestions": ensure_list(production_notes.get("revision_suggestions"), fallback_notes.get("revision_suggestions", [])),
        },
    }


def call_openai_compatible_chat(config: dict, messages: list[dict]) -> dict:
    request = urllib.request.Request(
        f"{config['base_url']}/chat/completions",
        data=json.dumps(
            {
                "model": config["model"],
                "messages": messages,
                "temperature": 0.4,
                "response_format": {"type": "json_object"},
            },
            ensure_ascii=False,
        ).encode("utf-8"),
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {config['api_key']}",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=90) as response:
            body = json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"AI 请求失败：{exc.code} {detail[:240]}") from exc
    content = body.get("choices", [{}])[0].get("message", {}).get("content")
    return extract_json_object(content)


def convert_novel_to_screenplay_optional_ai(payload: dict | None = None, env: dict[str, str] | None = None) -> dict:
    payload = payload or {}
    rule_result = convert_novel_to_screenplay(payload)
    requested_ai = payload.get("engine") == "ai"
    config = get_ai_config(env)
    if not requested_ai:
        return rule_result
    if not config["enabled"]:
        return {
            **rule_result,
            "meta": {
                **rule_result.get("meta", {}),
                "engine": "rules",
                "ai": {
                    "requested": True,
                    "used": False,
                    "reason": "未配置 OPENAI_API_KEY，已自动回退到规则引擎。",
                },
            },
        }

    try:
        messages = build_messages(payload, rule_result["script"], payload.get("text", ""), config)
        ai_draft = call_openai_compatible_chat(config, messages)
        enhanced_script = normalize_ai_script(ai_draft.get("script"), rule_result["script"])
        chapters = split_chapters(payload.get("text", ""))
        return build_conversion_result(
            enhanced_script,
            chapters,
            payload.get("text", ""),
            {
                "engine": "ai",
                "ai": {
                    "requested": True,
                    "used": True,
                    "model": config["model"],
                    "provider": config["base_url"].replace("https://", "").replace("http://", "").split("/")[0],
                },
            },
        )
    except Exception as exc:  # noqa: BLE001 - UI needs graceful fallback reason.
        return {
            **rule_result,
            "meta": {
                **rule_result.get("meta", {}),
                "engine": "rules",
                "ai": {
                    "requested": True,
                    "used": False,
                    "reason": str(exc) or "AI 增强失败，已自动回退到规则引擎。",
                },
            },
        }
