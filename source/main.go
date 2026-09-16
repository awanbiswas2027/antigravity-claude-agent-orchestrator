// orchestrator-launcher: brings up the Claude / Antigravity / Gemini orchestration system.
//
// Usage:
//   orchestrator-launcher.exe            ensure every component is up, then open Claude Code
//   orchestrator-launcher.exe --ensure   ensure every component is up (no Claude window); exit 0 = healthy
//   orchestrator-launcher.exe --check    report health only, start nothing; exit 0 = healthy
//   orchestrator-launcher.exe --watch 60 keep checking every 60 s and restart anything that stopped
package main

import (
	"encoding/json"
	"errors"
	"flag"
	"fmt"
	"io"
	"os"
	"os/exec"
	"path/filepath"
	"regexp"
	"runtime"
	"strings"
	"time"
)

type Component struct {
	Name                 string   `json:"name"`
	Kind                 string   `json:"kind"` // "app" (long-running process) or "cli" (invoked on demand)
	Required             bool     `json:"required"`
	ExecutableCandidates []string `json:"executable_candidates"`
	ProcessNames         []string `json:"process_names"`
	StartArgs            []string `json:"start_args"`
	CheckArgs            []string `json:"check_args"`
	InstallCommand       []string `json:"install_command"`
	AuthEnv              []string `json:"auth_env"`
	AuthFiles            []string `json:"auth_files"`
}

type Config struct {
	ProjectDir          string      `json:"project_dir"`
	PromptFile          string      `json:"prompt_file"`
	StartupTimeoutSecs  int         `json:"startup_timeout_seconds"`
	MaxStartAttempts    int         `json:"max_start_attempts"`
	AutoInstall         bool        `json:"auto_install"`
	LaunchClaude        bool        `json:"launch_claude"`
	ClaudeStartupPrompt string      `json:"claude_startup_prompt"`
	Components          []Component `json:"components"`
}

type Result struct {
	Name       string `json:"name"`
	Kind       string `json:"kind"`
	Required   bool   `json:"required"`
	Installed  bool   `json:"installed"`
	Running    bool   `json:"running"`
	Authorized bool   `json:"authorized"`
	Healthy    bool   `json:"healthy"`
	Executable string `json:"executable,omitempty"`
	Action     string `json:"action"`
	Detail     string `json:"detail,omitempty"`
}

type Status struct {
	Timestamp  string   `json:"timestamp"`
	ProjectDir string   `json:"project_dir"`
	Healthy    bool     `json:"healthy"`
	Components []Result `json:"components"`
}

var logw io.Writer = os.Stdout

func logf(format string, a ...any) {
	fmt.Fprintf(logw, "%s  %s\n", time.Now().Format("2006-01-02T15:04:05-07:00"), fmt.Sprintf(format, a...))
}

func exeDir() string {
	p, err := os.Executable()
	if err != nil {
		wd, _ := os.Getwd()
		return wd
	}
	return filepath.Dir(p)
}

var envRe = regexp.MustCompile(`%([A-Za-z0-9_]+)%`)

func expand(s, projectDir string) string {
	s = strings.ReplaceAll(s, "{project_dir}", projectDir)
	s = envRe.ReplaceAllStringFunc(s, func(m string) string { return os.Getenv(m[1 : len(m)-1]) })
	return os.ExpandEnv(s)
}

func loadConfig(path string) (*Config, error) {
	b, err := os.ReadFile(path)
	if errors.Is(err, os.ErrNotExist) {
		if werr := os.WriteFile(path, []byte(defaultConfig), 0o644); werr != nil {
			return nil, werr
		}
		b = []byte(defaultConfig)
		logf("Created default config: %s", path)
	} else if err != nil {
		return nil, err
	}
	var c Config
	if err := json.Unmarshal(b, &c); err != nil {
		return nil, fmt.Errorf("config %s is not valid JSON: %w", path, err)
	}
	if c.StartupTimeoutSecs <= 0 {
		c.StartupTimeoutSecs = 60
	}
	if c.MaxStartAttempts <= 0 {
		c.MaxStartAttempts = 3
	}
	return &c, nil
}

