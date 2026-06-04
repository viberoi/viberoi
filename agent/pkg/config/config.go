// Package config loads + persists the agent's local config.
//
// Default location: $XDG_CONFIG_HOME/viberoi/config.yaml on Linux/Mac;
// %APPDATA%\viberoi\config.yaml on Windows; fall back to ~/.viberoi/
// when neither env var is set. Permissions: 0600 (owner read+write).
//
// Token is plaintext at rest — there's no derivation we can do on the
// agent side that's stronger than chmod 0600. Real production hardening
// would store it in the OS keyring; that's V2.
package config

import (
	"errors"
	"fmt"
	"os"
	"path/filepath"
	"runtime"
	"time"

	"gopkg.in/yaml.v3"
)

// Config is the on-disk shape.
type Config struct {
	OrgID          string `yaml:"org_id"`
	DeveloperID    string `yaml:"developer_id"`
	Token          string `yaml:"token"`
	IngestURL      string `yaml:"ingest_url"`
	PollIntervalS  int    `yaml:"poll_interval_seconds"`
	ClaudeCodePath string `yaml:"claude_code_path,omitempty"`
	// Root containing Claude Code AGENT MODE (Cowork) audit logs:
	// `%APPDATA%\Claude\local-agent-mode-sessions\`. Empty = skip AGENT MODE.
	ClaudeCodeAgentModePath string `yaml:"claude_code_agent_mode_path,omitempty"`
	// Path to the Cursor SQLite file
	// (`%APPDATA%\Cursor\User\globalStorage\state.vscdb`). Empty = skip Cursor.
	CursorDBPath string `yaml:"cursor_db_path,omitempty"`
}

// Validate returns an error if any required field is missing.
func (c *Config) Validate() error {
	missing := []string{}
	if c.OrgID == "" {
		missing = append(missing, "org_id")
	}
	if c.DeveloperID == "" {
		missing = append(missing, "developer_id")
	}
	if c.Token == "" {
		missing = append(missing, "token")
	}
	if c.IngestURL == "" {
		missing = append(missing, "ingest_url")
	}
	if len(missing) > 0 {
		return fmt.Errorf("config missing required fields: %v", missing)
	}
	if c.PollIntervalS == 0 {
		c.PollIntervalS = 300 // 5 min default
	}
	return nil
}

// PollInterval returns PollIntervalS as a duration with a sane floor.
func (c *Config) PollInterval() time.Duration {
	d := time.Duration(c.PollIntervalS) * time.Second
	if d < 30*time.Second {
		return 30 * time.Second
	}
	return d
}

// DefaultDir returns the config dir for the current OS, creating it if
// it doesn't exist.
func DefaultDir() (string, error) {
	var base string
	switch runtime.GOOS {
	case "windows":
		base = os.Getenv("APPDATA")
		if base == "" {
			home, err := os.UserHomeDir()
			if err != nil {
				return "", err
			}
			base = filepath.Join(home, "AppData", "Roaming")
		}
	default:
		base = os.Getenv("XDG_CONFIG_HOME")
		if base == "" {
			home, err := os.UserHomeDir()
			if err != nil {
				return "", err
			}
			base = filepath.Join(home, ".config")
		}
	}
	dir := filepath.Join(base, "viberoi")
	if err := os.MkdirAll(dir, 0o700); err != nil {
		return "", err
	}
	return dir, nil
}

// Path returns the default config file path.
func Path() (string, error) {
	dir, err := DefaultDir()
	if err != nil {
		return "", err
	}
	return filepath.Join(dir, "config.yaml"), nil
}

// Load reads the config from `path`, validates it, and returns it.
func Load(path string) (*Config, error) {
	data, err := os.ReadFile(path)
	if err != nil {
		return nil, err
	}
	var c Config
	if err := yaml.Unmarshal(data, &c); err != nil {
		return nil, fmt.Errorf("config yaml invalid: %w", err)
	}
	if err := c.Validate(); err != nil {
		return nil, err
	}
	return &c, nil
}

// Save writes the config to `path` with 0600 perms.
func Save(path string, c *Config) error {
	if c == nil {
		return errors.New("nil config")
	}
	if err := os.MkdirAll(filepath.Dir(path), 0o700); err != nil {
		return err
	}
	data, err := yaml.Marshal(c)
	if err != nil {
		return err
	}
	return os.WriteFile(path, data, 0o600)
}
