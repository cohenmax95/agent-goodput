# Agent Goodput 0.1.0-alpha.2

Alpha.2 fixes the personal plugin installation path and makes the policy
controller hands-off on Codex versions that run the `Stop` hook but do not run
`SessionEnd`.

## What changed

- The generated personal marketplace entry now resolves to
  `~/.agents/plugins/agent-goodput`.
- An alpha.1 installation with an owned legacy entry is migrated in place.
  Duplicate or unmanaged conflicting entries still stop the installer.
- The `Stop` hook runs the controller only after new verified outcomes arrive.
  A signed outcome cursor prevents duplicate work when later hooks fire.
- The evidence database is set to user-only file permissions.
- Integration instructions include first-party plugin enablement and the
  required `/hooks` review.
- The evidence site uses direct, scope-limited language and reflects the tested
  live installation.

## Compatibility and overhead

The compatibility path does not call a model. In a local 30-pair check, the
full promotion calculation completed in about 80 milliseconds. Repeated checks
with no new outcomes had a median runtime below 1 millisecond.

## Evidence boundary

This release does not add a new savings benchmark. The current claims remain:

- public synthetic confirmation: 35 of 35 tasks passed on both routes, with
  29.8% fewer raw tokens for the candidate;
- private-workload shadow: 40 of 40 candidate tasks passed, compared with 32 of
  40 on the baseline, with 39.6% fewer raw tokens for the candidate.

The private fixtures are not public, and neither result supports a universal
savings claim.

## Installation

Preview and apply the managed installation:

```bash
agp install
agp install --apply
codex plugin add agent-goodput@personal
```

Restart Codex if it was open. Then open `/hooks`, inspect the definitions, and
approve them. See the
[integration guide](https://github.com/cohenmax95/agent-goodput/blob/v0.1.0-alpha.2/docs/INTEGRATION.md).