// findExecutable returns the first candidate that exists (absolute path) or is on PATH.
func findExecutable(c Component, projectDir string) string {
	for _, cand := range c.ExecutableCandidates {
		p := expand(cand, projectDir)
		if p == "" {
			continue
		}
		if filepath.IsAbs(p) {
			if st, err := os.Stat(p); err == nil && !st.IsDir() {
				return p
			}
			continue
		}
		if lp, err := exec.LookPath(p); err == nil {
			return lp
		}
	}
	return ""
}

// commandFor wraps .cmd/.bat shims (npm installs) so they run correctly on Windows.
func commandFor(exe string, args ...string) *exec.Cmd {
	ext := strings.ToLower(filepath.Ext(exe))
	if runtime.GOOS == "windows" && (ext == ".cmd" || ext == ".bat") {
		return exec.Command("cmd", append([]string{"/c", exe}, args...)...)
	}
	return exec.Command(exe, args...)
}

func runQuiet(timeout time.Duration, exe string, args ...string) (string, error) {
	cmd := commandFor(exe, args...)
	type res struct {
		out []byte
		err error
	}
	ch := make(chan res, 1)
	go func() { o, e := cmd.CombinedOutput(); ch <- res{o, e} }()
	select {
	case r := <-ch:
		return strings.TrimSpace(string(r.out)), r.err
	case <-time.After(timeout):
		if cmd.Process != nil {
			_ = cmd.Process.Kill()
		}
		return "", fmt.Errorf("timed out after %s", timeout)
	}
}

func isProcessRunning(names []string) bool {
	for _, n := range names {
		if runtime.GOOS == "windows" {
			out, err := exec.Command("tasklist", "/FI", "IMAGENAME eq "+n, "/NH", "/FO", "CSV").Output()
			if err == nil && strings.Contains(strings.ToLower(string(out)), strings.ToLower(n)) {
				return true
			}
		} else {
			if err := exec.Command("pgrep", "-x", strings.TrimSuffix(n, ".exe")).Run(); err == nil {
				return true
			}
		}
	}
	return false
}

func startDetached(exe string, args []string, dir string) error {
	var cmd *exec.Cmd
	if runtime.GOOS == "windows" {
		cmd = exec.Command("cmd", append([]string{"/c", "start", "", exe}, args...)...)
	} else {
		cmd = exec.Command(exe, args...)
	}
	cmd.Dir = dir
	if err := cmd.Start(); err != nil {
		return err
	}
	go cmd.Wait()
	return nil
}

func checkAuth(c Component, projectDir string) (bool, string) {
	if len(c.AuthEnv) == 0 && len(c.AuthFiles) == 0 {
		return true, ""
	}
	for _, e := range c.AuthEnv {
		if os.Getenv(e) != "" {
			return true, "credentials found in env var " + e
		}
	}
	for _, f := range c.AuthFiles {
		if _, err := os.Stat(expand(f, projectDir)); err == nil {
			return true, "credentials file found"
		}
	}
	return false, fmt.Sprintf("no credentials: set one of %v or sign in once interactively", c.AuthEnv)
}

func tryInstall(c Component) error {
	if len(c.InstallCommand) == 0 {
		return errors.New("no install_command configured")
	}
	bin, err := exec.LookPath(c.InstallCommand[0])
	if err != nil {
		return fmt.Errorf("%s not found on PATH (install Node.js first)", c.InstallCommand[0])
	}
	logf("  installing %s: %s", c.Name, strings.Join(c.InstallCommand, " "))
	out, err := runQuiet(10*time.Minute, bin, c.InstallCommand[1:]...)
	if err != nil {
		return fmt.Errorf("install failed: %v: %s", err, lastLines(out, 5))
	}
	return nil
}

func lastLines(s string, n int) string {
	l := strings.Split(s, "\n")
	if len(l) > n {
		l = l[len(l)-n:]
	}
	return strings.Join(l, " | ")
}

