# Templates

Contents:
1. Task folder layout
2. STATUS.md and state machine
3. shared_context.md
4. Implementation prompt (P)
5. Regression prompt (R) and regression matrix
6. Corrective prompt (C)
7. Agent report (evidence standard)
8. Message bus JSON
9. ADR
10. Review note
11. Final report
12. Self-check before sending a prompt
13. Definition of Done
14. Log line format

---

## 1. Task folder layout

`scripts/new_task.py` creates this tree:

```text
TASKS/<TASK_ID>/
├── STATUS.md                 # single source of current truth
├── shared_context.md         # shared state for all agents
├── 00_project_context.md  01_problem_definition.md  02_requirements.md
├── 03_architecture.md     04_task_breakdown.md
├── prompts/{implementation,regression,corrective}/   P001-v1.md, R001-v1.md, C001-v1.md
├── tests/{regression_matrix.md, acceptance_tests.md, test_results.md}
├── research/{sources.md, skills.md, technical_findings.md}
├── communication/{message_bus.jsonl, requests/, responses/}
├── decisions/ADR-001.md …
├── logs/{execution.log, errors.log, audit.log}
└── reports/{implementation_report.md, regression_report.md, final_report.md}
```

Project-wide files:
- `.shared/agents.md`: agent capability table
- `.shared/skills/registry.md`: tools and skills in use
- `.shared/system_status.json`: health
- `.shared/research/integration.md`: how each agent is actually reached

## 2. STATUS.md

```markdown
# Task Status
Task: TASK-20260916-1930-A81F      Tier: M
## Objective:
## Current Phase:   IMPLEMENTING
## Current Prompt:  P003-v1
## Agent:           Gemini (Antigravity)
## Overall Status:  IN_PROGRESS
## Completed:       P001, P002
## Active:          P003
## Pending:         P004, R003
## Test Status:     42 passed / 2 failed / 0 skipped   (source: logs, re-run by Claude)
## Corrective Iterations: 1 of 3
## Blocking Issues:
## Next Action:
```

State machine:

```text
DISCOVERY → RESEARCH → ARCHITECTURE → DECOMPOSITION → READY
→ IMPLEMENTING → TESTING → REVIEW ─┬─ APPROVED → COMPLETE
                                   └─ FAILED → CORRECTIVE_ACTION → IMPLEMENTING
```

The terminal states are `COMPLETE`, `BLOCKED` and `CANCELLED`.

## 3. shared_context.md

Sections:
- Task objective
- Current architecture
- Current state
- Relevant files
- Constraints
- Decisions
- Active prompt
- Acceptance criteria
- Known failures
- Latest test results
- Implementation status
- Agent responsibilities

Update it after every meaningful state change.

## 4. Implementation prompt: `prompts/implementation/P00N-v1.md`

The agent must be able to run this prompt without guessing about architecture. Avoid vague phrases like "make it better" or "fix the backend", and describe observable outcomes instead.

```markdown
# P003-v1 · TASK-20260916-1930-A81F

## ROLE
You are the implementation engineer responsible for <scope>.
## MISSION / OBJECTIVE
## CONTEXT                      (link shared_context.md; summarize what matters)
## CURRENT SYSTEM STATE         (what exists now, with file paths)
## ARCHITECTURAL CONSTRAINTS
## PREREQUISITES / DEPENDENCIES (e.g. "P002 merged")
## FILES TO INSPECT
## FILES YOU MAY MODIFY         (exact paths or globs)
## FILES YOU MUST NOT MODIFY
## IMPLEMENTATION REQUIREMENTS
## STEP-BY-STEP EXECUTION
## EDGE CASES
## ERROR HANDLING
## SECURITY REQUIREMENTS
## PERFORMANCE REQUIREMENTS
## TESTING                      (exact commands)
## ACCEPTANCE CRITERIA          (measurable)
## EVIDENCE REQUIRED            (command output, diff summary, …)
## ROLLBACK CONSIDERATIONS
## REPORT
Write your report as JSON to: <TASKS/ID/communication/responses/MSG-000N.json>
using the Agent report format below. If anything is ambiguous, set
status NEEDS_CLARIFICATION and ask. Don't guess.
Rules: don't edit files outside FILES YOU MAY MODIFY; don't weaken, skip or
delete tests; don't claim success without command output.
Working loop: READ → UNDERSTAND → PLAN → MODIFY → TEST → INSPECT DIFF → FIX → TEST AGAIN → REPORT
```

## 5. Regression prompt: `prompts/regression/R00N-v1.md` (one for every P)

```markdown
# R003-v1 → covers P003
## ROLE
## TASK UNDER TEST
## KNOWN PREVIOUS BEHAVIOR
## NEW EXPECTED BEHAVIOR
## REGRESSION RISKS             (what existing behavior could this change break?)
## TEST ENVIRONMENT / SETUP
## TEST CASES                   (existing behavior · new behavior · integration), each with an ID like REG-AUTH-001
## EDGE CASES                   (boundaries · invalid input · missing data · concurrency · network/permission failures · timeouts · duplicates · unexpected state)
## NEGATIVE TESTS
## EXPECTED RESULTS
## FAILURE CONDITIONS
## COMMANDS
## EVIDENCE REQUIRED
## REPORT FORMAT
```

`tests/regression_matrix.md`:

| Test ID | Feature | Type | Status | Evidence | Failure | Related Prompt |
|---|---|---|---|---|---|---|
| REG-AUTH-001 | Login rejects bad password | negative | NOT_RUN | | | P003 |

