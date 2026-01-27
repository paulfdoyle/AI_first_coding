#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import subprocess
import sys
import threading
import time
import uuid
from dataclasses import asdict, dataclass
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any, Dict, List, Optional
from urllib.parse import parse_qs, urlparse

ROOT = Path(__file__).resolve().parents[2]
DATA_DIR = ROOT / "AI_first/data"
QUICK_ISSUES_PATH = DATA_DIR / "quick_issues.json"
SIMPLE_PROJECT_PATH = DATA_DIR / "simple_project.json"
UI_STYLE_SELECTION_PATH = DATA_DIR / "ui_style_selection.json"
SIMPLE_PROJECT_MD_PATH = ROOT / "AI_first/projects/simple_pm/project_context.md"


def _now() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%S")


def _is_local_origin(origin: Optional[str]) -> bool:
    if not origin:
        return True
    return (
        origin.startswith("http://localhost")
        or origin.startswith("http://127.0.0.1")
        or origin.startswith("http://[::1]")
        or origin.startswith("http://[::]")
    )


def _tail_lines(path: Path, limit: int = 20) -> str:
    try:
        lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
        return "\n".join(lines[-limit:])
    except Exception:
        return ""


def _iso_mtime(path: Path) -> Optional[str]:
    if not path.exists():
        return None
    return time.strftime("%Y-%m-%dT%H:%M:%S", time.localtime(path.stat().st_mtime))