func ensure(c Component, cfg *Config, projectDir string, startMissing bool) Result {
	r := Result{Name: c.Name, Kind: c.Kind, Required: c.Required, Action: "none"}
	logf("[%s] checking…", c.Name)

	exe := findExecutable(c, projectDir)
	if exe == "" && startMissing && cfg.AutoInstall && len(c.InstallCommand) > 0 {
		if err := tryInstall(c); err != nil {
			r.Detail = err.Error()
		} else {
			r.Action = "installed"
			exe = findExecutable(c, projectDir)
		}
	}
	if exe == "" {
		if r.Detail == "" {
			r.Detail = "not installed / not found (edit executable_candidates in orchestrator.config.json)"
		}
		logf("[%s] NOT FOUND — %s", c.Name, r.Detail)
		return r
	}
	r.Installed, r.Executable = true, exe
	r.Authorized, _ = checkAuth(c, projectDir)
	_, authDetail := checkAuth(c, projectDir)

	switch c.Kind {
	case "app":
		r.Running = isProcessRunning(c.ProcessNames)
		if !r.Running && startMissing {
			for attempt := 1; attempt <= cfg.MaxStartAttempts && !r.Running; attempt++ {
				logf("[%s] not running — starting (attempt %d/%d)", c.Name, attempt, cfg.MaxStartAttempts)
				args := make([]string, len(c.StartArgs))
				for i, a := range c.StartArgs {
					args[i] = expand(a, projectDir)
				}
				if err := startDetached(exe, args, projectDir); err != nil {
					r.Detail = "start failed: " + err.Error()
					continue
				}
				deadline := time.Now().Add(time.Duration(cfg.StartupTimeoutSecs) * time.Second / time.Duration(cfg.MaxStartAttempts))
				for time.Now().Before(deadline) {
					time.Sleep(2 * time.Second)
					if isProcessRunning(c.ProcessNames) {
						r.Running, r.Action, r.Detail = true, "started", ""
						break
					}
				}
			}
			if !r.Running && r.Detail == "" {
				r.Detail = "process did not appear after start attempts"
			}
		}
	default: // cli
		out, err := runQuiet(60*time.Second, exe, c.CheckArgs...)
		if err != nil {
			r.Detail = fmt.Sprintf("health check failed: %v %s", err, lastLines(out, 3))
		} else {
			r.Running = true
			r.Detail = strings.TrimSpace(lastLines(out, 1))
		}
	}
	if !r.Authorized {
		r.Detail = strings.TrimSpace(r.Detail + "; " + authDetail)
	}
	r.Healthy = r.Installed && r.Running && r.Authorized
	state := "OK"
	if !r.Healthy {
		state = "UNHEALTHY"
	}
	logf("[%s] %s (action=%s) %s", c.Name, state, r.Action, r.Detail)
	return r
}

func writeStatus(projectDir string, s Status) {
	dir := filepath.Join(projectDir, ".shared")
	_ = os.MkdirAll(dir, 0o755)
	b, _ := json.MarshalIndent(s, "", "  ")
	_ = os.WriteFile(filepath.Join(dir, "system_status.json"), b, 0o644)
}

func runAll(cfg *Config, projectDir string, start bool) Status {
	s := Status{Timestamp: time.Now().Format(time.RFC3339), ProjectDir: projectDir, Healthy: true}
	for _, c := range cfg.Components {
		r := ensure(c, cfg, projectDir, start)
		s.Components = append(s.Components, r)
		if c.Required && !r.Healthy {
			s.Healthy = false
		}
	}
	writeStatus(projectDir, s)
	return s
}

func launchClaude(cfg *Config, projectDir string, s Status) error {
	var exe string
	for _, r := range s.Components {
		if strings.EqualFold(r.Name, "Claude Code") && r.Installed {
			exe = r.Executable
		}
	}
	if exe == "" {
		return errors.New("Claude Code is not installed, cannot open the orchestrator")
	}
	prompt := expand(cfg.ClaudeStartupPrompt, projectDir)
	prompt = strings.ReplaceAll(prompt, "{prompt_file}", cfg.PromptFile)
	prompt = strings.NewReplacer(`"`, "'", "\r", " ", "\n", " ").Replace(prompt)

	if runtime.GOOS != "windows" {
		logf("Would launch: %s %q (in %s)", exe, prompt, projectDir)
		return nil
	}
	// A small .cmd file avoids fragile nested quoting through `start`.
	script := filepath.Join(projectDir, ".shared", "launch_claude.cmd")
	body := "@echo off\r\ntitle Claude Orchestrator\r\ncd /d \"" + projectDir + "\"\r\n" +
		"call \"" + exe + "\" \"" + strings.ReplaceAll(prompt, "%", "%%") + "\"\r\n"
	if err := os.WriteFile(script, []byte(body), 0o644); err != nil {
		return err
	}
	return exec.Command("cmd", "/c", "start", "Claude Orchestrator", "cmd", "/k", script).Start()
}

