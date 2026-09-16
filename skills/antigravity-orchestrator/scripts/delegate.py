#!/usr/bin/env python3
"""File-based message bus between Claude and Antigravity/Gemini agents.

Subcommands:
  send       Write a request for a prompt file, snapshot the project, print paste-ready text for the human.
  handshake  Set up a one-off connectivity test in .shared/handshake/.
  wait       Poll for the response file (exit 0 = arrived, 1 = timeout).
  verify     Check the response fields and list every file changed since the request (exit 0 = clean, 2 = issues).

Examples:
  python delegate.py send --task-dir TASKS/TASK-... --prompt-file TASKS/TASK-.../prompts/implementation/P001-v1.md
  python delegate.py wait --task-dir TASKS/TASK-... --message-id MSG-0001 --timeout 900
  python delegate.py verify --task-dir TASKS/TASK-... --message-id MSG-0001
  python delegate.py handshake --project .
"""
import argparse
import fnmatch
import json
import re
import sys
import time
from datetime import datetime
from pathlib import Path

SKIP_DIRS = {".git", "node_modules", ".venv", "venv", "__pycache__", ".mypy_cache", ".pytest_cache",
             "dist", "build", ".next", "target", ".idea", ".gradle"}
STATUSES = {"SUCCESS", "FAILED", "BLOCKED", "NEEDS_CLARIFICATION"}
REQUIRED = {
    "HANDSHAKE_REQUEST": ["message_id", "in_reply_to", "status"],
    "_default": ["message_id", "in_reply_to", "status", "files_changed", "commands_run",
                 "tests_run", "summary_or_output"],
}


def now():
    return datetime.now().astimezone().isoformat(timespec="seconds")


def project_root_for(task_dir: Path) -> Path:
    # TASKS/<ID>  or  .shared/handshake  → two levels up is the project root
    if task_dir.parent.name in ("TASKS", ".shared"):
        return task_dir.parent.parent
    for p in [task_dir, *task_dir.parents]:
        if (p / ".git").exists() or (p / "TASKS").is_dir():
            return p
    return task_dir.parent.parent


def comm_dir(task_dir: Path) -> Path:
    # task folders use communication/, the handshake folder is flat
    return task_dir / "communication" if (task_dir / "communication").is_dir() or task_dir.parent.name == "TASKS" else task_dir


def bus_path(task_dir: Path) -> Path:
    return comm_dir(task_dir) / "message_bus.jsonl"


def append_bus(task_dir: Path, entry: dict):
    p = bus_path(task_dir)
    p.parent.mkdir(parents=True, exist_ok=True)
    with p.open("a", encoding="utf-8") as f:
        f.write(json.dumps(entry, ensure_ascii=False) + "\n")


def next_message_id(task_dir: Path) -> str:
    n = 0
    p = bus_path(task_dir)
    if p.exists():
        for m in re.finditer(r'"MSG-(\d+)"', p.read_text(encoding="utf-8", errors="replace")):
            n = max(n, int(m.group(1)))
    return f"MSG-{n + 1:04d}"


def snapshot(root: Path) -> dict:
    snap = {}
    for p in root.rglob("*"):
        rel = p.relative_to(root)
        if any(part in SKIP_DIRS for part in rel.parts) or not p.is_file():
            continue
        try:
            st = p.stat()
        except OSError:
            continue
        snap[rel.as_posix()] = [st.st_size, st.st_mtime_ns]
    return snap


def allowed_from_prompt(prompt_file: Path) -> list:
    text = prompt_file.read_text(encoding="utf-8", errors="replace")
    m = re.search(r"^##\s*FILES YOU MAY MODIFY\s*$(.*?)(?=^##\s|\Z)", text, re.M | re.S | re.I)
    if not m:
        return []
    out = []
    for line in m.group(1).splitlines():
        line = line.strip()
        if not line or line.startswith("<!--"):
            continue
        ticks = re.findall(r"`([^`]+)`", line)
        if ticks:
            out.extend(t.strip() for t in ticks)
            continue
        line = re.sub(r"^[-*+]\s+|^\d+\.\s+", "", line)
        line = re.split(r"\s+[—–-]\s+|\s+\(|\s+#", line)[0].strip()
        if line and " " not in line:
            out.append(line)
    norm = [a.replace("\\", "/") for a in out]
    return [a[2:] if a.startswith("./") else a for a in norm]


