// Package ingest is the HTTP client to the Ingest service.
//
// Bearer auth, three identifying headers, exponential backoff with jitter.
// One method per endpoint; callers never construct URLs by hand.
//
// Privacy: never log the request body, the token, or anything that could
// echo it. Logs carry endpoint, status, attempt count, duration.
package ingest

import (
	"bytes"
	"context"
	"encoding/json"
	"errors"
	"fmt"
	"io"
	"math/rand/v2"
	"net/http"
	"strings"
	"time"

	"github.com/viberoi/viberoi/agent/pkg/schema"
)

const (
	maxAttempts        = 4
	baseBackoff        = 500 * time.Millisecond
	maxBackoff         = 10 * time.Second
	requestTimeout     = 30 * time.Second
	contentTypeJSON    = "application/json"
)

// ErrAuth is returned when the server rejects our credentials. The runner
// surfaces this as a hard stop (no point retrying with the same token).
var ErrAuth = errors.New("ingest: unauthorized")

// Client posts sessions to the Ingest service.
type Client struct {
	BaseURL     string // e.g. https://ingest.viberoi.io
	Token       string // Argon2id-verified server side; never log
	OrgID       string
	DeveloperID string
	UserAgent   string // identifies agent version

	HTTP *http.Client // if nil, http.Client{Timeout: requestTimeout} is used
}

// PushOne posts a single session. Idempotent server-side
// (unique on org_id + session_id), so re-running is safe.
func (c *Client) PushOne(ctx context.Context, s schema.Session) error {
	return c.do(ctx, "/ingest/session", s)
}

// PushBatch posts up to 100 sessions in one call. Server returns 422 if
// the batch is larger than its limit; callers should chunk.
func (c *Client) PushBatch(ctx context.Context, sessions []schema.Session) error {
	if len(sessions) == 0 {
		return nil
	}
	return c.do(ctx, "/ingest/sessions", sessions)
}

func (c *Client) do(ctx context.Context, path string, payload any) error {
	if c.BaseURL == "" {
		return errors.New("ingest: BaseURL empty")
	}
	if c.Token == "" || c.OrgID == "" || c.DeveloperID == "" {
		return errors.New("ingest: auth fields missing")
	}

	body, err := json.Marshal(payload)
	if err != nil {
		return fmt.Errorf("ingest: marshal: %w", err)
	}
	url := strings.TrimRight(c.BaseURL, "/") + path

	httpClient := c.HTTP
	if httpClient == nil {
		httpClient = &http.Client{Timeout: requestTimeout}
	}

	var lastErr error
	for attempt := 1; attempt <= maxAttempts; attempt++ {
		req, err := http.NewRequestWithContext(
			ctx, http.MethodPost, url, bytes.NewReader(body),
		)
		if err != nil {
			return fmt.Errorf("ingest: build request: %w", err)
		}
		req.Header.Set("Authorization", "Bearer "+c.Token)
		req.Header.Set("X-VibeROI-Org-Id", c.OrgID)
		req.Header.Set("X-VibeROI-Developer-Id", c.DeveloperID)
		req.Header.Set("Content-Type", contentTypeJSON)
		req.Header.Set("Accept", contentTypeJSON)
		if c.UserAgent != "" {
			req.Header.Set("User-Agent", c.UserAgent)
		}

		resp, err := httpClient.Do(req)
		if err != nil {
			lastErr = err
		} else {
			func() {
				defer resp.Body.Close()
				if resp.StatusCode == http.StatusUnauthorized ||
					resp.StatusCode == http.StatusForbidden {
					lastErr = ErrAuth
					return
				}
				if resp.StatusCode >= 200 && resp.StatusCode < 300 {
					// Drain so the connection can be reused.
					_, _ = io.Copy(io.Discard, resp.Body)
					lastErr = nil
					return
				}
				lastErr = fmt.Errorf(
					"ingest: %s returned status %d", path, resp.StatusCode,
				)
			}()
		}

		if lastErr == nil {
			return nil
		}
		if errors.Is(lastErr, ErrAuth) {
			return lastErr // never retry — caller revokes
		}
		if ctx.Err() != nil {
			return ctx.Err()
		}
		if attempt == maxAttempts {
			break
		}
		// Exponential backoff with full jitter.
		wait := time.Duration(1<<(attempt-1)) * baseBackoff
		if wait > maxBackoff {
			wait = maxBackoff
		}
		jittered := time.Duration(rand.Int64N(int64(wait) + 1))
		select {
		case <-ctx.Done():
			return ctx.Err()
		case <-time.After(jittered):
		}
	}
	return lastErr
}