func ensureFolders(projectDir string) {
	for _, d := range []string{
		"TASKS", ".shared", filepath.Join(".shared", "skills", "installed"),
		filepath.Join(".shared", "skills", "recommended"), filepath.Join(".shared", "logs"),
	} {
		_ = os.MkdirAll(filepath.Join(projectDir, d), 0o755)
	}
	for name, content := range map[string]string{
		filepath.Join(".shared", "skills", "registry.md"): "# Skill Registry\n\n| Name | Purpose | Source | Version | Installed | Used by |\n|---|---|---|---|---|---|\n",
		filepath.Join(".shared", "agents.md"):             "# Agent Capability Registry\n\n| Agent | Role | Capabilities | Status |\n|---|---|---|---|\n| Claude | Architect | Architecture, decomposition, review | Available |\n| Antigravity | Orchestrator | Swarm coordination, routing | See system_status.json |\n| Gemini | Implementer | Coding, tests, debugging | See system_status.json |\n",
	} {
		p := filepath.Join(projectDir, name)
		if _, err := os.Stat(p); errors.Is(err, os.ErrNotExist) {
			_ = os.WriteFile(p, []byte(content), 0o644)
		}
	}
}

func pauseIfInteractive(interactive bool) {
	if interactive && runtime.GOOS == "windows" {
		fmt.Println("\nPress Enter to close…")
		fmt.Scanln()
	}
}

func main() {
	check := flag.Bool("check", false, "report health only, start nothing")
	ensureOnly := flag.Bool("ensure", false, "start missing components but do not open Claude")
	watch := flag.Int("watch", 0, "keep ensuring every N seconds (0 = off)")
	configPath := flag.String("config", filepath.Join(exeDir(), "orchestrator.config.json"), "config file")
	flag.Parse()
	interactive := !*check && !*ensureOnly && *watch == 0

	cfg, err := loadConfig(*configPath)
	if err != nil {
		fmt.Println("ERROR:", err)
		pauseIfInteractive(true)
		os.Exit(2)
	}
	projectDir := expand(cfg.ProjectDir, exeDir())
	if projectDir == "" {
		projectDir = exeDir()
	}
	projectDir, _ = filepath.Abs(projectDir)

	ensureFolders(projectDir)
	if f, err := os.OpenFile(filepath.Join(projectDir, ".shared", "logs", "startup.log"), os.O_CREATE|os.O_APPEND|os.O_WRONLY, 0o644); err == nil {
		defer f.Close()
		logw = io.MultiWriter(os.Stdout, f)
	}
	logf("=== Orchestrator system-up · project: %s ===", projectDir)
	if _, err := os.Stat(filepath.Join(projectDir, cfg.PromptFile)); err != nil {
		logf("WARNING: prompt file %s not found in project folder", cfg.PromptFile)
	}

	if *watch > 0 {
		logf("Watch mode: checking every %d s (Ctrl+C to stop)", *watch)
		for {
			runAll(cfg, projectDir, true)
			time.Sleep(time.Duration(*watch) * time.Second)
		}
	}

	s := runAll(cfg, projectDir, !*check)
	if s.Healthy {
		logf("SYSTEM UP — all required components healthy")
	} else {
		logf("SYSTEM DEGRADED — see .shared/system_status.json")
	}

	if interactive && cfg.LaunchClaude {
		if err := launchClaude(cfg, projectDir, s); err != nil {
			logf("ERROR launching Claude: %v", err)
		} else {
			logf("Claude Code orchestrator window opened")
		}
	}
	if !s.Healthy {
		pauseIfInteractive(interactive)
		os.Exit(1)
	}
	if interactive {
		time.Sleep(3 * time.Second)
	}
}

const defaultConfig = `{
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
      "executable_candidates": ["claude", "%APPDATA%\\npm\\claude.cmd", "%USERPROFILE%\\.local\\bin\\claude.exe"],
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
        "%ProgramFiles%\\Antigravity\\Antigravity.exe",
        "antigravity"
      ],
      "process_names": ["Antigravity.exe"],
      "start_args": ["{project_dir}"]
    }
  ]
}
`
