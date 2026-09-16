# Colony Charter

Founded: 2026-09-16T22:55+05:30 by the Queen (Claude Code, claude-opus-5)
Operating rules: `autonomous_software_engineering_orchestrator.md` (master, wins on conflict) + `v2/orchestrator-launcher_1/orchestrator-launcher/ant_colony_agents.md` (colony add-on v1)
Current generation: 0 (founded, no ants spawned)
Colony state: FOUNDED (dormant)
Profile: LEAN (§6 default for this project; switch to STANDARD only when the human asks)

## Wake conditions (all three required, §6 Dormant state)
| # | Condition | State (2026-09-16T23:00+05:30) |
|---|---|---|
| 1 | Goal below has measurable acceptance criteria | NOT MET (goal unknown) |
| 2 | `cost_budget` is set | MET (see Budgets) |
| 3 | `orchestrator-launcher.exe --check` exits 0 | MET (exit 0 at 23:17; Gemini CLI set to not required by the human) |

While dormant the Queen only reads and writes files: no spawning, no research, no calls to other engines.

## Goals
UNKNOWN: the human hasn't set a colony goal yet. This workspace hosts the orchestrator tooling itself:
the launcher Go source in `source/`, the skill in `skills/antigravity-orchestrator/`, and the prompts. The only open task is
TASK-20260916-2235-BEFA (skill packaging, phase REVIEW, waiting for human feedback).
Resolve by: asking the human.

## Budgets (§6 LEAN profile, active)
```text
max_active_ants            : 2
max_workers                : 1
max_ants_per_caste         : 1
max_spawn_per_cycle        : 1
max_generations            : 3
ant_timeout_minutes        : 20
claim_ttl_minutes          : 30
heartbeat_interval_minutes : 5
max_retries_per_task       : 2
max_ant_crashes_per_10min  : 2
cost_budget                : Antigravity: unlimited (human, 2026-09-16) · Claude: minimal (orders and final reviews only)
```
Standard profile (inactive): 6 / 3 / 3 / 2 / 10 / 30 / 3 / 3.

## LEAN operating rules
- **Reviews:** the Queen reviews all work herself. A Soldier is spawned only for security-sensitive diffs or critical-file changes.
- **Ant lifetime:** prefer on-demand Gemini headless ants (`gemini -p`); retire each ant as soon as it reports.
- **Scouting:** one Scout covering one area at a time; reuse existing maps in `TASKS/*/research/scout_*.md`.
- **Testing:** targeted tests for each ant; the full regression suite once per generation, before any `DONE`.

## Work selection (§4)
alpha = 1.0, beta = 2.0, marker floor = 0.05, strength cap = 1.0
Response threshold: a caste's backlog above threshold for 2 cycles → the Queen may spawn; a caste idle for 2 cycles → retire its extra ants.

## Caste engines (§1, set from system health on 2026-09-16)
**Human directive (2026-09-16): Antigravity first.** Antigravity credits are effectively unlimited (the human also has 3 Gemini Pro accounts); Claude tokens are scarce.
The Queen writes complete, executable orders and does the final evidence review. Antigravity agents do all the other work.
This overrides the LEAN bullet preferring Gemini headless.

| Caste | Engine |
|---|---|
| Scout | Antigravity agent (read-only orders) |
| Worker | Antigravity agent |
| Soldier | Antigravity agent (review orders); the Queen still does the final gate |
| Nurse | Antigravity agent |
| Midden | Antigravity agent |
| Forager | Antigravity agent (web research) |
| Fallback | Claude subagent only when no Antigravity path exists; recorded in `nest_status.md` |

Dispatch: file message bus (channel A, verified). The human starts one Antigravity conversation per ant and pastes the one-line
order pointer that the Queen prints. Pro model preferred for Worker and Soldier orders.

## Wake-up plan (LEAN)
Generation 1: one Scout on the area the goal names → the Queen breaks the findings into tasks and lays FOOD → one Worker
→ Queen review (plus a Soldier only if the rules above require one) → full regression suite → DONE.

## Critical files (claims need Queen approval)
`orchestrator.config.json`, `source/**`, `orchestrator-launcher.exe`, `.gitignore`, `.shared/system_status.json`,
`autonomous_software_engineering_orchestrator.md`, `ant_colony_agents.md`, `skills/*/SKILL.md`, any CI config or lockfile.
