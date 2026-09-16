# System bring-up and health

## Two ways to check health

| Tool | When to use it | Starts or installs anything? |
|---|---|---|
| `orchestrator-launcher.exe` (Go; source in `assets/launcher/`) | The project already has the launcher in its root | `--ensure` and the default mode start or install missing parts. `--check` doesn't. |
| `scripts/health_check.py` | Any project. Needs only Python 3.9+. | Never. It only reports. `--init` creates the folders and registries. |

Both write `.shared/system_status.json` in the same shape:

```json
{"timestamp": "…", "project_dir": "…", "healthy": false,
 "components": [{"name": "Gemini CLI", "kind": "cli", "required": true, "installed": true,
   "running": true, "authorized": false, "healthy": false, "executable": "…", "action": "none",
   "detail": "0.60.0; no credentials: …"}]}
```

## Launcher modes

| Command | Effect | Exit code |
|---|---|---|
| `orchestrator-launcher.exe` | Brings everything up, then opens Claude Code with the master prompt | 0 = healthy, 1 = degraded |
| `--ensure` | Starts or installs anything missing (no Claude window) | 0 / 1 |
| `--check` | Reports only | 0 / 1 |
| `--watch 60` | Watchdog that restarts anything that stopped | runs until stopped |

The launcher reads `orchestrator.config.json` from its own folder. An empty `project_dir` means "the folder the exe is in", so put the exe in the **project root**.

To install it in a project:
1. Copy `assets/launcher/orchestrator.config.json` and `README.txt` into the project root.
2. Build the exe (needs Go 1.24 or newer), or copy a trusted build:
   ```
   cd assets/launcher && go build -o <project>/orchestrator-launcher.exe .
   ```
3. Unsigned builds trigger a SmartScreen warning. Read the source before running a binary you didn't build.
4. Add `*.exe`, `.shared/logs/`, `.shared/system_status.json` and `.shared/launch_claude.cmd` to `.gitignore`.

The shipped config only checks the `Antigravity.exe` agent hub. If a project delegates through the IDE instead, add an `Antigravity IDE` component (with `process_names: ["Antigravity IDE.exe"]`), and record the change in an audit entry.

## What "healthy" means

| Component | Healthy when | What auto-recovery can do |
|---|---|---|
| Claude Code | `claude --version` succeeds | Install it with npm |
| Gemini CLI | `gemini --version` succeeds **and** credentials exist | Install it with npm. Credentials always need a human. |
| Antigravity | The process is running | Start it with the project folder, up to the retry limit |

A Gemini CLI marked unhealthy doesn't block delegation if Antigravity agents are available, because they use the app's own sign-in. Say this explicitly in the status report.

## Recovery rules

1. **At startup:** run `--ensure` (or `health_check.py`) and read the status before doing any work.
2. **Before each delegation:** run a health check. If something is unhealthy, run `--ensure` once and check again.
3. **After a connection error or timeout:** run `--ensure`, then send the message again **once**, after first checking whether it was already received.
4. **Log every recovery** in `logs/audit.log` and `STATUS.md`.
5. **Know what needs a human:** credentials or sign-in, installing the app, a failed Node/npm install, and license problems. Set the status to `BLOCKED`, give the exact action, and continue whatever work is safe.
6. **Never work around a failure** by editing credentials, disabling security prompts, killing unrelated processes, or quietly changing the launcher config.
7. **Limit restarts.** More than 3 crashes in 10 minutes means stop and report.
8. **Keep the registry current.** Update `.shared/agents.md` whenever health changes.
