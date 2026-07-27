# Negative and developmental results

Failed and inconclusive experiments stay visible. Token reduction does not become a win when the quality or measurement gate fails.

## Smoke 1: evaluator path defect

Benchmark: `codex-smoke-v1-f41a0c7761fa`

- Baseline pass rate: 0 of 3
- Candidate pass rate: 0 of 3
- Aggregate raw-token difference: candidate used 43.3% fewer
- Disposition: rejected

The answer evaluator did not normalize ordinary line citations such as `path.py:12-18` and absolute temporary-workspace citations. Correctly cited answers therefore failed. The result says nothing useful about route quality or savings.

Fix: normalize supported line-citation formats and validate paths by exact relative suffix. A regression test now covers both formats.

## Smoke 2: brittle and ambiguous contracts

Benchmark: `codex-smoke-v1-fb92de1dc790`

- Baseline pass rate: 2 of 3
- Candidate pass rate: 2 of 3
- Aggregate raw-token difference: candidate used 33.4% fewer
- Candidate critical failures: 1
- Paired quality-delta interval: -1.0 to 1.0
- Paired raw-token-savings interval: -1.3% to 55.0%
- Disposition: rejected

The failures were not the same:

- The baseline security answer described an `@unittest.skip` regression test, while the evaluator required the exact word `skipped`.
- The SMS task asked which field “overrides” the webhook. One candidate answer selected the boolean field controlling precedence instead of the URL field carrying the actual destination.

Fix: require the stem `skip` and ask specifically for the dotted field that supplies the destination URL. The old result remains rejected.

## Smoke 3: clean but underpowered

Benchmark: `codex-smoke-v1-6397c1c1550a`

- Baseline pass rate: 3 of 3
- Candidate pass rate: 3 of 3
- Baseline raw tokens: 142,848
- Candidate raw tokens: 106,308
- Aggregate raw-token difference: candidate used 25.6% fewer
- Baseline elapsed time: 60.1 seconds
- Candidate elapsed time: 45.1 seconds
- Paired quality-delta interval: 0.0 to 0.0
- Paired raw-token-savings interval: -1.0% to 39.2%
- Disposition: hold

The corrected smoke suite preserved every tested obligation. It still cannot support promotion or a broad savings claim:

- only three pairs were run;
- one high-risk task used the same Sol High route on both sides and was approximately flat;
- the lower confidence bound on savings was below zero;
- the production threshold requires at least 30 pairs.

The smoke suite justified running a larger development benchmark. It did not justify changing a live route.

## Full development v1: savings signal, quality hold

Benchmark: `codex-full-v1-c6cc9924c810`

- Pairs: 21 across 7 synthetic projects and 7 task families
- Baseline pass rate: 20 of 21
- Candidate pass rate: 20 of 21
- Baseline raw tokens: 1,180,197
- Candidate raw tokens: 836,320
- Aggregate raw-token difference: candidate used 29.1% fewer
- Paired mean raw-token savings: 30.4%
- Paired raw-token-savings interval: 23.4% to 36.6%
- Baseline elapsed time: 517.8 seconds
- Candidate elapsed time: 355.1 seconds
- Candidate critical failures: 1
- Disposition: rejected

Both failures occurred on `config-precedence`, but they were different:

- One Terra Medium answer returned the correct conclusion and named the task layer, but cited only `router/config.py` and omitted `tests/test_config.py`.
- One Sol High answer returned the correct conclusion and cited both required files, but did not explicitly use the word `task` in its evidence fact.

The task instruction said to read the resolver and test but did not explicitly say to cite both or identify the layer that sets final effort. The evaluator required both.

Fix: create a new confirmatory instruction that states those citation obligations directly. The development result remains rejected. Fresh execution labels are used for confirmation, and the new bundle hash covers the manifest, instructions, fixtures, runner, and runtime source.

## Confirmatory v1: hidden lexical contracts

Benchmark: `codex-confirmatory-v1-50e49852ad2c`

- Pairs: 35 across 7 synthetic projects and 7 task families
- Baseline pass rate: 34 of 35
- Candidate pass rate: 34 of 35
- Baseline raw tokens: 1,962,177
- Candidate raw tokens: 1,360,257
- Aggregate raw-token difference: candidate used 30.7% fewer
- Paired mean raw-token savings: 30.2%
- Paired raw-token-savings interval: 24.6% to 35.5%
- Baseline elapsed time: 880.6 seconds
- Candidate elapsed time: 599.0 seconds
- Candidate critical failures: 1
- Disposition: rejected

Both failed answers reached the correct conclusion and cited the required files.
The hidden lexical checks were not fully stated in the task:

- One Terra Medium log diagnosis described the false number-level switch but
  did not spell the identifier `useInboundWebhookOnNumber`.
- One Sol High mailbox answer wrote `scan-history` rather than the exact source
  identifier `scan_history`.

