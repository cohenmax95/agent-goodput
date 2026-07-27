# Changelog

Agent Goodput follows semantic versioning. Alpha releases may change command
and plugin interfaces while the evidence model is tested on more workloads.

## 0.1.0-alpha.2 - 2026-07-27

### Fixed

- Corrected the personal marketplace path so Codex resolves the installed
  plugin under `~/.agents/plugins/agent-goodput`.
- Added an owned migration from the alpha.1 marketplace entry. Conflicting or
  duplicate unmanaged entries still stop installation.

### Changed

- The turn-completion hook now runs one controller cycle when new verified
  outcomes exist. A signed outcome cursor makes later turn or session hooks a
  sub-millisecond no-op until more outcomes arrive.
- Evidence databases are created with user-only file permissions.
- Installation instructions now include first-party plugin enablement and
  explicit hook review.
- Site copy now states the benchmark scope, live-install boundary, and quality
  gates directly.

## 0.1.0-alpha.1 - 2026-07-26

First public alpha.

### Added

- Conservative task classification and model-effort routing with Sol High as
  the baseline.
- Measured context compilation and deterministic prework.
- Delegation return-on-investment gates.
- Task-specific obligation scoring, critical-failure zeroing, paired bootstrap
  intervals, and verified-goodput reporting.
- Shadow, canary, active, and rollback policy phases backed by a signed,
  hash-chained SQLite evidence ledger.
- One-shot selective repair and fail-closed deterministic lexical evidence
  completion with full revalidation.
- Privacy-safe Codex lifecycle hooks and dry-run-first managed installation.
- Installer refusal for unmanaged, modified, or symlinked destination paths.
- Isolated Codex runner with exact token usage and aggregate response-cycle
  attribution from disposable rollouts.
- Reproducible synthetic benchmark evidence and a sanitized private-workload
  confirmation.

### Evidence boundary

The private-workload confirmation passed its frozen gates, but its proprietary
fixtures are not public. The synthetic confirmation is the independently
reproducible proof. Neither result supports a universal savings claim.
