# Skill / Tool Registry

| Name | Purpose | Source | Version | Install method | Config location | Why needed | Alternatives | Compatibility | Security | Used by | Installed? |
|---|---|---|---|---|---|---|---|---|---|---|---|
| Claude Code | Architect / orchestrator CLI | npm | 2.1.270 | npm (global) | ~/.claude | Core agent | — | Windows 11, Node | — | Claude | Y |
| Gemini CLI | Implementation agent | npm | 0.60.0 | npm (global) | ~/.gemini | Core agent | Antigravity agents (Gemini through the app's sign-in) | Windows 11, Node | Needs credentials (env var or sign-in) | Gemini | Y (not authenticated) |
| Antigravity (app) | Agent hub / orchestrator | Google | app 2.14.0 hub | installer | ~/.gemini/antigravity | Runs Gemini agents | Antigravity IDE `chat` | Windows 11 | `agentapi` requires a local CSRF token | Antigravity | Y |
| Antigravity IDE CLI | `antigravity-ide chat` | Google | 1.107.0 | installer (bin on PATH) | ~/.gemini/antigravity-ide | Alternative delegation channel | agentapi | Windows 11 | — | Antigravity | Y (chat delivery unverified) |