def _write_json(path: Path, payload: Dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
    tmp.replace(path)


def _read_json(path: Path, default: Dict[str, Any]) -> Dict[str, Any]:
    if not path.exists():
        _write_json(path, default)
        return default
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        _write_json(path, default)
        return default


def _default_quick_issues() -> Dict[str, Any]:
    return {"updated_at": time.strftime("%Y-%m-%d"), "issues": []}


def _default_simple_project() -> Dict[str, Any]:
    return {
        "title": "Untitled project",
        "summary": "Describe the current focus, scope, and key decisions here.",
        "updated_at": time.strftime("%Y-%m-%d"),
        "entries": [],
    }


def _default_ui_style_selection() -> Dict[str, Any]:
    return {"active_template_id": "", "notes": "", "updated_at": time.strftime("%Y-%m-%d")}


def _next_issue_id(issues: List[Dict[str, Any]], now_date: str) -> str:
    prefix = f"QI-{now_date[:4]}-{now_date[5:7]}-"
    numbers: List[int] = []
    for issue in issues:
        issue_id = str(issue.get("id") or "")
        if not issue_id.startswith(prefix):
            continue
        tail = issue_id.rsplit("-", 1)[-1]
        if tail.isdigit():
            numbers.append(int(tail))
    next_num = (max(numbers) if numbers else 0) + 1
    return f"{prefix}{next_num:03d}"


def _normalize_status(value: Optional[str]) -> str:
    value = (value or "").strip().lower()
    if value in {"open", "in_progress", "closed"}:
        return value
    return "open"


def _normalize_priority(value: Optional[str]) -> str:
    value = (value or "").strip().lower()
    if value in {"high", "medium", "low"}:
        return value
    return "medium"


def _render_simple_project_md(payload: Dict[str, Any]) -> str:
    title = (payload.get("title") or "Untitled project").strip()
    summary = (payload.get("summary") or "").strip() or "Describe the current focus, scope, and key decisions here."
    entries = payload.get("entries") or []
    lines = [
        "# Simple Project Log",
        "",
        "## Title",
        title,
        "",
        "## Summary",
        summary,
        "",
        "## Recent Updates",
    ]
    if not entries:
        lines.append("- No updates logged yet.")
    else:
        for entry in entries:
            date = entry.get("date") or ""
            text = entry.get("text") or ""
            lines.append(f"- {date} — {text}".strip())
    return "\n".join(lines) + "\n"


def _write_simple_project_md(payload: Dict[str, Any]) -> None:
    SIMPLE_PROJECT_MD_PATH.parent.mkdir(parents=True, exist_ok=True)
    SIMPLE_PROJECT_MD_PATH.write_text(_render_simple_project_md(payload), encoding="utf-8")


@dataclass(frozen=True)
class ActionSpec:
    id: str
    label: str
    description: str
    commands: List[List[str]]
    fallback_cmd: str


@dataclass
class Job:
    id: str
    action: str
    status: str
    log_path: str
    log_url: str
    started_at: Optional[str] = None
    ended_at: Optional[str] = None
    returncode: Optional[int] = None


def _action_specs(python_bin: str) -> Dict[str, ActionSpec]:
    return {
        "render_docs": ActionSpec(
            id="render_docs",
            label="Render docs",
            description="Refresh AI_first/ui/docs from markdown.",
            commands=[[python_bin, "AI_first/scripts/render_docs.py"]],
            fallback_cmd="python3 AI_first/scripts/render_docs.py",
        ),
        "render_pm": ActionSpec(
            id="render_pm",
            label="Render PM report",
            description="Refresh AI_first/ui/PM.html and project detail pages.",
            commands=[[python_bin, "AI_first/scripts/render_pm.py"]],
            fallback_cmd="python3 AI_first/scripts/render_pm.py",
        ),
        "bugmgmt_export": ActionSpec(
            id="bugmgmt_export",
            label="Export BugMgmt",
            description="Regenerate BugMgmt JSON + HTML exports.",
            commands=[
                [
                    python_bin,
                    "AI_first/scripts/issues.py",
                    "list",
                    "--format",
                    "json",
                    "--output",
                    "AI_first/bugmgmt/exports/json/bugmgmt_issues.json",
                ],
                [
                    python_bin,
                    "AI_first/scripts/issues.py",
                    "list",
                    "--format",
                    "html",
                    "--output",
                    "AI_first/ui/bugmgmt_issues.html",
                ],
            ],
            fallback_cmd=(
                "python3 AI_first/scripts/issues.py list --format json --output "
                "AI_first/bugmgmt/exports/json/bugmgmt_issues.json && "
                "python3 AI_first/scripts/issues.py list --format html --output "
                "AI_first/ui/bugmgmt_issues.html"
            ),
        ),
        "refresh_all": ActionSpec(
            id="refresh_all",
            label="Refresh all",
            description="Render docs + PM report + BugMgmt exports.",
            commands=[
                [python_bin, "AI_first/scripts/render_docs.py"],
                [python_bin, "AI_first/scripts/render_pm.py"],
                [
                    python_bin,
                    "AI_first/scripts/issues.py",
                    "list",
                    "--format",
                    "json",
                    "--output",
                    "AI_first/bugmgmt/exports/json/bugmgmt_issues.json",
                ],
                [
                    python_bin,
                    "AI_first/scripts/issues.py",
                    "list",
                    "--format",
                    "html",
                    "--output",
                    "AI_first/ui/bugmgmt_issues.html",
                ],
            ],
            fallback_cmd=(
                "python3 AI_first/scripts/render_docs.py && "
                "python3 AI_first/scripts/render_pm.py && "
                "python3 AI_first/scripts/issues.py list --format json --output "
                "AI_first/bugmgmt/exports/json/bugmgmt_issues.json && "
                "python3 AI_first/scripts/issues.py list --format html --output "
                "AI_first/ui/bugmgmt_issues.html"
            ),
        ),
    }


class ControlServer:
    def __init__(self, cfg: argparse.Namespace) -> None:
        self.cfg = cfg
        self.jobs: Dict[str, Job] = {}
        self.job_order: List[str] = []
        self.lock = threading.Lock()
        self.queue: List[str] = []
        self.queue_running = False
        self.error_log: List[Dict[str, Any]] = []
        self.actions = _action_specs(cfg.python)

    def _job_log_path(self, job_id: str, action: str) -> Path:
        log_dir = Path(self.cfg.log_dir).expanduser()
        log_dir.mkdir(parents=True, exist_ok=True)
        safe_id = f"{job_id}_{action}".replace("/", "_")
        return log_dir / f"{safe_id}.log"

    def _command_for(self, action: str) -> List[List[str]]:
        spec = self.actions.get(action)
        if not spec:
            raise ValueError(f"Unsupported action {action}")
        return spec.commands

    def status_payload(self) -> Dict[str, Any]:
        outputs = {
            "pm_html": _iso_mtime(ROOT / "AI_first/ui/PM.html"),
            "bugmgmt_html": _iso_mtime(ROOT / "AI_first/ui/bugmgmt_issues.html"),
            "docs_process": _iso_mtime(ROOT / "AI_first/ui/docs/process.html"),
        }
        quick_issues = _read_json(QUICK_ISSUES_PATH, _default_quick_issues())
        simple_project = _read_json(SIMPLE_PROJECT_PATH, _default_simple_project())
        ui_style = _read_json(UI_STYLE_SELECTION_PATH, _default_ui_style_selection())
        with self.lock:
            jobs = [asdict(self.jobs[jid]) for jid in self.job_order[-8:]][::-1]
            active_jobs = [
                {"id": j.id, "action": j.action, "status": j.status}
                for j in self.jobs.values()
                if j.status in {"queued", "running"}
            ]
            error_jobs = list(self.error_log)[-50:][::-1]
        return {
            "ok": True,
            "server_time": _now(),
            "repo_root": str(ROOT),
            "api_base": f"http://{self.cfg.host}:{self.cfg.port}",
            "outputs": outputs,
            "quick_issues": {
                "count": len(quick_issues.get("issues") or []),
                "updated_at": quick_issues.get("updated_at"),
            },
            "simple_project": {
                "title": simple_project.get("title"),
                "updated_at": simple_project.get("updated_at"),
            },
            "ui_style": ui_style,
            "actions": [
                {
                    "id": spec.id,
                    "label": spec.label,
                    "description": spec.description,
                    "fallback_cmd": spec.fallback_cmd,
                }
                for spec in self.actions.values()
            ],
            "jobs": jobs,
            "active_jobs": active_jobs,
            "error_jobs": error_jobs,
        }

    def start_job(self, action: str) -> Job:
        job_id = uuid.uuid4().hex[:10]
        log_path = self._job_log_path(job_id, action)
        log_url = f"http://{self.cfg.host}:{self.cfg.port}/logs/{log_path.name}"
        job = Job(
            id=job_id,
            action=action,
            status="queued",
            log_path=str(log_path),
            log_url=log_url,
        )
        with self.lock:
            self.jobs[job_id] = job
            self.job_order.append(job_id)
            self.queue.append(job_id)
            should_start = not self.queue_running
            if should_start:
                self.queue_running = True
        if should_start:
            thread = threading.Thread(target=self._queue_worker, daemon=True)
            thread.start()
        return job

    def _queue_worker(self) -> None:
        while True:
            with self.lock:
                if not self.queue:
                    self.queue_running = False
                    return
                job_id = self.queue.pop(0)
                job = self.jobs.get(job_id)
            if job is None:
                continue
            self._run_job(job)

    def _run_job(self, job: Job) -> None:
        job.status = "running"
        job.started_at = _now()
        commands = self._command_for(job.action)
        log_path = Path(job.log_path)
        log_path.parent.mkdir(parents=True, exist_ok=True)
        returncode = 0
        with log_path.open("w", encoding="utf-8") as fh:
            for cmd in commands:
                fh.write(f"[{_now()}] RUN: {' '.join(cmd)}\n")
                fh.flush()
                proc = subprocess.Popen(
                    cmd,
                    cwd=str(ROOT),
                    stdout=fh,
                    stderr=subprocess.STDOUT,
                    text=True,
                )
                returncode = proc.wait()
                if returncode != 0:
                    break
        job.returncode = returncode
        job.ended_at = _now()
        job.status = "done" if returncode == 0 else "error"
        if job.status == "error":
            with self.lock:
                self.error_log.append(
                    {
                        "id": job.id,
                        "action": job.action,
                        "status": job.status,
                        "returncode": job.returncode,
                        "started_at": job.started_at,
                        "ended_at": job.ended_at,
                        "log_url": job.log_url,
                    }
                )
                if len(self.error_log) > 200:
                    self.error_log = self.error_log[-200:]

    def get_job(self, job_id: str) -> Optional[Job]:
        with self.lock:
            return self.jobs.get(job_id)


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Local control server for AI_first (localhost only).")
    p.add_argument("--host", default="127.0.0.1", help="Host to bind (default: 127.0.0.1)")
    p.add_argument("--port", type=int, default=8790, help="Port to bind (default: 8790)")
    p.add_argument("--log-dir", default="AI_first/ui/logs", help="Directory for command logs")
    p.add_argument("--python", default=None, help="Python interpreter to use for commands")
    p.add_argument("--token", default=None, help="Optional token required via X-AI-Token header")
    return p.parse_args()


def make_handler(server: ControlServer):
    class Handler(BaseHTTPRequestHandler):
        def _send_json(self, status: int, payload: Dict[str, Any]) -> None:
            body = json.dumps(payload).encode("utf-8")
            self.send_response(status)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.send_header("Access-Control-Allow-Origin", "*")
            self.send_header("Access-Control-Allow-Headers", "Content-Type, X-AI-Token")
            self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
            self.end_headers()
            self.wfile.write(body)

        def _send_text(self, status: int, body: str) -> None:
            data = body.encode("utf-8")
            self.send_response(status)
            self.send_header("Content-Type", "text/plain; charset=utf-8")
            self.send_header("Content-Length", str(len(data)))
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()
            self.wfile.write(data)

        def _auth_ok(self) -> bool:
            if not _is_local_origin(self.headers.get("Origin")):
                return False
            token = server.cfg.token
            if token is None:
                return True
            return self.headers.get("X-AI-Token") == token

        def do_OPTIONS(self) -> None:
            self.send_response(204)
            self.send_header("Access-Control-Allow-Origin", "*")
            self.send_header("Access-Control-Allow-Headers", "Content-Type, X-AI-Token")
            self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
            self.end_headers()

        def do_GET(self) -> None:
            if not self._auth_ok():
                self._send_text(403, "Forbidden")
                return
            parsed = urlparse(self.path)
            if parsed.path == "/api/status":
                self._send_json(200, server.status_payload())
                return
            if parsed.path == "/api/quick-issues":
                payload = _read_json(QUICK_ISSUES_PATH, _default_quick_issues())
                self._send_json(200, payload)
                return
            if parsed.path == "/api/simple-project":
                payload = _read_json(SIMPLE_PROJECT_PATH, _default_simple_project())
                self._send_json(200, payload)
                return
            if parsed.path == "/api/ui-style":
                payload = _read_json(UI_STYLE_SELECTION_PATH, _default_ui_style_selection())
                self._send_json(200, payload)
                return
            if parsed.path.startswith("/api/jobs/"):
                job_id = parsed.path.rsplit("/", 1)[-1]
                job = server.get_job(job_id)
                if not job:
                    self._send_json(404, {"error": "job not found"})
                    return
                query = parse_qs(parsed.query)
                tail = int((query.get("tail") or ["0"])[0])
                payload = asdict(job)
                if tail > 0:
                    payload["log_tail"] = _tail_lines(Path(job.log_path), limit=tail)
                self._send_json(200, payload)
                return
            if parsed.path.startswith("/logs/"):
                filename = parsed.path.split("/logs/")[-1]
                log_dir = Path(server.cfg.log_dir).expanduser()
                target = (log_dir / filename).resolve()
                if not target.exists() or log_dir.resolve() not in target.parents:
                    self._send_text(404, "Log not found")
                    return
                self._send_text(200, target.read_text(encoding="utf-8", errors="replace"))
                return
            self._send_text(200, "AI_first control server running.")

        def do_POST(self) -> None:
            if not self._auth_ok():
                self._send_text(403, "Forbidden")
                return
            parsed = urlparse(self.path)
            if parsed.path == "/api/errors/clear":
                with server.lock:
                    server.error_log.clear()
                self._send_json(200, {"status": "cleared"})
                return
            length = int(self.headers.get("Content-Length", "0"))
            raw = self.rfile.read(length) if length else b"{}"
            try:
                payload = json.loads(raw.decode("utf-8"))
            except Exception:
                self._send_json(400, {"error": "invalid json"})
                return
            if parsed.path == "/api/run":
                action = payload.get("action")
                if action not in server.actions:
                    self._send_json(400, {"error": "invalid action"})
                    return
                try:
                    job = server.start_job(str(action))
                except Exception as exc:
                    self._send_json(500, {"error": str(exc)})
                    return
                self._send_json(200, asdict(job))
                return
            if parsed.path == "/api/quick-issues":
                data = _read_json(QUICK_ISSUES_PATH, _default_quick_issues())
                issues = data.get("issues") or []
                action = (payload.get("action") or "").strip().lower()
                now_date = time.strftime("%Y-%m-%d")
                now_stamp = _now()
                if not action:
                    action = "update" if payload.get("id") else "create"
                if action == "create":
                    title = (payload.get("title") or "").strip()
                    if not title:
                        self._send_json(400, {"error": "title required"})
                        return
                    issue_id = _next_issue_id(issues, now_date)
                    issue = {
                        "id": issue_id,
                        "title": title,
                        "status": _normalize_status(payload.get("status")),
                        "priority": _normalize_priority(payload.get("priority")),
                        "owner": (payload.get("owner") or "unassigned").strip() or "unassigned",
                        "tags": payload.get("tags") or [],
                        "notes": (payload.get("notes") or "").strip(),
                        "created_at": now_stamp,
                        "updated_at": now_stamp,
                    }
                    if isinstance(issue["tags"], str):
                        issue["tags"] = [t.strip() for t in issue["tags"].split(",") if t.strip()]
                    issues.append(issue)
                elif action in {"update", "close"}:
                    issue_id = (payload.get("id") or "").strip()
                    if not issue_id:
                        self._send_json(400, {"error": "id required"})
                        return
                    target = next((i for i in issues if str(i.get("id")) == issue_id), None)
                    if not target:
                        self._send_json(404, {"error": "issue not found"})
                        return
                    if action == "close":
                        target["status"] = "closed"
                    if "title" in payload:
                        target["title"] = (payload.get("title") or "").strip()
                    if "status" in payload:
                        target["status"] = _normalize_status(payload.get("status"))
                    if "priority" in payload:
                        target["priority"] = _normalize_priority(payload.get("priority"))
                    if "owner" in payload:
                        target["owner"] = (payload.get("owner") or "unassigned").strip() or "unassigned"
                    if "tags" in payload:
                        tags = payload.get("tags") or []
                        if isinstance(tags, str):
                            tags = [t.strip() for t in tags.split(",") if t.strip()]
                        target["tags"] = tags
                    if "notes" in payload:
                        target["notes"] = (payload.get("notes") or "").strip()
                    target["updated_at"] = now_stamp
                else:
                    self._send_json(400, {"error": "invalid action"})
                    return
                data["issues"] = issues
                data["updated_at"] = now_date
                _write_json(QUICK_ISSUES_PATH, data)
                self._send_json(200, data)
                return
            if parsed.path == "/api/simple-project":
                data = _read_json(SIMPLE_PROJECT_PATH, _default_simple_project())
                now_date = time.strftime("%Y-%m-%d")
                if "title" in payload:
                    data["title"] = (payload.get("title") or "Untitled project").strip()
                if "summary" in payload:
                    data["summary"] = (payload.get("summary") or "").strip()
                if "entries" in payload and isinstance(payload.get("entries"), list):
                    data["entries"] = payload.get("entries") or []
                if "entry" in payload:
                    entry_text = (payload.get("entry") or "").strip()
                    if entry_text:
                        data.setdefault("entries", []).append({"date": now_date, "text": entry_text})
                data["updated_at"] = now_date
                _write_json(SIMPLE_PROJECT_PATH, data)
                _write_simple_project_md(data)
                self._send_json(200, data)
                return
            if parsed.path == "/api/ui-style":
                data = _read_json(UI_STYLE_SELECTION_PATH, _default_ui_style_selection())
                now_date = time.strftime("%Y-%m-%d")
                if "active_template_id" in payload:
                    data["active_template_id"] = (payload.get("active_template_id") or "").strip()
                if "notes" in payload:
                    data["notes"] = (payload.get("notes") or "").strip()
                data["updated_at"] = now_date
                _write_json(UI_STYLE_SELECTION_PATH, data)
                self._send_json(200, data)
                return
            self._send_json(404, {"error": "not found"})

        def log_message(self, format: str, *args: Any) -> None:
            return

    return Handler


def main() -> int:
    cfg = parse_args()
    python_bin = cfg.python or sys.executable
    if python_bin not in {"python3", "python"} and not Path(python_bin).exists():
        python_bin = sys.executable
    cfg.python = python_bin
    server = ControlServer(cfg)
    handler = make_handler(server)
    httpd = ThreadingHTTPServer((cfg.host, cfg.port), handler)
    print(f"AI_first control server listening on http://{cfg.host}:{cfg.port}")
    if cfg.token:
        print("Token required (X-AI-Token).")
    httpd.serve_forever()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
