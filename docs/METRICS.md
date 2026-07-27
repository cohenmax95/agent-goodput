# Metrics

Agent Goodput separates consumption, cost, speed, and quality. It does not turn all four into one opaque score.

## Raw tokens

The primary consumption measure is:

```text
raw tokens = input tokens + output tokens
```

Reasoning tokens are already included in provider output totals when the provider reports them that way, so they are not added a second time.

Cached input is reported separately:

```text
uncached input = input tokens - cached input tokens
```

Raw tokens are the basis for literal token-savings claims. Cache-aware or price-weighted views must not be described as literal token reduction.

## Effective tokens

An optional cost-equivalent view applies explicit weights:

```text
effective tokens =
    uncached input × uncached weight
  + cached input × cached weight
  + output × output weight
```

The default weights are 1.0, 0.1, and 8.0. They are visible configuration assumptions, not universal prices.

## Quality

Each task defines weighted obligations. An obligation can be critical.

```text
quality score =
    passed obligation weight / total obligation weight
```

Any critical failure forces quality to zero. A task contributes verified work only when every obligation passes.

## Verified goodput

```text
verified goodput =
    verified work units / effective tokens × 1,000,000
```

Failed tasks add zero work but keep all consumed tokens in the denominator. This prevents a cheap wrong answer from looking efficient.

When selective repair runs, its full usage and elapsed time are added to the
original attempt before quality or goodput is calculated. Repair cannot erase
the cost of the failed first attempt.

Deterministic completion adds no model tokens. Its local elapsed time and
success or refusal state are still reported. A completed answer contributes
verified work only after the full evaluator passes again.

Verified goodput is useful for ranking routes inside the same task suite. It is not a universal measure across unrelated benchmarks with different obligation weights.

## Promotion statistics

Candidate and baseline results are paired by task, project, and replicate. Promotion requires all of the following:

- at least 30 complete pairs;
- at least 2 independent projects;
- at least 3 task families;
- no candidate critical failures;
- candidate pass count at least baseline pass count;
- a 95% paired bootstrap lower bound on quality delta above the configured noninferiority margin;
- a 95% paired bootstrap lower bound on raw-token savings of at least 10%;
- provider-reported token usage for every paired run.

Default quality noninferiority allows at most a 1 percentage point loss at the lower confidence bound. Change that margin only before running an experiment.

## Call counts

Current Codex JSON execution output exposes cumulative token totals and item
lifecycle events, but not a reliable count of internal model requests. Agent
Goodput therefore keeps `calls` as an agent-run invocation count.

A selective repair creates a second isolated agent-run invocation, so its
combined outcome reports `calls=2`.

For isolated runs, the runner can also capture `response_cycles`. It lets Codex
write its rollout only inside the disposable execution home, counts persisted
`token_count` events with usage, retains only that integer, and deletes the
rollout with the temporary directory. In the inspected Codex runtime, one such
event is emitted after each completed sampling response. If the rollout is
missing, oversized, malformed, or conflicts with a direct Codex signal, the
field remains unknown.

Completed command executions and completed agent messages are recorded separately. They are useful process signals, but neither should be presented as an internal model-call count.

`response_cycles` is an episode signal, not a provider invoice item. Public
results must name its source and runtime version. The private-workload v6
confirmation predates this counter and reports agent-run invocations only.

## Reporting rule

Every public result should show:

- baseline and candidate pass rates;
- critical failures;
- pair, project, and task-family counts;
- raw input plus output tokens;
- cached and uncached input;
- output tokens;
- agent-run invocations;
- response cycles and coverage when the runtime exposes them;
- repair count, successful repairs, repair tokens, and repair elapsed time;
- deterministic completion attempts, refusals, successes, paths added, certificates added, matched literals, and elapsed time;
- elapsed time;
- paired confidence intervals;
- manifest and output hashes;
- rejected experiments and benchmark limitations.
