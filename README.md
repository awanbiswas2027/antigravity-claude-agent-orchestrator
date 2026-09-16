# Antigravity-Claude Agent Orchestrator

[![Go Version](https://img.shields.io/badge/Go-1.24+-00ADD8?style=flat&logo=go)](https://golang.org/)
[![Python Version](https://img.shields.io/badge/Python-3.9+-3776AB?style=flat&logo=python)](https://python.org/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Platform](https://img.shields.io/badge/Platform-Windows%20%7C%20Cross--Platform-blue)](#)
[![Architecture](https://img.shields.io/badge/Architecture-Hierarchical%20%26%20Stigmergic%20Swarm-8A2BE2)](#agent-hierarchy)

An autonomous software engineering framework and multi-agent operating system pairing **Claude Code** (Principal Architect, Technical Program Manager, QA Gatekeeper) with **Google Antigravity** and **Gemini** (Implementation Engines and Swarm Workers) through a resilient, auditable, file-based message bus.

---

## Table of Contents

- [The Philosophy: Disciplined Engineering](#the-philosophy-disciplined-engineering)
- [Agent Hierarchy & Architecture](#agent-hierarchy--architecture)
- [Key Features](#key-features)
- [Repository Structure](#repository-structure)
- [Prerequisites](#prerequisites)
- [Quick Start](#quick-start)
- [Launcher Modes & CLI](#launcher-modes--cli)
- [The Engineering Lifecycle](#the-engineering-lifecycle)
- [Task Management & File-Based Message Bus](#task-management--file-based-message-bus)
- [Ant Colony Swarm (Stigmergy Mode)](#ant-colony-swarm-stigmergy-mode)
- [Antigravity Skill Integration](#antigravity-skill-integration)
- [Configuration Reference](#configuration-reference)
- [Troubleshooting & Best Practices](#troubleshooting--best-practices)
- [Contributing & Building from Source](#contributing--building-from-source)
- [License](#license)

---

## The Philosophy: Disciplined Engineering

Most autonomous coding agents fail for three predictable reasons:
1. **Ambiguous specifications:** Prompts are vague, leading models to guess requirements and architectural boundaries.
2. **Hallucinated completion:** Agents produce eloquent reports claiming success without concrete, reproducible test evidence.
3. **Collateral breakage:** Local changes quietly break distant modules because no regression boundary was enforced.

**Antigravity-Claude Agent Orchestrator** treats AI software development like a high-reliability engineering organization:

```text
OBSERVE ──► UNDERSTAND ──► RESEARCH ──► ARCHITECT ──► DECOMPOSE
   ▲                                                       │
   │                                                       ▼
 CLOSE ◄── VERIFY ◄── REGRESSION TEST ◄── FIX ◄── REVIEW ◄── DELEGATE / IMPLEMENT
```

> **Priority Hierarchy:**  
> **Safety & Human Approval** > **Correctness & Evidence** > **Architectural Integrity** > **Speed**

---

## Agent Hierarchy & Architecture

The framework decouples high-level strategic reasoning and architecture from low-level code implementation:

```text
                    ┌──────────────────────────────────────────────┐
                    │                 CLAUDE CODE                  │
                    │   Principal Architect · QA Gatekeeper · TPM  │
                    └──────────────────────┬───────────────────────┘
                                           │
                          Architecture, Task Breakdown,
                         Strict Prompts & Acceptance Gates
                                           ▼
                    ┌──────────────────────────────────────────────┐
                    │               GOOGLE ANTIGRAVITY             │
                    │        Execution Hub & Swarm Coordinator     │
                    └──────────────┬───────────────┬───────────────┘
                                   │               │
                        Task Routing & Dispatch    │
                                   ▼               ▼
                        ┌────────────────────┐ ┌────────────────────┐
                        │     GEMINI CLI     │ │ ANTIGRAVITY AGENTS │
                        │  (Headless Engine) │ │ (Interactive Swarm)│
                        └────────────────────┘ └────────────────────┘
                                   │                      │
                                   └──────────┬───────────┘
                                              │
                                    Produces Code, Diffs,
                                   Logs & Verifiable Evidence
                                              ▼
                                 [ File-Based Audit Trail ]
                                  .shared/ & TASKS/<ID>/
```

### Roles & Responsibilities

| Agent / Layer | Primary Role | Core Responsibilities |
|---|---|---|
| **Claude Code** | Principal Architect & QA Authority | Repo inspection, architecture design, task decomposition, prompt engineering, diff review, final sign-off. |
| **Google Antigravity** | Execution Coordinator | Process lifecycle management, subagent routing, execution sandboxing, and transcript logging. |
| **Gemini (CLI / Antigravity)** | Implementation Engine | Writing code, running builds, authoring unit tests, debugging, and providing execution logs as proof. |
| **Human in the Loop** | Executive Authority | Setting task goals, approving high-risk actions, providing credentials, and conducting milestone reviews. |

---

## Key Features

- **Decoupled Architecture**: Claude handles the thinking, decomposition, and review; Gemini/Antigravity handles execution and tests.
- **Resilient File-Based Message Bus**: Asynchronous, transparent communication using `.shared/` and `TASKS/<ID>/` JSON message payloads and `.jsonl` audit streams. State persists through system reboots, network interruptions, and CLI restarts.
- **Go Orchestrator Launcher (`orchestrator-launcher.exe`)**: A single lightweight native supervisor binary that verifies dependencies, launches Antigravity, auto-installs missing CLI dependencies, and boots Claude Code with the master prompt.
- **Stigmergic Swarm Mode (Ant Colony Swarm v1)**: Autonomous multi-agent coordination modeled after ant colonies. Specialized castes (*Queen, Scout, Worker, Soldier, Nurse, Midden, Forager*) coordinate via a shared pheromone board (`.colony/pheromones.jsonl`) with claim locks, evaporative decay, and hard budget controls.
- **Evidence-Based Quality Gates**: Zero code merged without passing test outputs, command logs, and diff verification against allowed scope boundaries.
- **Three-Tier Task Sizing**:
  - **Tier S** (Small fixes, config changes): Streamlined single prompt, fast verification.
  - **Tier M** (New endpoints, modular features): Full task directory, regression prompt, and matrix tracking.
  - **Tier L** (Subsystems, architectural changes): Comprehensive architecture blueprints (`03_architecture.md`), ADRs (Architectural Decision Records), and full regression test suites.
- **Anti-Scope Drift Engine**: Snapshot-based diff checks (`python delegate.py verify`) that automatically catch agents modifying files outside designated boundaries.
- **Drop-in Antigravity Skill**: Ships as a fully self-contained skill in `skills/antigravity-orchestrator/` with Python automation scripts (`delegate.py`, `new_task.py`, `health_check.py`).

---

## Repository Structure

```text
antigravity-claude-agent-aurchestrator/
├── autonomous_software_engineering_orchestrator.md  # Master system operating prompt (v2)
├── orchestrator.config.json                         # System component & launcher configuration
├── orchestrator-launcher.exe                        # Native supervisor binary (Go)
├── source/                                          # Go source code for the launcher
│   ├── go.mod
│   └── main.go
├── skills/
│   └── antigravity-orchestrator/                    # Portable Antigravity skill package
│       ├── SKILL.md                                 # Skill specification & activation rules
│       ├── scripts/                                 # Automation tools (Python 3.9+)
│       │   ├── delegate.py                          # Message bus send, wait, verify & handshake
│       │   ├── health_check.py                      # Standalone system diagnostic tool
│       │   └── new_task.py                          # Task scaffolding & branch generator
│       └── references/                              # Deep-dive operating guides
│           ├── antigravity.md                       # Antigravity integration & IPC protocols
│           ├── bring-up.md                          # Health check & auto-recovery rules
│           ├── master-prompt.md                     # Full master prompt reference
│           └── templates.md                         # Standardized prompt & test templates
├── .colony/                                         # Stigmergic Ant Colony Swarm state
│   ├── colony.md                                    # Colony charter, budgets & caste ratios
│   ├── pheromones.jsonl                             # Live pheromone signal board
│   ├── nest_status.md                               # Swarm operational status
│   └── claims.json                                  # Active task claims and locks
├── .shared/                                         # Global workspace memory & bus
│   ├── system_status.json                           # Live component health telemetry
│   ├── agents.md                                    # Capability registry
│   ├── handshake/                                   # Inter-agent connectivity tests
│   └── logs/startup.log                             # Launcher audit logs
└── TASKS/                                           # Individual task audit folders
    └── TASK-<YYYYMMDD>-<HHMM>-<HASH>/
        ├── STATUS.md                                # Live phase & progress tracking
        ├── 00_project_context.md                    # Verified codebase context
        ├── 02_requirements.md                       # Measurable acceptance criteria
        ├── 04_task_breakdown.md                     # Dependency graph
        ├── communication/                           # Message bus requests & responses
        │   ├── requests/
        │   ├── responses/
        │   └── message_bus.jsonl
        ├── prompts/                                 # P00N (implementation) & R00N (regression)
        ├── reports/                                 # Execution & regression evidence
        └── tests/                                   # Regression matrix & results
```

---

## Prerequisites

1. **Node.js (v18+)**: Required for hosting the CLI tools.
2. **Claude Code**:
   ```bash
   npm install -g @anthropic-ai/claude-code
   ```
3. **Google Antigravity & Gemini CLI**:
   - Install the **Google Antigravity** desktop app hub.
   - Install the Gemini CLI:
     ```bash
     npm install -g @google/gemini-cli
     ```
   - Configure Gemini authentication: set the `GEMINI_API_KEY` environment variable, or sign in once via `gemini`. *(Note: Antigravity agents use the desktop application's built-in Google session, so Antigravity delegation works even if Gemini CLI is unauthenticated!)*
4. **Python (3.9+)**: Required for running the skill scripts (`delegate.py`, `new_task.py`, `health_check.py`).
5. **Go (1.24+)** *(Optional)*: Only required if compiling `orchestrator-launcher.exe` from source.

---

## Quick Start

### 1. Configure the Project
Clone this repository into your project root (or copy its files into your target workspace):

```bash
git clone https://github.com/awanbiswas2027/antigravity-claude-agent-aurchestrator.git .
```

Review `orchestrator.config.json`. By default, it looks for Claude Code, Gemini CLI, and Antigravity.

### 2. Boot the Orchestration Environment

#### Option A: Native Launcher (Recommended)
Double-click `orchestrator-launcher.exe` or run from your terminal:

```powershell
.\orchestrator-launcher.exe
```

This will:
1. Verify required folders (`.shared/`, `TASKS/`, logs, and registries).
2. Run health checks against Claude Code, Gemini CLI, and Antigravity.
3. Automatically install missing npm packages if enabled (`auto_install: true`).
4. Boot Antigravity if it is not running.
5. Write the health report to `.shared/system_status.json`.
6. Open a dedicated Claude Code window preloaded with `autonomous_software_engineering_orchestrator.md`.

> *Windows SmartScreen Note:* Because `orchestrator-launcher.exe` is self-compiled and unsigned, Windows SmartScreen may display a warning. Click **"More info"** &rarr; **"Run anyway"**. You can inspect and rebuild the binary anytime from `source/main.go`.

#### Option B: Python Standalone
If you prefer not to use the Go binary:

```bash
python skills/antigravity-orchestrator/scripts/health_check.py --project . --init
```

---

## Launcher Modes & CLI

The Go launcher supports several operating modes:

```bash
# Standard Launch: Ensures health, starts Antigravity, and launches Claude Code
orchestrator-launcher.exe

# Ensure: Starts/installs missing components without opening a Claude terminal (exit 0 = healthy)
orchestrator-launcher.exe --ensure

# Check: Diagnostics report only; does not start or install anything
orchestrator-launcher.exe --check

# Watchdog: Runs continuously, verifying and reviving stopped components every 60s
orchestrator-launcher.exe --watch 60
```

---

## The Engineering Lifecycle

Every piece of non-trivial work proceeds through explicit, auditable phases:

```text
[ OBSERVE ] ── Inspect repository, existing patterns, and test suites.
     │
[ ARCHITECT ] ── Identify blast radius, write 03_architecture.md, record ADRs.
     │
[ DECOMPOSE ] ── Break into verifiable units (P001, P002...).
     │
[ PROMPT ] ── Author implementation prompt (P00N) and regression prompt (R00N).
     │
[ DELEGATE ] ── Dispatch to Gemini via Antigravity using delegate.py.
     │
[ VERIFY ] ── Inspect changed files against allowable scope, review test evidence.
     │
[ CLOSE ] ── Run full regression suite, merge branch, sign off in STATUS.md.
```

### Prompt Numbering Convention
- `P001`, `P002`, ...: Implementation prompts.
- `R001`, `R002`, ...: Regression test prompts.
- `C001`, `C002`, ...: Corrective prompts (for failed reviews).
- `P001-v1`, `P001-v2`: Prompt versions (never overwrite an earlier prompt; preserves the audit trail).

---

## Task Management & File-Based Message Bus

### Creating a New Task
Use `new_task.py` to scaffold an isolated task environment and git branch:

```bash
python skills/antigravity-orchestrator/scripts/new_task.py \
  --project . \
  --title "Add rate limiting to authentication routes" \
  --tier M \
  --branch
```

This outputs:
```json
{
  "task_id": "TASK-20260916-2315-E4B2",
  "task_dir": "TASKS/TASK-20260916-2315-E4B2",
  "branch": "task/TASK-20260916-2315-E4B2",
  "branch_created": true
}
```

### Delegating to Google Antigravity
1. **Send the Request:**
   ```bash
   python skills/antigravity-orchestrator/scripts/delegate.py send \
     --task-dir TASKS/TASK-20260916-2315-E4B2 \
     --prompt-file TASKS/TASK-20260916-2315-E4B2/prompts/implementation/P001-v1.md
   ```
   *This snapshots git status, writes `communication/requests/MSG-0001.json`, and outputs the paste-ready prompt for Antigravity.*

2. **Execute in Antigravity:**
   Open Antigravity, start a conversation in the project, and paste the prompt. The Antigravity agent executes the instructions and writes `communication/responses/MSG-0001.json`.

3. **Wait for Completion:**
   ```bash
   python skills/antigravity-orchestrator/scripts/delegate.py wait \
     --task-dir TASKS/TASK-20260916-2315-E4B2 \
     --message-id MSG-0001 \
     --timeout 900
   ```

4. **Verify Scope & Results:**
   ```bash
   python skills/antigravity-orchestrator/scripts/delegate.py verify \
     --task-dir TASKS/TASK-20260916-2315-E4B2 \
     --message-id MSG-0001
   ```
   *Verifies that required response schema fields exist and flags any modified file not explicitly permitted in `FILES YOU MAY MODIFY`.*

---

## Ant Colony Swarm (Stigmergy Mode)

The repository includes the **Ant Colony Agent Swarm** protocol (`.colony/` & `v2/.../ant_colony_agents.md`), an autonomous stigmergic coordination system inspired by social insects. Rather than relying on rigid top-down management, agents coordinate asynchronously through a shared environmental blackboard.

```text
                     ┌───────────────────────┐
                     │   QUEEN  (Claude)     │  Goals · Architecture · Spawning · Final Review
                     └──────────┬────────────┘
                                │ Lays tasks ("food") & enforces budgets
                     ┌──────────▼────────────┐
                     │  NEST  (Antigravity)  │  Routes agents · Heartbeats · Claim locks
                     └──────────┬────────────┘
        ┌──────────┬────────────┼───────────┬────────────┬────────────┐
        ▼          ▼            ▼           ▼            ▼            ▼
     SCOUTS     WORKERS      SOLDIERS     NURSES       MIDDEN      FORAGERS
   (explore)   (implement)  (guard/QA)  (tests/docs)  (cleanup)   (research)
        │          │            │           │            │            │
        └──────────┴──── Read / Write ──────┴────────────┴────────────┘
                     .colony/pheromones.jsonl  (Pheromone Trail Board)
```

### Colony Castes

- **Queen (Claude)**: Master architect, sets budgets, decomposes goals into `FOOD` signals, signs off on PRs.
- **Scouts (Gemini/Claude)**: Explore unknown code, map dependencies, emit `FOOD` or `DANGER` pheromones.
- **Workers (Gemini / Antigravity)**: Claim `FOOD` signals and implement features inside isolated branches.
- **Soldiers (Claude/Gemini)**: Run regression and security checks; block pull requests with `DANGER` flags.
- **Nurses (Gemini)**: Write unit tests, strengthen regression matrices, and document changes.
- **Midden (Gemini)**: Perform safe refactoring, delete dead code, and fix lint errors.
- **Foragers (Claude)**: Research external dependencies, APIs, and add new skills.

### Pheromone Types
- `FOOD`: Available work waiting for a worker to claim.
- `TRAIL`: Progress signals along an active task.
- `DANGER`: Flagged bugs, regressions, or security concerns.
- `RETIRED`: Completed tasks and archived work.

---

## Antigravity Skill Integration

This repository is formatted as a native **Google Antigravity Skill**.

To install it into your global Antigravity configuration:
1. Copy `skills/antigravity-orchestrator/` into your Antigravity skills directory:
   - **Windows:** `%USERPROFILE%\.gemini\antigravity\skills\`
   - **macOS/Linux:** `~/.gemini/antigravity/skills/`
2. Antigravity will automatically detect `SKILL.md` and make orchestrator tooling available across all workspaces.

---

## Configuration Reference

The behavior of the orchestrator is controlled via `orchestrator.config.json`:

```json
{
  "project_dir": "",
  "prompt_file": "autonomous_software_engineering_orchestrator.md",
  "startup_timeout_seconds": 60,
  "max_start_attempts": 3,
  "auto_install": true,
  "launch_claude": true,
  "claude_startup_prompt": "Read {prompt_file} in this folder and adopt it as your operating instructions. Then run the Startup Procedure, starting with System Bring-Up (orchestrator-launcher.exe --ensure), and report system status.",
  "components": [
    {
      "name": "Claude Code",
      "kind": "cli",
      "required": true,
      "executable_candidates": ["claude", "%APPDATA%\\npm\\claude.cmd"],
      "check_args": ["--version"],
      "install_command": ["npm", "install", "-g", "@anthropic-ai/claude-code"]
    },
    {
      "name": "Gemini CLI",
      "kind": "cli",
      "required": true,
      "executable_candidates": ["gemini", "%APPDATA%\\npm\\gemini.cmd"],
      "check_args": ["--version"],
      "install_command": ["npm", "install", "-g", "@google/gemini-cli"],
      "auth_env": ["GEMINI_API_KEY", "GOOGLE_API_KEY", "GOOGLE_CLOUD_PROJECT"],
      "auth_files": ["%USERPROFILE%\\.gemini\\oauth_creds.json"]
    },
    {
      "name": "Antigravity",
      "kind": "app",
      "required": true,
      "executable_candidates": [
        "%LOCALAPPDATA%\\Programs\\Antigravity\\Antigravity.exe",
        "%ProgramFiles%\\Antigravity\\Antigravity.exe"
      ],
      "process_names": ["Antigravity.exe"],
      "start_args": ["{project_dir}"]
    }
  ]
}
```

---

## Troubleshooting & Best Practices

### 1. Gemini CLI Shows "Unhealthy / No Credentials"
- Antigravity agents utilize Antigravity's own authenticated Google session. Even if `Gemini CLI` is flagged as lacking credentials in `.shared/system_status.json`, delegation to Antigravity agents continues to work smoothly.
- To enable headless Gemini CLI (`gemini -p`), set your `GEMINI_API_KEY` or run `gemini` once interactively.

### 2. Preventing Scope Drift
- When creating prompts, always provide explicit boundaries in `FILES YOU MAY MODIFY`.
- Never give the Antigravity implementation agent the full orchestrator master prompt; provide only the scoped task prompt (`P00N-v1.md`).
- Run `python delegate.py verify` after every response. If an agent modified an unapproved file, roll back the unauthorized change and issue a corrective prompt (`C001`).

### 3. Stream Interruptions
- LLM agents working on complex builds can occasionally encounter stream timeouts.
- `delegate.py wait` defaults to a generous timeout (15 minutes). If an agent pauses, verify the live progress by inspecting `~/.gemini/antigravity/brain/<id>/.system_generated/logs/transcript.jsonl`.

### 4. SmartScreen Warning on Windows
- Because the launcher is compiled locally without an expensive commercial code-signing certificate, Windows SmartScreen will display an unrecognized application alert on first run.
- Click **"More info"** &rarr; **"Run anyway"**.

---

## Contributing & Building from Source

To compile the launcher from source:

```bash
# Navigate to the Go source directory
cd source

# Build for Windows
go build -o ../orchestrator-launcher.exe .

# Cross-compile for Linux (if desired)
set GOOS=linux
go build -o ../orchestrator-launcher-linux .
```

---

## License

This project is licensed under the [MIT License](LICENSE) &copy; 2026 Awan Biswas.
