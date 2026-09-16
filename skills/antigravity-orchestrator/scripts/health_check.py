#!/usr/bin/env python3
"""Report-only health check for the orchestrator (a Python stand-in for `orchestrator-launcher.exe --check`).

It never installs, starts or stops anything. It writes <project>/.shared/system_status.json
and exits 0 if all required components are healthy, 1 otherwise.

Usage:
  python health_check.py --project . [--init] [--config orchestrator.config.json]

--init creates TASKS/, .shared/{skills/installed,skills/recommended,logs,research,handshake},
and registry files if they are missing (it never overwrites them).
"""
import argparse
import json
import os
import platform
import re
import shutil
import subprocess
import sys
from datetime import datetime
from pathlib import Path

HOME = Path.home()
WIN = platform.system() == "Windows"

DEFAULT_COMPONENTS = [
    {"name": "Claude Code", "kind": "cli", "required": True,
     "executable_candidates": ["claude", "%APPDATA%\\npm\\claude.cmd", "%USERPROFILE%\\.local\\bin\\claude.exe"],
     "check_args": ["--version"]},
    {"name": "Gemini CLI", "kind": "cli", "required": True,
     "executable_candidates": ["gemini", "%APPDATA%\\npm\\gemini.cmd"],
     "check_args": ["--version"],
     "auth_env": ["GEMINI_API_KEY", "GOOGLE_API_KEY", "GOOGLE_CLOUD_PROJECT"],
     "auth_files": ["%USERPROFILE%\\.gemini\\oauth_creds.json", "~/.gemini/oauth_creds.json"]},
    {"name": "Antigravity", "kind": "app", "required": True,
     "executable_candidates": ["%LOCALAPPDATA%\\Programs\\Antigravity\\Antigravity.exe",
                               "%ProgramFiles%\\Antigravity\\Antigravity.exe",
                               "/Applications/Antigravity.app", "antigravity"],
     "process_names": ["Antigravity.exe", "Antigravity"]},
]

REGISTRY = ("# Skill / Tool Registry\n\n| Name | Purpose | Source | Version | Install method | Config location | "
            "Why needed | Alternatives | Compatibility | Security | Used by | Installed? |\n"
            "|---|---|---|---|---|---|---|---|---|---|---|---|\n")


def now():
    return datetime.now().astimezone().isoformat(timespec="seconds")


def expand(s):
    s = re.sub(r"%([A-Za-z0-9_]+)%", lambda m: os.environ.get(m.group(1), ""), s)
    return os.path.expanduser(os.path.expandvars(s))


def find_exe(cands):
    for c in cands:
        p = expand(c)
        if not p or p.startswith("\\") or "%" in c and not p.strip("\\/"):
            continue
        if os.path.isabs(p):
            if os.path.exists(p):
                return p
            continue
        # On Windows, npm installs an extensionless sh script next to the .cmd shim; prefer runnable extensions.
        names = [p + ext for ext in (".exe", ".cmd", ".bat")] + [p] if WIN and not os.path.splitext(p)[1] else [p]
        for n in names:
            found = shutil.which(n)
            if found:
                return found
    return None


def run(exe, args, timeout=60):
    cmd = [exe, *args]
    if WIN and exe.lower().endswith((".cmd", ".bat", ".ps1")):
        base = os.path.splitext(exe)[0]
        shim = base + ".cmd" if os.path.exists(base + ".cmd") else exe
        cmd = ["cmd", "/c", shim, *args]
    r = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
    return r.returncode, (r.stdout + r.stderr).strip()


def process_running(names):
    for n in names:
        try:
            if WIN:
                out = subprocess.run(["tasklist", "/FI", f"IMAGENAME eq {n}", "/NH", "/FO", "CSV"],
                                     capture_output=True, text=True, timeout=20).stdout
                if n.lower() in out.lower():
                    return True
            else:
                if subprocess.run(["pgrep", "-x", n.removesuffix(".exe")], capture_output=True).returncode == 0:
                    return True
        except (OSError, subprocess.TimeoutExpired):
            pass
    return False


