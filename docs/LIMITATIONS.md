# Limitations

Agent Goodput is alpha software. Its safety properties come from conservative defaults and deterministic gates, not from a claim that routing is solved.

- The bundled classifier is rule-based. It can miss nuance and intentionally sends uncertain or high-risk work to the baseline.
- Hooks are not an enforcement boundary. They can be disabled, time out, or fail open.
- Codex lifecycle hooks cannot replace the selected model for a task already in progress. The plugin maintains route certificates and policy state; actual model enforcement requires `agp run` or another pre-execution harness adapter.
- The controller cannot verify arbitrary real-world work by itself. Automatic promotion requires outcomes from a deterministic evaluator, benchmark adapter, or another reviewable oracle. Buckets without one remain in shadow.
- Automatic promotion is only as good as the evaluator suite. A weak oracle can verify the wrong property.
- The public reproducible benchmark uses synthetic repositories with deterministic answers. A private real-workload shadow can add practical evidence, but proprietary fixtures cannot be independently inspected and must not be presented as public reproducibility.
- Repeated benchmark labels represent fresh stochastic executions. They are not fixed provider seeds.
- Current Codex JSON output reports exact cumulative token totals but not an
  internal model-call count. For isolated runs, Agent Goodput can count
  completed sampling-response cycles from temporary rollout events. This
  version-dependent episode signal is not a provider billing item, and v6
  predates it.
- Raw tokens do not equal cost. Cache behavior, model pricing, and output pricing change the bill.
- Effective-token weights are explicit assumptions and should not be presented as literal token savings.
- The local signature and hash chain detect common corruption and tampering. They do not protect against an attacker who can replace the state directory and key together.
- Privacy checks reject known raw-content fields, but arbitrary custom metadata can still contain sensitive values under misleading keys.
- Deterministic prework can save reasoning but can also omit relevant evidence if configured badly. Required context therefore fails closed when it does not fit.
- Deterministic evidence completion handles only missing paths and missing
  literals already stated in the original task or answer. It requires a bounded
  in-workspace file and a lexical source match. Literal-only completion can
  inspect only paths already cited by the answer. It does not prove semantic
  correctness and never repairs a hidden fact, wrong conclusion, unsafe action,
  forbidden fact, or execution failure.
- Selective escalation assumes failed obligations can be repaired independently.
  The benchmark adapter permits only one model retry and revalidates the
  complete replacement answer. If dependencies invalidate earlier work or the
  evaluator type is not allowlisted, the caller must request a full rerun.
- Automatic selective repair currently requires a benchmark or harness adapter with deterministic obligations. The generic `agp run` command cannot invent a correctness oracle.
- The installer targets the current personal Codex plugin layout. Codex lifecycle schemas can change.
- Non-managed hooks require explicit review and trust through Codex. Agent
  Goodput does not and should not bypass that one-time control.
- No route is installed or promoted merely because a repository benchmark succeeds. Real workloads require their own shadow evidence.
