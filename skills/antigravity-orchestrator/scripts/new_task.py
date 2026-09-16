#!/usr/bin/env python3
"""Create a new orchestrator task: ID, folder tree, STATUS.md, shared_context.md, logs.

Usage:
  python new_task.py --project . --title "Add input validation" [--tier S|M|L] [--branch]

Prints JSON: {"task_id", "task_dir", "branch", "branch_created"}
"""
import argparse
import json
import secrets
import subprocess
import sys
from datetime import datetime
from pathlib import Path

DIRS = [
    "prompts/implementation", "prompts/regression", "prompts/corrective",
    "tests", "research", "communication/requests", "communication/responses",
    "decisions", "logs", "reports",
]

STUBS = {
    "00_project_context.md": "# Project Context\n\nProject · Repository · Detected stack · Architecture · Important modules\n"
                             "External services · Build system · Testing system · Potential risks\n"
                             "Unknowns (mark UNKNOWN + how to resolve) · Technical debt · Conventions\n"
                             "Current Git state · Relevant files\n",
    "01_problem_definition.md": "# Problem Definition\n",
    "02_requirements.md": "# Requirements\n\n## Functional\n\n## Non-functional\n\n## Acceptance criteria (measurable)\n",
    "03_architecture.md": "# Architecture\n\nComponents · Responsibilities · Interfaces · Dependencies · Data flow · Control flow\n"
                          "Failure boundaries · Security boundaries · State · Observability · Testing strategy · Performance\n",
    "04_task_breakdown.md": "# Task Breakdown\n\n| Prompt | Scope | Depends on | Regression prompt | Status |\n|---|---|---|---|---|\n",
    "tests/regression_matrix.md": "# Regression Matrix\n\n| Test ID | Feature | Type | Status | Evidence | Failure | Related Prompt |\n|---|---|---|---|---|---|---|\n",
    "tests/acceptance_tests.md": "# Acceptance Tests\n",
    "tests/test_results.md": "# Test Results\n\nRecord command, full result line, date, and who ran it.\n",
    "research/sources.md": "# Sources\n\n| Claim | Source | Date accessed | Why relevant | Impact |\n|---|---|---|---|---|\n",
    "research/skills.md": "# Skills / Tools Considered\n",
    "research/technical_findings.md": "# Technical Findings\n",
    "reports/implementation_report.md": "# Implementation Report\n\nAppend one review note per agent response.\n",
    "reports/regression_report.md": "# Regression Report\n",
    "logs/errors.log": "",
    "communication/message_bus.jsonl": "",
}


def now():
    return datetime.now().astimezone().isoformat(timespec="seconds")


def git(project, *args):
    try:
        r = subprocess.run(["git", *args], cwd=project, capture_output=True, text=True, timeout=30)
        return r.returncode, r.stdout.strip(), r.stderr.strip()
    except (OSError, subprocess.TimeoutExpired) as e:
        return 1, "", str(e)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--project", default=".", help="project root (default: .)")
    ap.add_argument("--title", required=True, help="one-line objective")
    ap.add_argument("--tier", default="M", choices=["S", "M", "L"])
    ap.add_argument("--branch", action="store_true", help="also create and switch to git branch task/<ID>")
    a = ap.parse_args()

    project = Path(a.project).resolve()
    if not project.is_dir():
        sys.exit(f"project dir not found: {project}")

    stamp = datetime.now().strftime("%Y%m%d-%H%M")
    tasks = project / "TASKS"
    while True:
        task_id = f"TASK-{stamp}-{secrets.token_hex(2).upper()}"
        task_dir = tasks / task_id
        if not task_dir.exists():
            break
    for d in DIRS:
        (task_dir / d).mkdir(parents=True, exist_ok=True)
    for rel, body in STUBS.items():
        (task_dir / rel).write_text(body, encoding="utf-8")

    rc, head, _ = git(project, "rev-parse", "--short", "HEAD")
    _, branch_now, _ = git(project, "branch", "--show-current")
    baseline = head if rc == 0 else "UNKNOWN (no commits or not a git repo)"
    branch = f"task/{task_id}"

    (task_dir / "STATUS.md").write_text(
        f"""# Task Status
Task: {task_id}      Tier: {a.tier}
## Objective:      {a.title}
## Current Phase:   DISCOVERY
## Current Prompt:  -
## Agent:           Claude
## Overall Status:  IN_PROGRESS
## Completed:       -
## Active:          -
## Pending:         -
## Test Status:     not run
## Corrective Iterations: 0 of 3
## Baseline Commit: {baseline} (branch at creation: {branch_now or 'UNKNOWN'})
## Blocking Issues: none
## Next Action:     Inspect project → 00_project_context.md
""", encoding="utf-8")

    (task_dir / "shared_context.md").write_text(
        f"""# Shared Context · {task_id}

## Task objective
{a.title}

## Current architecture
## Current state
DISCOVERY
## Relevant files
## Constraints
## Decisions
## Active prompt
## Acceptance criteria
## Known failures
## Latest test results
## Implementation status
## Agent responsibilities
| Agent | Responsibility |
|---|---|
| Claude | Architecture, prompts, review, sign-off |
| Antigravity/Gemini | Implementation and evidence, only within each prompt's allowed files |
""", encoding="utf-8")

    line = f"{now()} | {task_id} | CLAUDE | TASK_CREATED | SUCCESS | tier={a.tier}; title={a.title}\n"
    for log in ("execution.log", "audit.log"):
        (task_dir / "logs" / log).write_text(line, encoding="utf-8")

    created = False
    if a.branch:
        rc, _, err = git(project, "checkout", "-b", branch)
        created = rc == 0
        if not created:
            print(f"warning: could not create branch {branch}: {err}", file=sys.stderr)

    print(json.dumps({"task_id": task_id, "task_dir": str(task_dir), "branch": branch,
                      "branch_created": created}, indent=2))


if __name__ == "__main__":
    main()
