# Competitive audit

This audit records the public projects that most influenced Agent Goodput. It is a clean-room feature study, not a claim that Agent Goodput is universally better or faster.

Snapshot date: 2026-07-27 UTC. Repositories change quickly, so commit links are the durable references.

## What successful projects already do well

| Project | Public strength worth preserving | Gap Agent Goodput targets |
| --- | --- | --- |
| [RTK](https://github.com/rtk-ai/rtk/tree/1d6798de8aee0940b490719153e7554845f8f43c) | Fast, command-aware output reduction with raw passthrough when compression is not useful | Measures one context surface. It does not decide whether a cheaper model, less reasoning, or delegation preserved the task outcome |
| [Headroom](https://github.com/headroomlabs-ai/headroom/tree/904bc675b35072dc61191963cbe485fa692927d1) | Reversible, content-aware compression, cache alignment, proxy integration, and detailed telemetry | Compression and request routing are strong, but a cross-layer shadow-to-canary controller tied to task-specific deterministic outcomes was not found in the inspected commit |
| [Repowise](https://github.com/repowise-dev/repowise/tree/82cd55b0fc6a4fd823c034f14045a660c8113f71) | Precomputed repository intelligence that can replace broad file search and repeated reads | Repository context is one part of total agent consumption. Model effort, selective escalation, delegation return, and autonomous rollback remain separate problems |
| [CodexZero](https://github.com/Retro2512/CodexZero/tree/4304774a944a842703b00ada2c533c9872ddd6bb) | Strong reproducibility discipline: repeated paired runs, fresh homes, randomized order, pinned settings, confidence intervals, and evidence hashes | Focuses on reducing Codex input inside the harness. It is not a general model, effort, context, tool, and delegation policy controller |
| [Crucible](https://github.com/Siddhant-Goswami/Crucible/tree/156a4b899a61d987360458ba7e8287fa1e19a61f) | Deterministic hidden oracles, safety-gated goodput, and factorial harness-by-model evaluation | A research harness is not itself a low-overhead lifecycle controller that can promote and roll back bucket-specific policies |
| [Agent-as-a-Router](https://github.com/LanceZPF/agent-as-a-router/tree/e43839edb0d5d0a9feec2f7078019406ab4d64bd) | Serious learned routing research with a public benchmark and performance-cost framing | Learned routing can choose models, but production use still needs local obligation verification, privacy-safe telemetry, staged promotion, and rollback |
| [agentic-ops](https://github.com/githubnext/agentic-ops/tree/1115d071436896bba2115678d453c0fa545d7345) | Operational token audits and conservative optimization recommendations for GitHub agentic workflows | Recommendation workflows do not automatically prove quality noninferiority before applying a route to local Codex work |
| [ECC](https://github.com/affaan-m/ECC/tree/6a9f075cd97c139a5f7e84e1e3f2c9ab095adf64) | Broad, portable skills, agents, hooks, quality gates, memory, and workflow coverage | Breadth can increase loaded policy and delegation overhead. Agent Goodput keeps the runtime surface narrow and requires causal paired evidence for promotion |
| [Token Optimizer](https://github.com/alexgreensh/token-optimizer/tree/bc0e2bdfb8ac5a72ce455121197ad8d33242130a) | Polished automatic audits, context hygiene, hooks, checkpoints, and a live dashboard | The inspected public project is PolyForm Noncommercial. Its public history also shows why timeout bounds, interpreter portability, retention contracts, concurrency safety, and accounting semantics need hard gates |
| [subagents_configs](https://github.com/nsEytgXm/subagents_configs/tree/36bbd6a805b2122217b59db99f8868d69c766b48) | Portable role definitions, managed installation, ownership hashes, and orchestrator responsibility | Delegation is often more expensive than one-agent work. Agent Goodput makes delegation pass a return-on-investment and independence gate before spawning |

## Evidence-only reference

[JFrog Boost](https://github.com/jfrog/boost/tree/2ab14fd0feca752bb5e9e899ee4d687ebb222f17) publishes a useful claim shape: lower cost at the same task-benchmark pass rate. Its repository is All Rights Reserved and governed by a preview agreement. Agent Goodput did not copy or adapt its implementation. Only public claims and documentation informed the benchmark questions.

## Combined gap

The public projects above solve valuable parts of the problem:

- compress a command or context packet;
- precompute repository knowledge;
- route a request;
- measure a harness;
- package skills and subagents;
- report usage.

The missing combination is a conservative closed loop:

1. measure all major context and route surfaces;
2. move deterministic work out of the reasoning loop;
3. try cheaper routes only where risk rules allow;
4. verify task-specific obligations;
5. count failed attempts against consumption;
6. promote only from paired confidence bounds;
7. require fresh evidence at each phase;
8. roll back automatically on critical failure or integrity error;
9. retain counters and hashes, not private work content;
10. install without overwriting user-managed files.

Agent Goodput is built around that combination.

## Runtime episode evidence

[OpenAI Codex issue #35050](https://github.com/openai/codex/issues/35050)
contains controlled community tests in which bounded batching of independent
read-only tool calls reduced repeated context processing. The issue is open,
the results vary by workload, and at least one replication reported a quality
recovery advantage for the sequential control after broad output was
truncated. Agent Goodput therefore does not install a blanket batching rule.
It treats outer-cycle reduction, bounded deterministic batching, and
truncation recovery as candidate mechanisms that still need paired obligations
and full accounting.

The public v6 report records one Codex agent-run invocation per route. It
predates Agent Goodput's response-cycle counter and is not an internal
model-cycle claim. Current isolated runs can count completed sampling-response
cycles from temporary Codex rollout events while retaining only the integer.
Agent-run invocations, response cycles, tool events, and tokens remain separate
fields.

## What this audit does not prove

- It is not a complete security audit of any listed project.
- “Not found” means not found in the inspected public commit and relevant documentation, not proof that a capability cannot exist.
- Star counts measure attention, not correctness.
- Feature coverage does not establish better runtime performance.
- Agent Goodput needs its own reproducible benchmark and real-work shadow evidence before any broad claim.
