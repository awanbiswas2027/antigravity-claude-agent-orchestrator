# Integration Discovery (§19)

Date: 2026-09-16

## Antigravity: two separate products are installed
| Product | Executable | CLI | Running at check time |
|---|---|---|---|
| Antigravity | `%LOCALAPPDATA%\Programs\Antigravity\Antigravity.exe` | None (its `bin\` folder is on PATH but does not exist) | Yes (6 processes) |
| Antigravity IDE 1.107.0 (commit ecfbad74) | `%LOCALAPPDATA%\Programs\Antigravity IDE\Antigravity IDE.exe` | `antigravity-ide` (`bin\antigravity-ide.cmd`, a VS Code-style `cli.js` shim) | No |

`orchestrator.config.json` checks only `Antigravity.exe`, not the IDE.

## Delegation channel: `antigravity-ide chat`
```
antigravity-ide chat [-m ask|edit|agent] [-a <file>]... [-n | -r] "<prompt>"
```
- Opens a chat session in the IDE window for the current working directory. Default mode is `agent`.
- Fire-and-forget: exit code 0 means the IDE accepted the prompt, **not** that the task succeeded. Nothing is written to stdout.
- **Results must therefore come back through the filesystem.** The prompt must name the exact report/response file for the agent to write, and Claude polls for it.
- The `-` argument reads the prompt from stdin, which is useful for long prompts.

Other useful subcommands: `--status` (diagnostics; only works while the IDE is running), `--list-extensions`, `--add-mcp`.

## Gemini
- Gemini CLI 0.60.0 has no credentials (see `system_status.json`).
- Assumption, NOT yet verified: models used inside Antigravity IDE agent mode are authenticated by the IDE's own sign-in, so delegating through `antigravity-ide chat` may not need Gemini CLI credentials. This will be verified by the handshake below.

## Handshake
- MSG-0001 sent 2026-09-16T21:55 with `antigravity-ide chat -m agent -n -a .shared/handshake/MSG-0001-request.json`, exit 0.
- Expected response: `.shared/handshake/MSG-0002-response.json`. Result: **TIMEOUT after 300 s** (no file written).
- IDE logs (`%APPDATA%\Antigravity IDE\logs60916T215536\window1\exthost\google.antigravity\Antigravity IDE.log`) show `Auth succeeded` and models fetched, so the IDE is signed in. No evidence that the chat prompt was executed. Likely it was only placed in the chat box, or it is waiting for approval in the UI. UNVERIFIED.

## Channel 2: Antigravity agent API (`agentapi`)
- Shim: `%USERPROFILE%\.gemini\antigravity\bin\agentapi.bat` → `%LOCALAPPDATA%\Programs\Antigravity\resources\bin\language_server.exe agentapi`
- Commands:
  ```
  agentapi new-conversation [--model=<flash_lite|flash|pro>] [--title=<title>] [--profile=<profile>] <prompt>
  agentapi send-message [--title=<title>] <recipient_id> <content>
  agentapi get-conversation-metadata <conversation_id>
  ```
- Required env vars (strings found in the binary): `ANTIGRAVITY_LS_ADDRESS`, `ANTIGRAVITY_CSRF_TOKEN` (and `ANTIGRAVITY_CONVERSATION_ID` for agent-to-agent calls).
- Antigravity sets these inside its own agent terminals. Called from outside: `{"error": "ANTIGRAVITY_LS_ADDRESS is not set"}` (exit 1).
- The standalone hub language server (`--standalone --subclient_type hub`) was listening on 127.0.0.1:57745/57746 at check time. Ports are random per launch.
- Supplying `ANTIGRAVITY_CSRF_TOKEN` from outside would mean copying it from the running process's command line, which defeats the local CSRF protection. **Needs human approval. Not done.**
- The model choice (`flash_lite|flash|pro`) = Gemini through Antigravity's own sign-in, so no Gemini CLI key is needed on this path.


## Handshake result (2026-09-16 22:25): SUCCESS through the Antigravity app, started by the human
- The human started a conversation in the standalone Antigravity app (conversation `af88b146`, model Gemini 3.8 Flash (High)) that pointed at the request file.
- The agent wrote `MSG-0002-response.json` (`status: SUCCESS`) at 22:25:11, about 13 minutes after it was started.
- Proven path: **Claude writes a request file → a human starts an Antigravity agent on it → the agent writes the response file → Claude polls for it and checks it.**
- Not yet automated: Claude can't start an Antigravity conversation on its own (`agentapi` needs `ANTIGRAVITY_LS_ADDRESS`/`ANTIGRAVITY_CSRF_TOKEN`; `antigravity-ide chat` timed out twice).
- Agents can see this workspace and follow file-based instructions, but they do not strictly keep to scope: the response was written to 2 paths although 1 was requested. Keep checking the scope of every result.
- Agent transcripts can be read (read-only) at `%USERPROFILE%\.gemini\antigravity\brain\<conversation-id>\.system_generated\logs\transcript.jsonl`. They are useful as evidence and for watching progress.

## Workspace change made by a second Antigravity agent (conversation `2207f44c`)
- It was given the master prompt, so it acted as a second orchestrator.
- It ran `Copy-Item orchestrator-launcher\orchestrator-launcher\* . -Recurse -Force`, which copied the launcher package to the project root (SHA-256 of the exe is the same in both places: f0c5a023...33e6). This overwrote the root `.shared/agents.md`, `.shared/skills/registry.md` and `.shared/logs/startup.log` with the nested copies.
- It then ran `orchestrator-launcher.exe --ensure` from the root (22:17:44, DEGRADED) and `gemini -p "test"`.
- The project root is now the launcher's project dir. The nested `orchestrator-launcher/` folder is a stale duplicate.
