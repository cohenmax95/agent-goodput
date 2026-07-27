# Agent Goodput 0.1.0-alpha.1

Agent Goodput is a quality-gated control layer for Codex. It measures the full
route, including context, deterministic work, model effort, tools, and
delegation, then counts savings only when task-specific obligations pass.

This alpha ships with two separate evidence sets:

- A public 35-pair synthetic confirmation where both routes passed all 35 task
  contracts and the candidate used 29.8% fewer raw tokens overall. The 95%
  paired savings interval was 25.5% to 34.4%.
- A sanitized 40-pair shadow derived from four private application codebases.
  The candidate passed 40 of 40 contracts, compared with 32 of 40 for the
  always-Sol-High baseline, while using 39.6% fewer raw tokens overall. The
  proprietary fixtures are not public, so this is practical evidence rather
  than an independently reproducible benchmark.

The release includes conservative routing, measured context compilation,
deterministic prework, delegation return-on-investment gates, selective repair,
fail-closed lexical evidence completion, signed policy state, a hash-chained
evidence ledger, privacy-safe Codex hooks, staged promotion and rollback,
isolated response-cycle attribution, and dry-run-first installation.

Five private-workload development runs were rejected or held before v6. Those
negative results remain documented. No route is installed or promoted from a
benchmark alone, and this release does not change a user's live Codex
configuration.

The release workflow builds the wheel and source archive from the tagged
commit, publishes SHA-256 checksums, and records GitHub build provenance.

Verify downloaded files:

```bash
sha256sum --check SHA256SUMS
gh attestation verify agent_goodput-0.1.0a1-py3-none-any.whl \
  --repo cohenmax95/agent-goodput
```

Start with the dry-run commands in the
[integration guide](https://github.com/cohenmax95/agent-goodput/blob/v0.1.0-alpha.1/docs/INTEGRATION.md).