def check(c):
    r = {"name": c["name"], "kind": c.get("kind", "cli"), "required": c.get("required", True),
         "installed": False, "running": False, "authorized": True, "healthy": False,
         "executable": None, "action": "none", "detail": ""}
    exe = find_exe(c.get("executable_candidates", []))
    if not exe:
        r["detail"] = "not installed / not found"
        return r
    r["installed"], r["executable"] = True, exe

    if c.get("auth_env") or c.get("auth_files"):
        env_hit = next((e for e in c.get("auth_env", []) if os.environ.get(e)), None)
        file_hit = next((f for f in c.get("auth_files", []) if expand(f) and os.path.exists(expand(f))), None)
        r["authorized"] = bool(env_hit or file_hit)

    if r["kind"] == "app":
        r["running"] = process_running(c.get("process_names", []))
        if not r["running"]:
            r["detail"] = "installed but not running (start it manually; this check never starts apps)"
    else:
        try:
            rc, out = run(exe, c.get("check_args", ["--version"]))
            r["running"] = rc == 0
            r["detail"] = (out.splitlines() or [""])[-1][:200] if rc == 0 else f"health check failed ({rc}): {out[-200:]}"
        except (OSError, subprocess.TimeoutExpired) as e:
            r["detail"] = f"health check failed: {e}"
    if not r["authorized"]:
        r["detail"] = (r["detail"] + "; " if r["detail"] else "") + \
            f"no credentials: set one of {c.get('auth_env')} or sign in once interactively"
    r["healthy"] = r["installed"] and r["running"] and r["authorized"]
    return r


def extras():
    """Informational: alternative delegation channels (don't affect health)."""
    agentapi = HOME / ".gemini" / "antigravity" / "bin" / ("agentapi.bat" if WIN else "agentapi")
    return {
        "antigravity_ide_cli": find_exe(["antigravity-ide"]),
        "agentapi": str(agentapi) if agentapi.exists() else None,
        "agentapi_env_ready": bool(os.environ.get("ANTIGRAVITY_LS_ADDRESS") and os.environ.get("ANTIGRAVITY_CSRF_TOKEN")),
        "antigravity_ide_running": process_running(["Antigravity IDE.exe", "Antigravity IDE"]),
        "antigravity_transcripts_dir": str(HOME / ".gemini" / "antigravity" / "brain")
        if (HOME / ".gemini" / "antigravity" / "brain").is_dir() else None,
    }


def init(project):
    for d in ["TASKS", ".shared/skills/installed", ".shared/skills/recommended", ".shared/logs",
              ".shared/research", ".shared/handshake"]:
        (project / d).mkdir(parents=True, exist_ok=True)
    files = {
        ".shared/skills/registry.md": REGISTRY,
        ".shared/agents.md": "# Agent Capability Registry\n\n| Agent | Role | Capabilities | Status | Detail |\n"
                             "|---|---|---|---|---|\n| Claude | Architect | Architecture, decomposition, review | Available | |\n"
                             "| Antigravity | Orchestrator | Swarm coordination, routing | See system_status.json | |\n"
                             "| Gemini | Implementer | Coding, tests, debugging | See system_status.json | |\n",
        ".shared/research/integration.md": "# Integration Discovery\n\nRecord how each agent is actually reached "
                                           "(channel, command, verified date, evidence). Never invent endpoints.\n",
    }
    for rel, body in files.items():
        p = project / rel
        if not p.exists():
            p.write_text(body, encoding="utf-8")


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--project", default=".")
    ap.add_argument("--init", action="store_true")
    ap.add_argument("--config", help="orchestrator.config.json (default: <project>/orchestrator.config.json if present)")
    a = ap.parse_args()
    project = Path(a.project).resolve()
    if a.init:
        init(project)

    comps = DEFAULT_COMPONENTS
    cfg_path = Path(a.config) if a.config else project / "orchestrator.config.json"
    if cfg_path.exists():
        try:
            comps = json.loads(cfg_path.read_text(encoding="utf-8")).get("components") or comps
        except json.JSONDecodeError as e:
            print(f"warning: {cfg_path} invalid JSON ({e}); using defaults", file=sys.stderr)

    results = [check(c) for c in comps]
    status = {"timestamp": now(), "project_dir": str(project), "source": "health_check.py (report-only)",
              "healthy": all(r["healthy"] for r in results if r["required"]),
              "components": results, "extras": extras()}
    out = project / ".shared" / "system_status.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(status, indent=2), encoding="utf-8")

    for r in results:
        print(f"[{'OK ' if r['healthy'] else 'BAD'}] {r['name']}: {r['detail'] or r['executable']}")
    print("extras:", json.dumps(status["extras"]))
    print(f"SYSTEM {'UP' if status['healthy'] else 'DEGRADED'}; wrote {out}")
    sys.exit(0 if status["healthy"] else 1)


if __name__ == "__main__":
    main()
