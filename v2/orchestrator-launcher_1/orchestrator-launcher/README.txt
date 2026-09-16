ORCHESTRATOR LAUNCHER - SETUP
=============================
1. Copy everything in this folder into the root of your project.
2. Install Node.js (needed so Claude Code / Gemini CLI can auto-install).
3. Gemini credentials (one time): set GEMINI_API_KEY in Windows environment
   variables, OR run `gemini` once in a terminal and sign in.
4. Install Antigravity. If it is not in the default location, edit
   "executable_candidates" for Antigravity in orchestrator.config.json.
5. Double-click orchestrator-launcher.exe.
   It checks/starts Claude Code, Gemini CLI and Antigravity, writes
   .shared\system_status.json, then opens Claude Code with the master prompt.

Other modes (run from a terminal):
  orchestrator-launcher.exe --check      health report only
  orchestrator-launcher.exe --ensure     start/install missing parts
  orchestrator-launcher.exe --watch 60   watchdog, restarts stopped parts

Log: .shared\logs\startup.log
Windows SmartScreen may warn because the exe is unsigned: click
"More info" -> "Run anyway". Source code is in the source\ folder;
rebuild with:  set GOOS=windows && go build -o orchestrator-launcher.exe .
