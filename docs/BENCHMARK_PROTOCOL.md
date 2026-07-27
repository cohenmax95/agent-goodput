# Benchmark protocol

The benchmark asks a narrow question: can a candidate routing policy complete the same verified work as an always-baseline policy while using fewer provider-reported tokens?

## Design

Each task defines:

- a synthetic fixture;
- one task instruction;
- a project and task-family label;
- a baseline route;
- a candidate route;
- one or more deterministic evaluators;
- criticality for each evaluator;
- repeated run labels.

A variant may also declare one stronger repair route and the evaluator types
eligible for independent repair. Repair is part of the candidate policy under
test, not an after-the-fact rescore.

A variant may declare deterministic evidence completion. This is also part of
the candidate policy under test. It runs only after evaluation and only when
every failure is a missing path or a task-explicit missing evidence literal.

The runner expands each task into baseline and candidate executions, shuffles the full execution order with a recorded randomization seed, creates a fresh workspace for every execution, and removes it after artifacts are hashed.

An atomic checkpoint is written after every execution. A resumed run must match both the canonical manifest hash and the benchmark bundle hash. The bundle covers referenced instructions, fixtures, schemas, driver files, package configuration, and Agent Goodput runtime source.

A confirmatory manifest can also pin the exact Codex binary, reported version,
and SHA-256 checksum. The runner checks the lock before and after execution and
stops if the runtime drifts.

Codex runs use a fresh temporary home linked only to authentication. User configuration, project rules, plugins, hooks, browser surfaces, and multi-agent behavior are disabled. This isolates the route under test from a personal setup.

## Development and confirmation

Use three stages:

1. Unit tests validate the harness and evaluators.
2. A small smoke suite finds plumbing defects and ambiguous tasks. It cannot support a savings claim.
3. A preregistered confirmatory suite is frozen before execution and must meet the production evidence threshold.

If a task or evaluator changes after results are viewed, increment the manifest version. Keep the prior run as a negative or developmental result.

## Quality rules

- A run passes only if every obligation passes.
- Any critical evaluator failure sets quality to zero.
- Candidate savings are rejected if the candidate has any critical failure.
- Estimated token usage cannot promote a route.
- The baseline and candidate must receive the same task contract and equivalent workspace permissions.
- A candidate may receive deterministic prework only when that prework is part of the policy being evaluated and its tokens are included in the candidate total.
- Deterministic completion may use only verifier-reported missing paths and
  missing literals already present in the original task or answer. It may not
  consume the expected conclusion, hidden required facts, or a private oracle
  answer.
- Source search is limited to verifier-reported missing paths plus paths already
  cited by the answer. A literal-only failure cannot introduce an evaluator-only
  path.
- Every completed path must resolve to a bounded regular file inside the
  disposable workspace and contain a matching source line. A reported literal
  may be sourced from a different answer-cited path, but it must occur exactly
  in the selected source line. Otherwise completion fails closed.
- Completion cannot alter the conclusion or existing evidence. The complete
  answer is re-evaluated, its local elapsed time remains in the candidate total,
  and the certificate does not copy raw source lines.
- Selective repair runs at most once and only when every failed evaluator type is explicitly allowlisted in the frozen manifest.
- A targeted repair receives a compact failed-obligation packet, not raw prior
  reasoning or tool output. A clean retry receives the original task contract
  and no targeted failure packet.
- The complete repaired answer is evaluated from scratch. Previously passed fields are not assumed to remain correct.
- Initial and repair input, cached input, output, reasoning, elapsed time,
  agent-run counts, and response cycles when available are added together.
- A repair with missing or mixed usage cannot support promotion.
- Baseline and candidate repair behavior must be stated explicitly in the manifest and result.

## Statistics

The report includes aggregate totals and paired means. Promotion uses paired bootstrap confidence intervals over task-level quality deltas and raw-token savings.

The default gate requires:

- 30 pairs;
- 2 projects;
- 3 task families;
- 95% confidence;
- quality noninferiority within 1 percentage point;
- at least 10% raw-token savings at the lower confidence bound;
- no candidate critical failures;
- candidate pass count at least baseline pass count.

Repeated labels create independent model executions, not deterministic model seeds. Codex currently does not expose a seed control through this runner.

## Reproduction

```bash
python -m agent_goodput.cli benchmark run \
  benchmarks/manifests/codex-full-v1.json \
  --output benchmark-results
```

Retaining raw synthetic answers is optional:

```bash
python -m agent_goodput.cli benchmark run \
  benchmarks/manifests/codex-full-v1.json \
  --output benchmark-results \
  --retain-outputs
```

Do not enable raw output retention on private tasks unless the output directory is protected and excluded from version control.

Task instructions, repair packets, and deterministic completion workspaces are
stored only in temporary paths and removed with the disposable execution state
during normal completion.

Resume from the benchmark directory after an interruption:

```bash
python -m agent_goodput.cli benchmark run \
  benchmarks/manifests/codex-full-v1.json \
  --resume benchmark-results/codex-full-v1-EXAMPLE
```

## Required publication artifacts

- exact manifest;
- fixture and evaluator source;
- Codex and Python versions;
- randomized execution order;
- per-run route, usage, elapsed time, obligation outcomes, and output digest;
- whether selective repair was configured, invoked, and successful;
- whether deterministic completion was eligible, applied, and successful,
  including attempt, refusal, path, certificate, matched-literal, and
  elapsed-time counts;
- cumulative usage plus the repair-only token and time contribution;
- aggregate and paired statistics;
- manifest digest;
- rejected experiments;
- a sanitizer report showing that no private paths or raw answers are published.
