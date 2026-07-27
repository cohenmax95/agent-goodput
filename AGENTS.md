# Agent instructions

## Objective

Improve verified useful work per token without lowering quality.

## Required behavior

- Inspect the smallest relevant source set before editing.
- Use deterministic local checks before agent reasoning when they answer the question directly.
- Preserve the baseline, privacy boundary, dry-run defaults, and rollback behavior.
- Never convert estimated token usage into a reported measurement.
- Never treat tool events, response cycles, or one runner invocation as an
  exact provider-request count. Keep each signal separate and source-labeled.
- Never weaken evaluators or delete negative results to improve a benchmark.
- Do not retain raw prompts, model outputs, tool inputs, tool outputs, credentials, transcripts, or private project paths.
- Do not inspect or copy source from proprietary, preview-only, or incompatible-license projects.
- Use synthetic fixtures for tests.
- Run focused tests after each change and the full local quality suite before handoff.
- Do not publish, push, install globally, or mutate a live Codex setup unless the user explicitly asks.

## Architecture boundaries

- `classify.py` extracts conservative task features.
- `policy.py` decides baseline, shadow, canary, and active routes.
- `context.py` measures and compiles context without silently dropping required material.
- `preflight.py` performs deterministic work outside the reasoning loop.
- `evidence.py` stores privacy-safe, hash-chained outcomes.
- `stats.py` owns promotion statistics.
- `controller.py` owns transitions and rollback.
- `hook.py` adapts Codex lifecycle events and must remain fail-open.
- `installer.py` owns only files recorded in its hash ledger.
- `benchmark.py` must keep paired execution, fresh workspaces, deterministic evaluators, and source-labeled usage.

## Public writing

State what the evidence proves and what it does not. Show quality gates beside savings. Do not use attention metrics, feature counts, or a smoke test as proof of superior runtime performance.