def rel(root: Path, p: Path) -> str:
    try:
        return p.resolve().relative_to(root.resolve()).as_posix()
    except ValueError:
        return str(p.resolve())


def paste_text(project, request, response, prompt, mid):
    what = f"follow the prompt in `{prompt.resolve()}`" if prompt else "do what its objective says"
    return (
        f"Open Antigravity, start a NEW conversation with the folder `{project}` as workspace, and paste:\n\n"
        f"---\n"
        f"Read the request file `{request.resolve()}` and {what}.\n"
        f"When finished, write your report as a single JSON file to `{response.resolve()}` "
        f"(fields: message_id='{mid}-R', in_reply_to='{mid}', task_id, type, prompt_id, status [SUCCESS|FAILED|BLOCKED|NEEDS_CLARIFICATION], "
        f"agent, files_changed, commands_run, tests_run, tests_passed, tests_failed, test_output_excerpt, errors, "
        f"warnings, git_diff_summary, summary, timestamp).\n"
        f"Only modify files the prompt allows. Do not claim success without command output. "
        f"If anything is ambiguous, set status NEEDS_CLARIFICATION instead of guessing.\n"
        f"---"
    )


def cmd_send(a):
    task_dir = Path(a.task_dir).resolve()
    prompt = Path(a.prompt_file).resolve()
    if not prompt.is_file():
        sys.exit(f"prompt file not found: {prompt}")
    root = project_root_for(task_dir)
    cdir = comm_dir(task_dir)
    (cdir / "requests").mkdir(parents=True, exist_ok=True)
    (cdir / "responses").mkdir(parents=True, exist_ok=True)

    mid = next_message_id(task_dir)
    prompt_id = a.prompt_id or prompt.stem
    allowed = a.allowed or allowed_from_prompt(prompt)
    req_path = cdir / "requests" / f"{mid}.json"
    resp_path = cdir / "responses" / f"{mid}.json"
    kind = a.type or {"P": "IMPLEMENTATION_REQUEST", "R": "REGRESSION_REQUEST",
                      "C": "CORRECTIVE_REQUEST"}.get(prompt_id[:1].upper(), "IMPLEMENTATION_REQUEST")
    req = {
        "message_id": mid,
        "task_id": task_dir.name,
        "type": kind,
        "from": "claude",
        "to": "antigravity",
        "prompt_id": prompt_id,
        "priority": a.priority,
        "objective": a.objective or f"Execute {prompt_id} exactly as written.",
        "prompt_file": rel(root, prompt),
        "response_file": rel(root, resp_path),
        "context_file": rel(root, task_dir / "shared_context.md") if (task_dir / "shared_context.md").exists() else None,
        "allowed_files": allowed,
        "depends_on": a.depends_on or [],
        "timestamp": now(),
    }
    req_path.write_text(json.dumps(req, indent=2, ensure_ascii=False), encoding="utf-8")
    (cdir / "requests" / f"{mid}.snapshot.json").write_text(json.dumps(snapshot(root)), encoding="utf-8")
    keys = ("message_id", "task_id", "type", "prompt_id", "priority", "prompt_file", "response_file", "timestamp")
    append_bus(task_dir, dict({k: req[k] for k in keys}, channel=a.channel))
    print(json.dumps({"message_id": mid, "request_file": str(req_path), "response_file": str(resp_path),
                      "allowed_files": allowed}, indent=2))
    if not allowed:
        print("\nWARNING: no allowed files found (add a '## FILES YOU MAY MODIFY' section or pass --allowed); "
              "verify will flag every change.", file=sys.stderr)
    print("\n" + paste_text(root, req_path, resp_path, prompt, mid))