The failures occurred in different pairs, so the paired quality interval was
-8.6 to 8.6 percentage points. Quality noninferiority was not established.
These answers are not rescored after the fact.

The run also resolved the ChatGPT app's Codex 0.146 alpha binary, while the
pre-run note referenced the separate Codex app's 0.144 binary. Every recorded
execution used the same 0.146 version, but the environment note was wrong.

Fix: version both affected task instructions so the exact lexical requirements
are visible to both routes, use fresh run labels and randomization, and add a
fail-closed runtime lock that checks the exact Codex version and binary checksum
before and after execution. V1 remains rejected.

## Private real-workload confirmatory v1: selective repair was not wired

Benchmark: `real-workload-confirmatory-v1-596dc5214d49`

- Pairs: 32 across 4 private projects and 8 task families
- Baseline pass rate: 27 of 32
- Candidate pass rate: 25 of 32
- Baseline raw tokens: 1,944,860
- Candidate raw tokens: 1,222,994
- Aggregate raw-token difference: candidate used 37.1% fewer
- Paired mean raw-token savings: 36.2%
- Paired raw-token-savings interval: 29.7% to 42.1%
- Baseline elapsed time: 979.3 seconds
- Candidate elapsed time: 602.2 seconds
- Candidate critical failures: 7
- Paired quality-delta interval: -25.0 to 9.4 percentage points
- Disposition: rejected

The task conclusions were correct in every failed execution. The failures were
still legitimate because the answers omitted explicit evidence obligations:

- nine missing source or regression-evidence paths;
- three missing exact verification facts;
- some answers missed more than one obligation.

Sol High also failed five executions, which showed that this was not only a
cheaper-model problem. The evaluator was not weakened and the answers were not
rescored. The candidate completed fewer verified tasks, had critical failures,
and did not establish quality noninferiority.

The run exposed an implementation gap. `escalation.py` could construct and
merge a failed-obligation repair, but the benchmark adapter stopped after the
first answer. The documented system behavior and the measured execution path
did not match.

Fix: wire one manifest-declared stronger repair into the benchmark adapter.
Repair is permitted only when every failed evaluator type is allowlisted. The
adapter sends a compact failure packet, revalidates the complete replacement
answer, counts both executions, and fails closed after one repair. V1 remains a
negative result, and any new confirmation requires a new source commit, bundle
hash, randomization, and fresh run labels.

## Selective-repair fault-injection smoke

Benchmark: `real-workload-repair-smoke-v1-8388e4423338`

- Pairs: 1
- Baseline pass rate: 1 of 1
- Candidate pass rate after repair: 1 of 1
- Candidate repair invocations: 1
- Candidate agent-run count: 2
- Baseline raw tokens: 66,311
- Candidate cumulative raw tokens: 62,383
- Aggregate raw-token difference: candidate used 5.9% fewer
- Disposition: hold

The test deliberately removed one required citation from the candidate's first
structured answer. Deterministic evaluation detected the omission, one Sol High
repair restored it, and complete revalidation passed. Both executions remained
in the token and time totals.

This is plumbing evidence, not a route-savings result. It has one pair and an
injected fault. Its purpose is to prove that the repair path actually runs,
accounts for itself, and fails closed before a fresh confirmatory trial.

## Private real-workload confirmatory v2: repair contract still too weak

Benchmark: `real-workload-confirmatory-v2-89ac639494b9`

- Pairs: 32 across 4 private projects and 8 task families
- Baseline pass rate: 31 of 32
- Candidate pass rate: 31 of 32
- Baseline raw tokens recorded: 1,956,062
- Candidate raw tokens: 1,377,294
- Aggregate recorded raw-token difference: candidate used 29.6% fewer
- Paired mean raw-token savings: 34.0%
- Paired raw-token-savings interval: 24.0% to 42.9%
- Baseline elapsed time: 1,537.6 seconds
- Candidate elapsed time: 696.4 seconds
- Candidate repairs: 5 attempted, 4 successful
- Candidate critical failures: 1
- Paired quality-delta interval: -9.4 to 9.4 percentage points
- Disposition: rejected

One baseline Sol High execution reached the fixed timeout before emitting a
final usage record. Its zero token entry is missing telemetry, not evidence of a
free call. One Terra-first candidate failed its first answer contract, invoked
the allowed Sol High repair, and still omitted one required evidence path and
one required evidence fact.

The remaining 31 candidate executions passed. Four other repairs also passed
complete revalidation, but a 4 of 5 repair success rate does not satisfy a
zero-critical-failure gate. The missing baseline usage also prevents an exact
token claim. The result remains rejected.

Fix: compile machine-checkable missing paths and facts into an explicit literal
repair checklist, include the bounded current answer as untrusted data, require
the repair model to reopen every missing path, and allow more time for an
otherwise healthy provider execution to emit its final usage record. Any new
confirmation must use fresh run labels, a new source commit, a new bundle hash,
and a preregistration frozen before execution.

