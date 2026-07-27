# Confirmation results

## Private real-workload confirmation v6

Benchmark: `real-workload-confirmatory-v6-a12a28016bd1`

Disposition: passed every preregistered gate and is eligible for a canary only
inside the tested task envelope.

| Measure | Always Sol High | Candidate policy | Difference |
| --- | ---: | ---: | ---: |
| Verified tasks | 32 of 40 | 40 of 40 | Candidate passed 8 more |
| Critical failures | 8 | 0 | Candidate had 8 fewer |
| Raw tokens | 2,588,752 | 1,562,524 | 39.6% fewer |
| Input tokens | 2,546,773 | 1,537,065 | 39.6% fewer |
| Uncached input tokens | 586,325 | 444,969 | 24.1% fewer |
| Output tokens | 41,979 | 25,459 | 39.4% fewer |
| Elapsed time | 1,387.4 seconds | 798.0 seconds | 42.5% less |
| Verified goodput | 57.23 | 105.56 | 84.4% higher |
| Codex agent-run invocations | 40 | 40 | Equal |

Paired mean raw-token savings was 38.6%. The 95% paired bootstrap interval was
32.6% to 44.3%, above the frozen 10% lower-bound threshold. The candidate's
paired quality delta was 20 percentage points, with a 95% interval from 7.5 to
32.5 percentage points.

### Tested policy

The baseline used Sol High for all 40 tasks. The candidate policy used:

- Terra Medium for 25 bounded, low-risk read tasks;
- Sol High for 15 safety-sensitive tasks;
- no model repair or retry.

Two candidate answers omitted task-explicit lexical evidence. The bounded local
compiler added two evidence certificates in 2 milliseconds total, without an
additional Codex run. It could use only verifier-reported paths or facts
already present in the task or answer, only bounded files safely inside the
workspace, and only trusted lexical matches. The unchanged evaluator then
revalidated the complete answer. Hidden facts, semantic failures, unsafe paths,
and unsupported conclusions remained ineligible.

### Scope

The 40 pairs span eight task families and four pseudonymous private projects
derived from day-to-day application codebases. Proprietary fixtures,
instructions, source paths, project names, and raw answers are not published.
The result is therefore practical shadow evidence, not an independently
reproducible benchmark.

Every route received the same task contract and equivalent permissions. Every
execution used a fresh workspace and isolated Codex home. Each run recorded
exact Codex usage and exactly one agent-run invocation. This is not a claim
about the number of internal response cycles. The frozen v6 runner predates
Agent Goodput's response-cycle counter.

### Provenance

- Canonical manifest SHA-256:
  `ff1d4767981527696b123e759117b7f1d8be7d145995c2717283dc74faa4a6e5`
- Benchmark bundle SHA-256:
  `98bb2820d293606dfeb0543cf2e72b9c3f16b2aa2e9ef3f2de33aa2a3425f748`
- Benchmark source Git tree:
  `8c161524d7f0b5a05bd85ba96e9d3e5978860b8c`