def cmd_handshake(a):
    root = Path(a.project).resolve()
    hs = root / ".shared" / "handshake"
    hs.mkdir(parents=True, exist_ok=True)
    mid = next_message_id(hs)
    req_path = hs / f"{mid}-request.json"
    resp_path = hs / f"{mid}-response.json"
    req = {
        "message_id": mid,
        "task_id": "SYSTEM-HANDSHAKE",
        "type": "HANDSHAKE_REQUEST",
        "from": "claude",
        "to": "antigravity",
        "objective": (f"Round-trip connectivity test. Create exactly one file: {rel(root, resp_path)} containing JSON "
                      f"with message_id='{mid}-R', in_reply_to='{mid}', type='HANDSHAKE_RESULT', status='SUCCESS', "
                      f"agent=<your agent and model name>, timestamp=<ISO-8601>. Modify nothing else."),
        "response_file": rel(root, resp_path),
        "allowed_files": [rel(root, resp_path)],
        "timestamp": now(),
    }
    req_path.write_text(json.dumps(req, indent=2), encoding="utf-8")
    (hs / f"{mid}.snapshot.json").write_text(json.dumps(snapshot(root)), encoding="utf-8")
    append_bus(hs, {"message_id": mid, "type": "HANDSHAKE_REQUEST", "response_file": req["response_file"],
                    "channel": a.channel, "timestamp": req["timestamp"]})
    print(json.dumps({"message_id": mid, "request_file": str(req_path), "response_file": str(resp_path),
                      "task_dir": str(hs)}, indent=2))
    print("\n" + paste_text(root, req_path, resp_path, None, mid))


def locate(task_dir: Path, mid: str):
    cdir = comm_dir(task_dir)
    for req, resp, snap in (
        (cdir / "requests" / f"{mid}.json", cdir / "responses" / f"{mid}.json", cdir / "requests" / f"{mid}.snapshot.json"),
        (task_dir / f"{mid}-request.json", task_dir / f"{mid}-response.json", task_dir / f"{mid}.snapshot.json"),
    ):
        if req.exists():
            return req, resp, snap
    sys.exit(f"request {mid} not found under {task_dir}")


def cmd_wait(a):
    task_dir = Path(a.task_dir).resolve()
    _, resp, _ = locate(task_dir, a.message_id)
    deadline = time.time() + a.timeout
    while time.time() < deadline:
        if resp.exists() and resp.stat().st_size > 0:
            time.sleep(2)  # let the writer finish
            print(f"ARRIVED: {resp}")
            print(resp.read_text(encoding="utf-8-sig", errors="replace"))
            return 0
        time.sleep(a.interval)
    print(f"TIMEOUT after {a.timeout}s: {resp} not found. Check the agent transcript before re-sending.")
    append_bus(task_dir, {"message_id": a.message_id, "type": "DELIVERY_RESULT", "status": "TIMEOUT",
                          "detail": f"no response after {a.timeout}s", "timestamp": now()})
    return 1


