// Package machineid produces a stable per-machine identifier.
//
// Used to populate `developers.machine_id_hash` (DB) so the backend can
// detect cross-org device reuse and meter per-active-device billing
// (Master spec § 2399-2413).
//
// The returned value is a sha256 hex of (hostname | GOOS | GOARCH). Not
// a secret — just a stable fingerprint that survives across agent
// restarts and is consistent for a given laptop/workstation. We avoid
// MAC address / Windows MachineGuid / /etc/machine-id for now since
// those need platform-specific syscalls and the hostname-derived hash
// is sufficient for V1 dedup. Bump the payload format if you need
// stricter cross-OS-reinstall stability.
package machineid

import (
	"crypto/sha256"
	"encoding/hex"
	"os"
	"runtime"
)

// Get returns the stable per-machine hex hash. Never empty (falls back
// to "unknown" hostname if os.Hostname errors).
func Get() string {
	host, _ := os.Hostname()
	if host == "" {
		host = "unknown"
	}
	payload := host + "|" + runtime.GOOS + "|" + runtime.GOARCH
	h := sha256.Sum256([]byte(payload))
	return hex.EncodeToString(h[:])
}