- Public benchmark source commit:
  [`4c657b98763a53deb448715037747191298be6ad`](https://github.com/cohenmax95/agent-goodput/commit/4c657b98763a53deb448715037747191298be6ad)
- Codex version: `codex-cli 0.146.0-alpha.3.1`
- Codex binary SHA-256:
  `6d8be49e49751554df16572369e636cbe02c84b208cad3dc35528c846eeca223`
- Python: 3.13.13
- Operating system: macOS on arm64
- Started: 2026-07-27 01:51:28 UTC
- Completed: 2026-07-27 02:27:54 UTC
- Private source report SHA-256:
  `1e3687a33f039d46878a98cb2fab8616a5bb01f092c3f7d48adeb29abc1d7374`
- Sanitizer source SHA-256:
  `c9801b60fa02c6d1c03d2fd8f0dd67e9143fca031455aed3ec30d0e2a090c54a`
- Public payload SHA-256:
  `d099e8e065fa110b235e7913e4f9001b3cbe3ffb2757a110f4a43c0da5f97b7a`
- Sanitized report file SHA-256:
  `b4167bcff633e3e670f100157d678d44a5225ccc0e9dbb37292017a5c02818cd`

The sanitized report is
[`benchmarks/results/real-workload-confirmatory-v6.json`](../benchmarks/results/real-workload-confirmatory-v6.json).
It contains per-run routes, exact usage, call counts, timing, obligation
outcomes, randomized order, and provenance hashes. Obligation evidence is
hashed, and private paths and raw answers are absent.

The clean public history begins with the exact source tree used for v6. Its Git
tree object matches the value above even though the private development commit
history is not published.

### Response-cycle telemetry smoke

After v6 was frozen, a bounded read smoke on `codex-cli
0.146.0-alpha.3.1` recorded two completed response cycles inside one Codex
agent-run invocation. The command completed successfully with exact Codex token
usage, and the answer matched the inspected project field. Only the aggregate
cycle count survived; the isolated rollout and temporary Codex home were
deleted. This validates the counter's runtime integration, not a savings or
quality claim.

### Claim boundary

The supported claim is:

> On this preregistered 40-pair shadow derived from four private application
> codebases, the Agent Goodput candidate passed all 40 task contracts, compared
> with 32 for always using Sol High, while using 39.6% fewer raw tokens overall.
> The 95% paired savings interval was 32.6% to 44.3%.

This result does not establish that Terra Medium is generally better than Sol
High. It tests one selective policy: bounded reads may use Terra Medium,
safety-sensitive work stays on Sol High, and task-explicit mechanical evidence
gaps may be completed by a fail-closed local compiler. A new workload bucket
still needs its own shadow evidence and evaluator before canary use. No live
Codex policy was changed.

## Confirmation v2

Benchmark: `codex-confirmatory-v2-35d789ed35b5`

Disposition: passed the preregistered gate and is eligible for a canary inside
the tested task envelope.

| Measure | Always Sol High | Candidate policy | Difference |
| --- | ---: | ---: | ---: |
| Verified tasks | 35 of 35 | 35 of 35 | Equal |
| Critical failures | 0 | 0 | Equal |
| Raw tokens | 1,894,498 | 1,330,599 | 29.8% fewer |
| Input tokens | 1,867,226 | 1,312,551 | 29.7% fewer |
| Uncached input tokens | 425,434 | 336,935 | 20.8% fewer |
| Output tokens | 27,272 | 18,048 | 33.8% fewer |
| Elapsed time | 893.1 seconds | 615.9 seconds | 31.0% less |
| Verified goodput | 95.20 | 129.56 | 36.1% higher |

Paired mean raw-token savings was 30.1%. The 95% paired bootstrap interval was
25.5% to 34.4%, above the preregistered 10% lower-bound threshold. The paired
quality-delta interval was 0.0 to 0.0.

## Tested policy

The baseline used Sol High for all 35 tasks. The candidate policy used:

- Terra Medium plus deterministic prework for 20 bounded read and diagnosis
  tasks;
- Sol Medium plus deterministic prework for 5 bounded local code changes;
- Sol High for 10 security and high-stakes tasks.

This is selective routing, not a blanket cheaper-model comparison.

## Scope

The 35 pairs span seven task families and seven synthetic projects:

- state tracing;
- configuration precedence;
- data-flow tracing;
- incident diagnosis;
- security review;
- high-stakes ambiguity handling;
- a bounded local code change with executable tests.

Each route received the same task contract and equivalent permissions. Every
execution used a fresh workspace and isolated Codex home. User rules, plugins,
hooks, browser tools, and multi-agent behavior were disabled.

## Reproducibility

- Manifest: `benchmarks/manifests/codex-confirmatory-v2.json`
- Canonical manifest SHA-256:
  `5865441ef7328a1758402e2002c589725585b06467d8672a113d18eb94f571f6`
- Benchmark bundle SHA-256:
  `a3e1e511f51e38c42fe6b5ac71857d3b41de6eec437125107a46528bd2987836`
- Local benchmark source commit:
  `38a6c789756a66884c5c7e6cda19e5ac9c5f36d1`
- Codex version: `codex-cli 0.146.0-alpha.3.1`
- Codex binary SHA-256:
  `6d8be49e49751554df16572369e636cbe02c84b208cad3dc35528c846eeca223`
- Python: 3.13.13
- Operating system: macOS on arm64
- Started: 2026-07-26 19:08:21 UTC
- Completed: 2026-07-26 19:33:31 UTC

The runner checked the Codex version and binary checksum before and after the
run. Every outcome recorded the same runtime version and provider-reported token
source.

The sanitized report is
[`benchmarks/results/codex-confirmatory-v2.json`](../benchmarks/results/codex-confirmatory-v2.json).
Its provenance object links the private source-report checksum to the public
payload checksum without publishing raw answers or private paths.

## Claim boundary

The supported claim is:

> On this preregistered 35-pair synthetic Codex suite, the Agent Goodput
> candidate policy preserved all verified obligations while using 29.8% fewer
> raw tokens overall than always using Sol High. The 95% paired savings interval
> was 25.5% to 34.4%.

The result does not prove savings on every real repository, writing task,
browser workflow, or production action. A real task bucket needs its own shadow
evidence and evaluator before canary use. No live policy was changed.

## Private-workload confirmation v1

The first privacy-safe shadow over four private day-to-day application
codebases was rejected:

| Measure | Always Sol High | Candidate policy |
| --- | ---: | ---: |
| Verified tasks | 27 of 32 | 25 of 32 |
| Critical failures | 5 | 7 |
| Raw tokens | 1,944,860 | 1,222,994 |
| Elapsed time | 979.3 seconds | 602.2 seconds |

The candidate used 37.1% fewer raw tokens, but quality noninferiority failed.
Every failed execution reached the required conclusion and omitted at least one
explicit evidence path or verification fact. The framework therefore rejected
the savings.

The sanitized report is
[`benchmarks/results/real-workload-confirmatory-v1.json`](../benchmarks/results/real-workload-confirmatory-v1.json).
The private fixtures and instructions are not published, so this result is
practical shadow evidence rather than an independently reproducible benchmark.
See [negative results](NEGATIVE_RESULTS.md) for the failure diagnosis and
selective-repair fix.

## Private-workload confirmation v2

The first confirmatory test of the wired repair path was also rejected:

| Measure | Always Sol High | Candidate policy |
| --- | ---: | ---: |
| Verified tasks | 31 of 32 | 31 of 32 |
| Critical failures | 1 | 1 |
| Raw tokens recorded | 1,956,062 | 1,377,294 |
| Elapsed time | 1,537.6 seconds | 696.4 seconds |
| Repair attempts | 0 | 5 |
| Successful repairs | 0 | 4 |

The candidate's recorded raw-token total was 29.6% lower, but one Sol High
repair still missed two literal evidence requirements. One baseline execution
also timed out before exact usage was reported. Quality noninferiority and exact
usage therefore failed their preregistered gates.

The sanitized report is
[`benchmarks/results/real-workload-confirmatory-v2.json`](../benchmarks/results/real-workload-confirmatory-v2.json).
It preserves the failed result without publishing raw answers, private paths,
project names, fixtures, or instructions.

## Private-workload confirmation v3

The stricter verifier-derived repair prompt did not generalize:

| Measure | Always Sol High | Candidate policy |
| --- | ---: | ---: |
| Verified tasks | 31 of 32 | 28 of 32 |
| Critical failures | 1 | 4 |
| Raw tokens | 2,073,500 | 1,476,688 |
| Elapsed time | 1,005.1 seconds | 768.2 seconds |
| Repair attempts | 0 | 7 |
| Successful repairs | 0 | 3 |

The candidate used 28.8% fewer raw tokens, and the paired savings interval was
13.1% to 39.1%. Quality still regressed. Four Sol High repairs omitted a
required evidence path after the initial answer failed, so the quality and
critical-failure gates rejected the result.

The sanitized report is
[`benchmarks/results/real-workload-confirmatory-v3.json`](../benchmarks/results/real-workload-confirmatory-v3.json).
It uses exact provider telemetry and redacts obligation evidence. The result is
negative evidence against relying on targeted model prompting for mechanical
contract repair.