## Private real-workload confirmatory v3: targeted model repair is stochastic

Benchmark: `real-workload-confirmatory-v3-241f8ff622e8`

- Pairs: 32 across 4 private projects and 8 task families
- Baseline pass rate: 31 of 32
- Candidate pass rate: 28 of 32
- Baseline raw tokens: 2,073,500
- Candidate cumulative raw tokens: 1,476,688
- Aggregate raw-token difference: candidate used 28.8% fewer
- Paired mean raw-token savings: 26.8%
- Paired raw-token-savings interval: 13.1% to 39.1%
- Baseline elapsed time: 1,005.1 seconds
- Candidate cumulative elapsed time: 768.2 seconds
- Candidate repairs: 7 attempted, 3 successful
- Candidate critical failures: 4
- Paired quality-delta interval: -21.9 to 3.1 percentage points
- Disposition: rejected

The v3 repair packet made every missing literal explicit, embedded the prior
answer as bounded untrusted data, required the model to reopen missing paths,
and revalidated the complete replacement. It passed targeted fault injection
and a 16-pair development run. It did not generalize in confirmation.

All four remaining candidate failures omitted one required evidence path after
the Sol High repair. One affected a bounded Terra-first task, one affected
another bounded Terra-first task, and two affected a safety-retained Sol High
task. The pattern was mechanical citation completion, not a cheaper model
reaching a wrong conclusion.

Fix direction at the time: stop assigning mechanical evidence-path completion
to another reasoning call. A deterministic certificate may add a missing path
only when the verifier reports a path-only failure, the file is safely inside
the workspace, and bounded source lines match terms already present in the
answer or task. Complete revalidation remains mandatory. V3 remains rejected
and is not rescored.

## Private real-workload development v4: clean model fallback is still stochastic

Benchmark: `real-workload-development-v4-111b80838b88`

- Pairs: 24 across 4 private projects and 8 task families
- Baseline pass rate: 23 of 24
- Candidate pass rate: 23 of 24
- Baseline raw tokens: 1,457,911
- Candidate cumulative raw tokens: 940,173
- Aggregate raw-token difference: candidate used 35.5% fewer
- Candidate deterministic completions: 4 attempted, 4 successful
- Candidate clean fallbacks: 1 attempted, 0 successful
- Candidate critical failures: 1
- Disposition: rejected development result

The four verifier-reported path-only gaps were completed locally in about one
millisecond total and all passed full revalidation without another model call.
The remaining candidate failure omitted one evidence path and the task-explicit
literal `INBOX`. A clean Sol High retry omitted the same contract items and
failed again.

Fix direction: permit deterministic completion for a missing path accompanied
only by a missing literal that already appears in the original task or answer
and in the bounded source file. The certificate must avoid copying raw source,
and the complete answer must pass the unchanged evaluator. Remove automatic
model fallback from the next candidate policy so any semantic failure remains a
visible failed outcome.

## Private real-workload confirmatory v5: lexical facts can live on a different cited path

Benchmark: `real-workload-confirmatory-v5-6faed9d59b82`

- Pairs: 40 across 4 private projects and 8 task families
- Baseline pass rate: 37 of 40
- Candidate pass rate: 38 of 40
- Baseline raw tokens: 2,526,823
- Candidate raw tokens: 1,517,243
- Aggregate raw-token difference: candidate used 40.0% fewer
- Paired mean raw-token savings: 38.5%
- Paired raw-token-savings interval: 32.1% to 44.1%
- Baseline elapsed time: 1,370.5 seconds
- Candidate elapsed time: 759.9 seconds
- Candidate deterministic completions: 9 attempted, 8 successful
- Candidate model repairs or retries: 0
- Candidate critical failures: 2
- Paired quality-delta interval: -5.0 to 12.5 percentage points
- Disposition: rejected

All 80 executions reported exact Codex usage and one agent-run invocation. The
candidate passed more tasks overall and used fewer tokens, but the
zero-critical-failure and quality-noninferiority gates still rejected it.

One safety-retained Sol High answer cited all three required files and reached
the correct conclusion but omitted the task-explicit sentence `No messages were
sent`. The first lexical compiler required a missing path, so a fact-only gap
was ineligible. Another candidate reached the correct conclusion but omitted
one required path and the task-explicit word `durable`. The word existed in a
different path already cited by the answer, not in the missing path, so the
compiler correctly refused under its frozen source rule.

Fix direction: allow a task-explicit literal to be verified from any bounded
path already cited by the answer, while still adding each verifier-missing path
from a separate trusted lexical match. A literal-only gap may inspect only
answer-cited paths. Hidden facts, evaluator-only fact paths, semantic failures,
and unsafe paths remain ineligible. V5 remains rejected and is not rescored.