The allowed statuses are `NOT_RUN`, `PASS`, `FAIL`, `BLOCKED` and `SKIPPED`. Mark PASS only when you have evidence. Don't delete a test just because it fails: either fix the code, or document why the test is obsolete.

## 6. Corrective prompt: `prompts/corrective/C00N-v1.md`

```markdown
# C001-v1 · fixes P003 · TASK-…
## ORIGINAL TASK
## FAILURE
## EXACT EVIDENCE        (verbatim output)
## EXPECTED RESULT
## ACTUAL RESULT
## LIKELY ROOT CAUSE
## FILES INVOLVED
## MINIMAL CORRECTION    (smallest safe fix, not a rewrite)
## CONSTRAINTS
## TESTS THAT MUST PASS
## REGRESSION TESTS THAT MUST STAY GREEN
## REPORT                (same response path and format)
```

The limit is 3 corrective cycles per issue. After that, set the task to BLOCKED and escalate to the human.

## 7. Agent report (evidence standard)

```json
{
  "message_id": "MSG-0001-R",
  "in_reply_to": "MSG-0001",
  "task_id": "TASK-…",
  "type": "IMPLEMENTATION_RESULT",
  "prompt_id": "P003-v1",
  "status": "SUCCESS | FAILED | BLOCKED | NEEDS_CLARIFICATION",
  "agent": "gemini (antigravity, <model>)",
  "files_changed": [{"path": "src/x.py", "why": "…"}],
  "commands_run": ["pytest tests/x -q"],
  "tests_run": 44, "tests_passed": 42, "tests_failed": 2, "tests_skipped": 0,
  "test_output_excerpt": "42 passed, 2 failed in 3.1s",
  "errors": [], "warnings": [],
  "git_diff_summary": "2 files changed, 40 insertions(+), 3 deletions(-)",
  "decisions": [], "remaining_work": [], "risks": [],
  "next_recommendation": "…",
  "timestamp": "2026-09-16T19:55:00+05:30"
}
```

Reply IDs are `<request id>-R`, so they never collide with Claude's next request ID. Reject any report whose claims have no evidence behind them.

## 8. Message bus (`communication/message_bus.jsonl`, append-only)

Claude → Antigravity:
```json
{"message_id":"MSG-0001","task_id":"TASK-…","type":"IMPLEMENTATION_REQUEST","prompt_id":"P003-v1","priority":"HIGH","objective":"…","prompt_file":"TASKS/…/P003-v1.md","response_file":"TASKS/…/responses/MSG-0001.json","context_file":"TASKS/…/shared_context.md","depends_on":["P002"],"required_tests":[],"acceptance_criteria":[],"timestamp":"…"}
```

Other message types:
- `HANDSHAKE_REQUEST` / `HANDSHAKE_RESULT`
- `IMPLEMENTATION_RESULT`
- `REGRESSION_REQUEST` / `REGRESSION_RESULT`
- `CORRECTIVE_REQUEST`
- `REVIEW` (Claude's verdict)
- `DELIVERY_RESULT` (a channel failed or timed out)

Never rewrite earlier lines. Before sending the same message again, check whether the first one was received (look for its `message_id` in the bus and in responses).

## 9. ADR (`decisions/ADR-NNN.md`)

```markdown
# ADR-001: <title>
## Status      Proposed | Accepted | Superseded by ADR-00X
## Context
## Options Considered
## Decision
## Reasoning
## Trade-offs
## Rejected Alternatives (and why)
## Consequences
```

## 10. Review note (append to `reports/implementation_report.md`)

```markdown
### Review of MSG-000N (P003-v1): APPROVED | NEEDS_REVISION | BLOCKED
Evidence re-run by Claude: <command → result>
Diff inspected: <files, +/- lines>
Scope check: <in scope | out-of-scope files: …>
Checklist: architecture · requirements · code quality · security · error handling ·
performance · test coverage · regression risk · docs · maintainability ·
complexity · dependencies · backward compatibility · drift
Findings: …
Decision and next action: …
```

## 11. Final report (`reports/final_report.md`)

```markdown
# Final Engineering Report
## Task
## Objective
## Architecture
## Implementation Summary
## Files Changed
## Agents Used
## Skills / Tools Used
## Tests
## Regression Results
## Failures Encountered
## Corrections Applied
## Evidence
## Security Considerations
## Performance Considerations
## Architectural Decisions (ADR links)
## Remaining Risks / Follow-ups
## Final Status
```

## 12. Self-check before sending an implementation prompt

```text
[ ] Requirements understood          [ ] Relevant code inspected
[ ] Architecture defined             [ ] Dependencies identified
[ ] Skill/tool needs checked         [ ] Prompt executable without guessing
[ ] Files listed (may / must not modify)
[ ] Acceptance criteria measurable   [ ] Regression prompt created
[ ] Evidence requirements defined    [ ] Rollback risk considered
[ ] No secrets in the prompt         [ ] Health check done (agent reachable or fallback chosen)
[ ] Response file path stated in the prompt
```

## 13. Definition of Done

```text
[ ] Implementation verified against evidence (re-run by Claude)
[ ] Target tests passed               [ ] Full regression suite passed
[ ] Architecture reviewed (no unaddressed drift)
[ ] Git diff reviewed                 [ ] Documentation updated
[ ] Logs written                      [ ] Communication recorded
[ ] ADRs recorded for major decisions
[ ] Final report created              [ ] STATUS.md = COMPLETE
```

## 14. Log line format (`logs/*.log`)

```text
timestamp | task_id | agent | event | status | details
2026-09-16T19:42:10+05:30 | TASK-20260916-1930-A81F | CLAUDE | PROMPT_CREATED | SUCCESS | P003-v1
```
