from __future__ import annotations

import json
import socket
import subprocess
import sys
import time
from pathlib import Path
from urllib import error, request


ROOT_DIR = Path(__file__).resolve().parents[1]
SAMPLE_PATH = ROOT_DIR / "examples" / "three-chapter-novel.txt"


def assert_true(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def find_free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("127.0.0.1", 0))
        return int(sock.getsockname()[1])


def read_url(base_url: str, path: str) -> tuple[int, str, str]:
    with request.urlopen(f"{base_url}{path}", timeout=10) as response:
        return response.status, response.headers.get("Content-Type", ""), response.read().decode("utf-8")


def post_json(base_url: str, path: str, payload: dict, expected_status: int = 200) -> dict:
    encoded = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    req = request.Request(
        f"{base_url}{path}",
        data=encoded,
        headers={"Content-Type": "application/json; charset=utf-8"},
        method="POST",
    )
    try:
        with request.urlopen(req, timeout=20) as response:
            status = response.status
            body = response.read().decode("utf-8")
    except error.HTTPError as exc:
        status = exc.code
        body = exc.read().decode("utf-8")

    assert_true(status == expected_status, f"{path} expected {expected_status}, got {status}: {body[:200]}")
    return json.loads(body)


def wait_for_server(base_url: str, process: subprocess.Popen, timeout_seconds: float = 10) -> None:
    deadline = time.time() + timeout_seconds
    last_error = ""
    while time.time() < deadline:
        if process.poll() is not None:
            stdout, stderr = process.communicate(timeout=1)
            raise RuntimeError(f"Server exited early.\nstdout:\n{stdout}\nstderr:\n{stderr}")
        try:
            status, _, body = read_url(base_url, "/api/config")
            if status == 200 and json.loads(body).get("ok"):
                return
        except Exception as exc:  # noqa: BLE001 - retry loop reports final error.
            last_error = str(exc)
        time.sleep(0.2)
    raise RuntimeError(f"Server did not become ready: {last_error}")


def start_server(port: int) -> subprocess.Popen:
    return subprocess.Popen(
        [sys.executable, "-c", f"from app.server import run; run(port={port})"],
        cwd=ROOT_DIR,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        encoding="utf-8",
    )


def stop_server(process: subprocess.Popen) -> None:
    if process.poll() is not None:
        return
    process.terminate()
    try:
        process.wait(timeout=5)
    except subprocess.TimeoutExpired:
        process.kill()
        process.wait(timeout=5)


def assert_export(base_url: str, script: dict, yaml_text: str, export_format: str) -> dict:
    exported = post_json(base_url, "/api/export", {"script": script, "yaml": yaml_text, "format": export_format})
    assert_true(exported["ok"] is True, f"{export_format} export ok")
    assert_true(exported["filename"], f"{export_format} export filename")
    assert_true(exported["content"], f"{export_format} export content")
    return exported


