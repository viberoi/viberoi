// viberoi-agent — privacy-first AI engineering ROI agent.
//
// Commands:
//   register --org-id <uuid> --developer-id <uuid> --token <secret> --url <https-url> [--claude-code-path <dir>] [--poll-seconds <n>]
//   push                  one-shot scan + upload
//   run                   daemon loop
//   version               prints version
//
// All commands honour a global --config flag for the config path.
package main

import (
	"context"
	"flag"
	"fmt"
	"os"
	"os/signal"
	"path/filepath"
	"syscall"

	"github.com/viberoi/viberoi/agent/pkg/config"
	"github.com/viberoi/viberoi/agent/pkg/runner"
	"github.com/viberoi/viberoi/agent/pkg/state"
)

const usage = `viberoi-agent — captures AI coding-tool session metadata.

USAGE:
  viberoi-agent register --org-id <uuid> --developer-id <uuid> --token <token> --url <https-url> [--claude-code-path <dir>] [--claude-code-agent-mode-path <dir>] [--cursor-db-path <file>] [--poll-seconds <n>]
  viberoi-agent push
  viberoi-agent run
  viberoi-agent version
`

func main() {
	if len(os.Args) < 2 {
		fmt.Fprint(os.Stderr, usage)
		os.Exit(2)
	}
	switch os.Args[1] {
	case "register":
		runRegister(os.Args[2:])
	case "push":
		runOnce(os.Args[2:], false)
	case "run":
		runOnce(os.Args[2:], true)
	case "version":
		fmt.Println("viberoi-agent", runner.AgentVersion)
	case "-h", "--help", "help":
		fmt.Print(usage)
	default:
		fmt.Fprintf(os.Stderr, "unknown command: %s\n\n%s", os.Args[1], usage)
		os.Exit(2)
	}
}

func cfgPath(custom string) string {
	if custom != "" {
		return custom
	}
	p, err := config.Path()
	if err != nil {
		fmt.Fprintf(os.Stderr, "could not resolve config path: %v\n", err)
		os.Exit(1)
	}
	return p
}

func runRegister(args []string) {
	fs := flag.NewFlagSet("register", flag.ExitOnError)
	customCfg := fs.String("config", "", "config file (default: OS user-config dir)")
	orgID := fs.String("org-id", "", "organization UUID")
	devID := fs.String("developer-id", "", "developer UUID")
	token := fs.String("token", "", "agent token (server-issued)")
	url := fs.String("url", "", "Ingest base URL (https://...)")
	claudePath := fs.String("claude-code-path", "", "Claude Code local-cli-sessions root")
	agentModePath := fs.String("claude-code-agent-mode-path", "", "Claude Code local-agent-mode-sessions root (optional)")
	cursorDBPath := fs.String("cursor-db-path", "", "Cursor state.vscdb path (optional)")
	pollSeconds := fs.Int("poll-seconds", 300, "poll interval in seconds")
	_ = fs.Parse(args)

	if *orgID == "" || *devID == "" || *token == "" || *url == "" {
		fmt.Fprintln(os.Stderr, "register requires --org-id, --developer-id, --token, --url")
		os.Exit(2)
	}
	c := &config.Config{
		OrgID:                   *orgID,
		DeveloperID:             *devID,
		Token:                   *token,
		IngestURL:               *url,
		PollIntervalS:           *pollSeconds,
		ClaudeCodePath:          *claudePath,
		ClaudeCodeAgentModePath: *agentModePath,
		CursorDBPath:            *cursorDBPath,
	}
	if err := c.Validate(); err != nil {
		fmt.Fprintln(os.Stderr, err)
		os.Exit(1)
	}
	path := cfgPath(*customCfg)
	if err := config.Save(path, c); err != nil {
		fmt.Fprintf(os.Stderr, "save config: %v\n", err)
		os.Exit(1)
	}
	fmt.Printf("Registered. Config written to %s\n", path)
}

func runOnce(args []string, forever bool) {
	fs := flag.NewFlagSet("run", flag.ExitOnError)
	customCfg := fs.String("config", "", "config file")
	_ = fs.Parse(args)

	path := cfgPath(*customCfg)
	c, err := config.Load(path)
	if err != nil {
		fmt.Fprintf(os.Stderr, "load config: %v\n  hint: run `viberoi-agent register ...` first\n", err)
		os.Exit(1)
	}

	stDir := filepath.Dir(path)
	stPath := filepath.Join(stDir, "state.json")
	st, err := state.Open(stPath)
	if err != nil {
		fmt.Fprintf(os.Stderr, "open state: %v\n", err)
		os.Exit(1)
	}

	r := runner.New(c, st)
	ctx, cancel := signal.NotifyContext(context.Background(), syscall.SIGINT, syscall.SIGTERM)
	defer cancel()

	if forever {
		if err := r.RunForever(ctx); err != nil && ctx.Err() == nil {
			fmt.Fprintf(os.Stderr, "run: %v\n", err)
			os.Exit(1)
		}
		return
	}
	res, err := r.Run(ctx)
	fmt.Printf("discovered=%d pushed=%d skipped=%d failed=%d\n",
		res.Discovered, res.Pushed, res.Skipped, res.Failed,
	)
	if err != nil {
		fmt.Fprintf(os.Stderr, "run: %v\n", err)
		os.Exit(1)
	}
}
