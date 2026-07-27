---
name: agent-goodput
description: Measure and improve agent token efficiency without lowering verified task quality. Use for model or effort routing, context-cost audits, delegation decisions, paired benchmarks, efficiency claims, policy promotion, and rollback.
---

# Agent Goodput

Optimize only inside a verified quality envelope.

## Rules

1. Keep the current proven route as the baseline.
2. Measure raw input, cached input, output, calls, elapsed time, and task outcome separately.
3. Label estimates as estimates. Never use estimated token counts to promote a policy.
4. Run deterministic inventory, filtering, diff, schema, and test work before asking a model to reason over the same data.
5. Start every cheaper model, lower effort, compressed context, or delegation policy in shadow mode.
6. Score task obligations with deterministic checks. A safety-critical failure makes verified work zero.
7. Require paired evidence, multiple projects, multiple task families, a quality-noninferiority confidence bound, and a positive raw-token-savings confidence bound before a canary.
8. Advance through shadow, canary, and active states. Roll back on any critical failure or integrity error.
9. Escalate only failed obligations. Do not rerun already verified work unless dependencies make the partial result invalid.
10. Never store raw prompts, model outputs, tool inputs, credentials, transcripts, or project paths in telemetry.
11. Use deterministic completion only for verifier-reported missing paths and task-explicit evidence literals verified in bounded source. Search only verifier-missing and answer-cited paths. Fail closed on hidden facts, semantic, conclusion, execution, forbidden-fact, or unsafe failures.

## Workflow

1. Run `agp classify` or `agp route` on the task.
2. Run the recommended deterministic preflight steps.
3. Audit context sources with `agp context audit`.
4. Use `agp delegate` before spawning support agents.
5. Execute the applied route through `agp run` or another pre-execution harness.
   Lifecycle hooks only observe and maintain policy state; they do not switch the
   model for a task already running. Treat shadow candidates as observations only.
6. Ingest reported usage and deterministic obligation results.
7. Run `agp policy evaluate`. Apply a transition only when every gate passes.
8. Present raw measurements, quality results, confidence bounds, rejected experiments, and limitations together.

Read `references/metrics.md` before making a public savings claim.