def main() -> None:
    port = find_free_port()
    base_url = f"http://127.0.0.1:{port}"
    process = start_server(port)
    try:
        wait_for_server(base_url, process)

        status, content_type, index_html = read_url(base_url, "/")
        assert_true(status == 200, "index status")
        assert_true("text/html" in content_type, "index content type")
        assert_true("AI 小说转剧本工具" in index_html, "index title")

        sample_text = SAMPLE_PATH.read_text(encoding="utf-8")
        analysis = post_json(base_url, "/api/analyze", {"text": sample_text, "characters": "林澈，沈雾，周栩"})
        assert_true(analysis["ok"] is True, "analysis ok")
        assert_true(analysis["status"] == "ready", "analysis status")
        assert_true(analysis["summary"]["chapter_count"] == 3, "analysis chapter count")
        assert_true(analysis["summary"]["dialogues"] >= 3, "analysis dialogue count")

        dirty_text = "最新网址：https://example.com\n----\n" + sample_text.replace("“", "「").replace("”", "」") + "\n返回目录"
        cleanup = post_json(base_url, "/api/cleanup", {"text": dirty_text})
        assert_true(cleanup["ok"] is True, "cleanup ok")
        assert_true(cleanup["stats"]["removed_lines"] >= 3, "cleanup removed lines")
        assert_true("https://" not in cleanup["text"], "cleanup removes url")
        assert_true("「" not in cleanup["text"] and "」" not in cleanup["text"], "cleanup normalizes quotes")

        convert_payload = {
            "title": "E2E runtime sample",
            "text": cleanup["text"],
            "characters": "林澈，沈雾，周栩",
            "themes": "信任，真相，成长",
            "mode": "drama",
            "density": "balanced",
            "engine": "rules",
        }
        converted = post_json(base_url, "/api/convert", convert_payload)
        assert_true(converted["ok"] is True, "convert ok")
        assert_true(converted["stats"]["chapters"] == 3, "convert chapter count")
        assert_true(converted["stats"]["scenes"] >= 3, "convert scene count")
        assert_true(converted["stats"]["beats"] >= 3, "convert beat count")
        assert_true("runtime_plan:" in converted["yaml"], "yaml runtime plan")
        assert_true("source_coverage:" in converted["yaml"], "yaml source coverage")
        assert_true("revision_tasks:" in converted["yaml"], "yaml revision tasks")

        script = converted["script"]
        scenes = [scene for act in script["acts"] for scene in act.get("scenes", [])]
        assert_true(all(scene.get("source_chapter") for scene in scenes), "scene traceability")
        assert_true(all(scene.get("objective") and scene.get("obstacle") and scene.get("outcome") for scene in scenes), "scene dramatic fields")
        assert_true(all(scene.get("estimated_runtime_minutes", 0) > 0 for scene in scenes), "scene runtime estimates")
        assert_true(script["production_notes"]["estimated_runtime_minutes"] > 0, "total runtime")
        assert_true(script["production_notes"]["runtime_plan"]["average_scene_minutes"] > 0, "runtime plan average")
        source_coverage = script["production_notes"]["source_coverage"]
        assert_true(len(source_coverage) == 3, "source coverage count")
        assert_true(all(item["covered"] for item in source_coverage), "source coverage covered")
        revision_tasks = script["production_notes"]["revision_tasks"]
        assert_true(len(revision_tasks) >= 1, "revision task count")
        assert_true(any(task["target_scene_ids"] for task in revision_tasks), "revision task scene targets")
        assert_true(converted["quality"]["metrics"]["revision_task_count"] == len(revision_tasks), "revision task quality metric")
        assert_true(any(check["id"] == "schema_contract" and check["passed"] for check in converted["quality"]["checks"]), "quality schema check")

        yaml_export = assert_export(base_url, script, converted["yaml"], "yaml")
        assert_true(yaml_export["content"] == converted["yaml"], "yaml export preserves content")

        json_export = assert_export(base_url, script, converted["yaml"], "json")
        json_document = json.loads(json_export["content"])
        assert_true(json_document["script"]["title"] == "E2E runtime sample", "json export script title")

        outline_export = assert_export(base_url, script, converted["yaml"], "outline_md")
        outline = outline_export["content"]
        for fragment in ["# E2E runtime sample", "## 来源覆盖", "## 修订任务", "## 篇幅规划", "目标：", "阻碍：", "结果：", "道具/线索"]:
            assert_true(fragment in outline, f"outline contains {fragment}")

        bad_convert = post_json(base_url, "/api/convert", {"text": ""}, expected_status=400)
        assert_true(bad_convert["ok"] is False and bad_convert.get("error"), "empty convert error")
    finally:
        stop_server(process)

    print(
        json.dumps(
            {
                "ok": True,
                "port": port,
                "checked": [
                    "static index",
                    "analyze",
                    "cleanup",
                    "convert",
                    "yaml/json/markdown export",
                    "error response",
                ],
            },
            ensure_ascii=False,
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
