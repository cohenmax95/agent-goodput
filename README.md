# Agent Goodput

Save tokens only when verified work survives.

Agent Goodput is a quality-gated control layer for Codex. It measures task risk, context cost, deterministic prework, model and effort routes, tool activity, delegation overhead, and verified outcomes. Cheaper policies begin in shadow and cannot affect live execution until paired evidence establishes quality noninferiority and token savings.

[View the live evidence site](https://agent-goodput.netlify.app).

## Current evidence

The project is alpha. A preregistered 40-pair shadow derived from four private
day-to-day codebases passed every frozen gate. The candidate completed all 40
tasks, compared with 32 for the always-Sol-High baseline, while using 39.6%
fewer raw tokens overall. The 95% paired savings interval was 32.6% to 44.3%.

The private fixtures cannot be published, so that result is practical evidence,
not an independently reproducible benchmark. A separate public synthetic suite
is included so anyone can inspect the tasks, rerun the evaluator, and challenge
the method.

| Suite | Quality | Candidate raw tokens | Candidate time | Decision |
| --- | ---: | ---: | ---: | --- |
| Corrected 3-pair smoke | 3/3 vs 3/3 | 25.6% fewer overall | 25.0% less | Hold, too small and savings interval crosses zero |
| 21-pair development | 20/21 vs 20/21 | 29.1% fewer overall | 31.4% less | Reject, each route failed a different citation obligation and fewer than 30 pairs |
| 35-pair confirmation v1 | 34/35 vs 34/35 | 30.7% fewer overall | 32.0% less | Reject, hidden lexical obligations caused different failures |
| 35-pair confirmation v2 | 35/35 vs 35/35 | 29.8% fewer overall | 31.0% less | Pass, canary eligible inside the tested envelope |
| 32-pair private-workload confirmation v1 | 27/32 vs 25/32 | 37.1% fewer overall | 38.5% less | Reject, deterministic evidence obligations failed |
| 32-pair private-workload confirmation v2 | 31/32 vs 31/32 | 29.6% fewer recorded, not claimable | 54.7% less | Reject, one candidate repair failed and one baseline run lacked exact usage |
| 32-pair private-workload confirmation v3 | 31/32 vs 28/32 | 28.8% fewer overall | 23.6% less | Reject, targeted repair failed 4 of 7 times |
| 40-pair private-workload confirmation v5 | 37/40 vs 38/40 | 40.0% fewer overall | 44.6% less | Reject, two candidate critical failures |
| 40-pair private-workload confirmation v6 | 32/40 vs 40/40 | 39.6% fewer overall | 42.5% less | Pass, canary eligible inside the tested envelope |

In private-workload confirmation v6, the candidate kept 15 safety-sensitive
tasks on Sol High and routed 25 bounded read tasks to Terra Medium. It made
exactly one Codex agent-run invocation per task, the same as the baseline.
That frozen run predates Agent Goodput's privacy-safe response-cycle counter,
so it makes no internal-cycle claim. Two answers needed mechanical evidence
completion. A fail-closed local compiler added two certificates in 2
milliseconds total, without a second Codex run, and the unchanged evaluator
revalidated each complete answer. Every execution used provider-reported
usage.

The reproducible synthetic confirmation remains a separate result. Both routes
passed all 35 public tasks. The candidate used 29.8% fewer raw tokens overall,
with a 95% paired savings interval from 25.5% to 34.4%, and finished 31.0%
faster.

Five earlier private-workload iterations were rejected or held even when they
used fewer tokens. Those failures exposed unwired repair, missing exact usage,
stochastic model repair, and overly narrow deterministic evidence rules. None
was rescored. The v6 claim comes from a fresh preregistration, new run labels,
new randomization, and a frozen implementation.

See [confirmation v2 results](docs/RESULTS.md), [negative and developmental
results](docs/NEGATIVE_RESULTS.md), and the [sanitized per-run
evidence](benchmarks/results/README.md).

These results do not prove savings on every repository, writing task, browser
workflow, or production action. The maintainer's Codex installation runs the
plugin in observation and shadow mode. The plugin cannot replace the model for
a task that is already running.

## The problem

Most efficiency tools optimize one surface:

- compress shell output;
- compress context;
- index a repository;
- route to a cheaper model;
- add subagents;
- report token totals.

Each can help. Each can also create a cheap wrong answer or add more agent steps than it removes.

Agent Goodput evaluates the combined policy:

```text
model + reasoning effort + context + deterministic work + tools + delegation
```

Savings count only when task-specific obligations pass.

## What it includes

- Conservative task classification with negation-aware action detection
- Sol High as the proven baseline
- Terra Medium candidates only for bounded low-risk reading
- Sol Medium candidates for bounded local changes
- Sol High retention for security, high-stakes, sensitive, broad, external, architecture, and explicit maximum-quality work
- Exact context-source audits with source labels
- Required, conditional, and optional context compilation
- Deterministic inventory, diff, log filtering, and schema prework
- Fail-closed deterministic completion for verifier-reported, task-explicit lexical evidence gaps
- Delegation return-on-investment and independence gates
- Optional targeted model repair with complete revalidation and cumulative accounting
- Exact cumulative accounting for initial and repair executions
- Provider-reported token accounting separated from cache and cost views
- Privacy-safe response-cycle counts from disposable isolated Codex rollouts
- Deterministic task obligations and safety-critical zeroing
- Paired bootstrap confidence intervals
- Shadow, canary, active, and rolled-back policy phases
- Fresh evidence at every phase
- Signed policy snapshots and an atomic hash-chained evidence ledger
- Privacy-safe Codex lifecycle hooks
- Dry-run-first, hash-owned installation and uninstall
- Randomized, resumable paired benchmarks
- Public-result sanitization with provenance hashes

## Quick start

```bash
git clone https://github.com/cohenmax95/agent-goodput.git
cd agent-goodput
python3 -m venv .venv
. .venv/bin/activate
python -m pip install -e .
```

Inspect the system without installing anything:

```bash
agp doctor
agp policy show
agp route "Read this small repository and explain the request flow."
```

Run deterministic prework:

```bash
agp preflight --cwd . inventory diff-summary
```

Audit context cost:

```bash
agp context audit AGENTS.md pyproject.toml
```

Preview plugin installation:

```bash
agp install
```

Installation and policy mutation are dry-run by default. See
[integration](docs/INTEGRATION.md) before applying either. After reviewing the
plan, install and enable the plugin:

```bash
agp install --apply
codex plugin add agent-goodput@personal
```

Restart Codex if it was open, then use `/hooks` to review and trust the exact
hook definitions. Codex does not let a third-party installer bypass that trust
step.

## Quality gate

A candidate cannot advance unless all configured requirements pass:

- at least 30 paired outcomes;
- at least 2 projects;
- at least 3 task families;
- no candidate critical failures;
- candidate pass count at least baseline pass count;
- a 95% paired quality-noninferiority bound within 1 percentage point;
- a 95% paired raw-token-savings lower bound of at least 10%;
- provider-reported usage for every pair.

Failed attempts contribute zero verified work and keep all their tokens in the denominator.

## Hands-off policy-state lifecycle

Codex lifecycle hooks cannot change the model selected for the task already
running. The plugin is therefore an observation and policy-state surface, not a
silent model interceptor. Actual route enforcement happens through `agp run` or
another harness adapter that can select a model before execution.

After an intentional plugin install, the hooks can:

1. classify a task and add one compact route certificate;
2. keep the policy target on the baseline while a candidate is in shadow;
3. count selected tool events without retaining tool output;
4. evaluate outcomes ingested by a verifier or benchmark adapter;
5. run one bounded evaluation after new outcomes arrive at turn or session end;
6. canary, promote, hold, or roll back from signed policy state.

Outcome ingestion requires an evaluator or benchmark adapter. A generic hook
cannot prove an arbitrary real-world answer correct. Hooks fail open because
lifecycle hooks are not a complete security boundary. Missing telemetry never
makes a cheaper route eligible.

## Benchmark

Benchmark manifests are executable local configuration. Run only manifests you
trust.

Run the small plumbing suite:

```bash
agp benchmark run benchmarks/manifests/codex-smoke-v1.json
```

Resume an interrupted benchmark:

```bash
agp benchmark run \
  benchmarks/manifests/codex-confirmatory-v1.json \
  --resume benchmark-results/codex-confirmatory-v1-EXAMPLE
```

Create a public-safe report:

```bash
agp benchmark sanitize \
  benchmark-results/codex-confirmatory-v1-EXAMPLE/report.json \
  --output benchmarks/results/codex-confirmatory-v1.json
```

The sanitizer rejects raw-answer fields and private filesystem paths. It replaces run identifiers and attaches source and public-payload hashes.
For non-public fixtures, add `--redact-obligation-evidence` so evaluator details
are replaced with hashes instead of exposing relative source paths or literals.

## Privacy

The evidence ledger rejects common fields for:

- raw prompts;
- model output;
- tool input and output;
- credentials and secrets;
- transcripts.

Hook telemetry uses digests, keyed project identifiers, allowlisted reason codes, aggregate counters, and hashes. This is a strong default, not a substitute for reviewing custom metadata.

## Documentation

- [Confirmation results](docs/RESULTS.md)
- [Architecture](docs/ARCHITECTURE.md)
- [Metrics](docs/METRICS.md)
- [Benchmark protocol](docs/BENCHMARK_PROTOCOL.md)
- [Threat model](docs/THREAT_MODEL.md)
- [Competitive audit](docs/COMPETITIVE_AUDIT.md)
- [Prior art and clean-room policy](docs/PRIOR_ART.md)
- [Limitations](docs/LIMITATIONS.md)
- [Publication checklist](docs/PUBLICATION_CHECKLIST.md)
- [Alpha.2 release notes](docs/RELEASE_NOTES_0.1.0-alpha.2.md)
- [Alpha.1 release notes](docs/RELEASE_NOTES_0.1.0-alpha.1.md)
- [Security policy](SECURITY.md)
- [Contributing](CONTRIBUTING.md)
- [Changelog](CHANGELOG.md)

## License

Apache-2.0. See [LICENSE](LICENSE).