def cmd_verify(a):
    task_dir = Path(a.task_dir).resolve()
    req_path, resp, snap_path = locate(task_dir, a.message_id)
    root = project_root_for(task_dir)
    req = json.loads(req_path.read_text(encoding="utf-8"))
    issues, notes = [], []

    data = None
    if not resp.exists():
        issues.append(f"response file missing: {resp}")
    else:
        try:
            data = json.loads(resp.read_text(encoding="utf-8-sig"))
        except json.JSONDecodeError as e:
            issues.append(f"response is not valid JSON: {e}")
    if isinstance(data, dict):
        if data.get("in_reply_to") != a.message_id:
            issues.append(f"in_reply_to is {data.get('in_reply_to')!r}, expected {a.message_id!r}")
        status = str(data.get("status", "")).upper()
        if status not in STATUSES:
            issues.append(f"status {data.get('status')!r} not in {sorted(STATUSES)}")
        elif status != "SUCCESS":
            notes.append(f"agent reported status {status}")
        need = REQUIRED.get(req.get("type"), REQUIRED["_default"])
        for f in need:
            if f == "summary_or_output":
                if not (data.get("summary") or data.get("test_output_excerpt")):
                    issues.append("missing summary / test_output_excerpt")
            elif f not in data:
                issues.append(f"missing field: {f}")
        if req.get("type") != "HANDSHAKE_REQUEST" and status == "SUCCESS":
            if not data.get("commands_run"):
                issues.append("SUCCESS claimed but commands_run is empty (no evidence)")
            if not (data.get("test_output_excerpt") or data.get("tests_passed")):
                issues.append("SUCCESS claimed without test output")
    elif data is not None:
        issues.append("response JSON is not an object")

    changed, added, deleted = [], [], []
    if snap_path.exists():
        before = json.loads(snap_path.read_text(encoding="utf-8"))
        after = snapshot(root)
        added = sorted(set(after) - set(before))
        deleted = sorted(set(before) - set(after))
        changed = sorted(k for k in set(after) & set(before) if after[k] != before[k])
    else:
        notes.append("no snapshot found; scope check skipped")

    allowed = list(req.get("allowed_files") or [])
    own = {rel(root, resp), rel(root, bus_path(task_dir)), rel(root, req_path), rel(root, snap_path)}
    task_rel = rel(root, task_dir)
    out_of_scope = []
    for f in changed + added + deleted:
        if f in own:
            continue
        if any(fnmatch.fnmatch(f, g) or f == g.rstrip("/") or f.startswith(g.rstrip("/") + "/") for g in allowed):
            continue
        # Claude's own bookkeeping inside the task folder is reported separately, not as agent drift
        if f.startswith(task_rel + "/") and not f.startswith(task_rel + "/communication/responses/"):
            notes.append(f"task-folder change (likely Claude bookkeeping): {f}")
            continue
        out_of_scope.append(f)
    if out_of_scope:
        issues.append(f"{len(out_of_scope)} change(s) outside allowed files")

    result = {
        "message_id": a.message_id,
        "verdict": "CLEAN" if not issues else "ISSUES",
        "issues": issues,
        "notes": notes,
        "allowed_files": allowed,
        "changed": changed, "added": added, "deleted": deleted,
        "out_of_scope": out_of_scope,
        "reminder": "This is a mechanical check. Re-run tests and read the git diff yourself before APPROVED.",
    }
    print(json.dumps(result, indent=2))
    append_bus(task_dir, {"message_id": a.message_id, "type": "VERIFY_RESULT", "verdict": result["verdict"],
                          "issues": issues, "out_of_scope": out_of_scope, "timestamp": now()})
    return 0 if not issues else 2


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)

    s = sub.add_parser("send")
    s.add_argument("--task-dir", required=True)
    s.add_argument("--prompt-file", required=True)
    s.add_argument("--prompt-id")
    s.add_argument("--type", help="default inferred from prompt id: P→IMPLEMENTATION, R→REGRESSION, C→CORRECTIVE")
    s.add_argument("--objective")
    s.add_argument("--priority", default="NORMAL", choices=["LOW", "NORMAL", "HIGH"])
    s.add_argument("--allowed", nargs="*", help="allowed paths/globs (default: parsed from the prompt)")
    s.add_argument("--depends-on", nargs="*")
    s.add_argument("--channel", default="antigravity-app (human-started conversation)")

    h = sub.add_parser("handshake")
    h.add_argument("--project", default=".")
    h.add_argument("--channel", default="antigravity-app (human-started conversation)")

    w = sub.add_parser("wait")
    w.add_argument("--task-dir", required=True)
    w.add_argument("--message-id", required=True)
    w.add_argument("--timeout", type=int, default=900)
    w.add_argument("--interval", type=int, default=5)

    v = sub.add_parser("verify")
    v.add_argument("--task-dir", required=True)
    v.add_argument("--message-id", required=True)

    a = ap.parse_args()
    rc = {"send": cmd_send, "handshake": cmd_handshake, "wait": cmd_wait, "verify": cmd_verify}[a.cmd](a)
    sys.exit(rc or 0)


if __name__ == "__main__":
    main()
