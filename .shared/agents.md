# Agent Capability Registry

Source: `.shared/system_status.json` from `orchestrator-launcher.exe --ensure` at 2026-09-16T22:17:44+05:30 (exit 1, DEGRADED)

| Agent | Role | Capabilities | Status | Detail |
|---|---|---|---|---|
| Claude | Architect | Architecture, decomposition, review | Available | 2.1.270 (Claude Code) |
| Antigravity | Orchestrator | Swarm coordination, routing | Available: file handshake verified 2026-09-16 22:25 (conversation started by human) | `%LOCALAPPDATA%\Programs\Antigravity\Antigravity.exe`; Claude cannot start conversations automatically yet (see research/integration.md) |
| Gemini (via Antigravity) | Implementer | Coding, tests, debugging | Available inside Antigravity agents (Gemini 3.8 Flash) | Uses Antigravity's sign-in |
| Gemini CLI | Implementer | Coding, tests, debugging | BLOCKED (no credentials) | 0.60.0; needs `GEMINI_API_KEY` / `GOOGLE_API_KEY` / `GOOGLE_CLOUD_PROJECT`, or one interactive sign-in |

