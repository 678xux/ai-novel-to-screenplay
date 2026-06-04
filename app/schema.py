from __future__ import annotations

from typing import Any

SCRIPT_SCHEMA_VERSION = "1.0.0"

SCREENPLAY_SCHEMA = {
    "script": {
        "schema_version": "string",
        "title": "string",
        "source": {
            "type": "novel",
            "chapter_count": "number",
            "input_language": "string",
            "adaptation_mode": "string",
        },
        "logline": "string",
        "themes": ["string"],
        "characters": [
            {
                "id": "string",
                "name": "string",
                "role": "string",
                "traits": ["string"],
                "first_appearance": "string",
                "goal": "string",
                "arc": "string",
                "appearances": ["string"],
            }
        ],
        "acts": [
            {
                "id": "string",
                "title": "string",
                "source_chapters": ["string"],
                "purpose": "string",
                "scenes": [
                    {
                        "id": "string",
                        "title": "string",
                        "source_chapter": "string",
                        "location": "string",
                        "time": "string",
                        "mood": "string",
                        "summary": "string",
                        "objective": "string",
                        "obstacle": "string",
                        "outcome": "string",
                        "beats": [
                            {
                                "id": "string",
                                "type": "action | dialogue | narration | transition",
                                "speaker": "string?",
                                "text": "string",
                                "emotion": "string?",
                                "camera": "string?",
                                "hook": "string?",
                                "stage_direction": "string?",
                            }
                        ],
                        "conflict": "string",
                        "turning_point": "string",
                        "props": ["string"],
                        "notes": ["string"],
                    }
                ],
            }
        ],
        "production_notes": {
            "estimated_runtime_minutes": "number",
            "adaptation_warnings": ["string"],
            "revision_suggestions": ["string"],
        },
    }
}


def _type_name(value: Any) -> str:
    if isinstance(value, bool):
        return "boolean"
    if isinstance(value, str):
        return "string"
    if isinstance(value, (int, float)):
        return "number"
    if isinstance(value, list):
        return "array"
    if isinstance(value, dict):
        return "object"
    if value is None:
        return "null"
    return type(value).__name__


def _path(parent: str, key: str) -> str:
    return f"{parent}.{key}" if parent else key


def _schema_error(path: str, message: str) -> dict:
    return {"path": path, "message": message, "severity": "error"}


def _is_optional(spec: Any) -> bool:
    return isinstance(spec, str) and spec.endswith("?")


def _validate_scalar(value: Any, spec: str, path: str) -> list[dict]:
    optional = spec.endswith("?")
    core_spec = spec[:-1] if optional else spec
    if value is None and optional:
        return []

    if "|" in core_spec:
        allowed_values = {item.strip() for item in core_spec.split("|")}
        if not isinstance(value, str) or value not in allowed_values:
            return [
                _schema_error(
                    path,
                    f"{path} 必须是以下枚举值之一：{', '.join(sorted(allowed_values))}，当前为 {_type_name(value)}。",
                )
            ]
        return []

    if core_spec == "string":
        if not isinstance(value, str):
            return [_schema_error(path, f"{path} 必须是 string，当前为 {_type_name(value)}。")]
        return []

    if core_spec == "number":
        if not isinstance(value, (int, float)) or isinstance(value, bool):
            return [_schema_error(path, f"{path} 必须是 number，当前为 {_type_name(value)}。")]
        return []

    if value != core_spec:
        return [_schema_error(path, f"{path} 必须固定为 {core_spec}，当前为 {value!r}。")]
    return []


def _validate_value(value: Any, spec: Any, path: str) -> list[dict]:
    if isinstance(spec, str):
        return _validate_scalar(value, spec, path)

    if isinstance(spec, list):
        if not isinstance(value, list):
            return [_schema_error(path, f"{path} 必须是 array，当前为 {_type_name(value)}。")]
        if not spec:
            return []
        errors = []
        item_spec = spec[0]
        for index, item in enumerate(value):
            errors.extend(_validate_value(item, item_spec, f"{path}[{index}]"))
        return errors

    if isinstance(spec, dict):
        if not isinstance(value, dict):
            return [_schema_error(path, f"{path} 必须是 object，当前为 {_type_name(value)}。")]

        errors = []
        for key, child_spec in spec.items():
            child_path = _path(path, key)
            if key not in value:
                if not _is_optional(child_spec):
                    errors.append(_schema_error(child_path, f"缺少必填字段 {child_path}。"))
                continue
            errors.extend(_validate_value(value.get(key), child_spec, child_path))
        return errors

    return [_schema_error(path, f"{path} 的 Schema 定义无法识别。")]


def validate_screenplay_document(document: dict) -> list[dict]:
    """Validate the full YAML document shape: {"script": ...}."""
    return _validate_value(document, SCREENPLAY_SCHEMA, "")


def validate_screenplay_script(script: dict) -> list[dict]:
    """Validate a script object against the documented screenplay YAML Schema."""
    return validate_screenplay_document({"script": script})
