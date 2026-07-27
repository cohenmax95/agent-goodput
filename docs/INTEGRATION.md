# Integration

Agent Goodput has two independent surfaces: a CLI for explicit evaluation and a Codex plugin for lifecycle observation.

## Safe evaluation first

Create an isolated local environment:

```bash
python3 -m venv .venv
. .venv/bin/activate
python -m pip install -e .
```

Inspect the default state without installing a plugin:

```bash
agp doctor
agp policy show
agp classify "Read this small repository and explain one function."
agp route "Read this small repository and explain one function."
```

Every command accepts `--state-dir` before the subcommand when you want an isolated state directory:

```bash
agp --state-dir /tmp/agp-state policy show
```

## Context and deterministic work

```bash
agp context audit AGENTS.md pyproject.toml
agp preflight --cwd . inventory diff-summary
```

Context audit reports whether counting is exact or estimated. Estimated usage can inform development but cannot promote a route.

## Run Codex through the controller

```bash
agp run --cwd . "Trace the configuration precedence."
```

The baseline remains Sol High unless an eligible bucket has advanced through the evidence controller. Use `--include-user-context` only when personal rules and plugins are intentionally part of the experiment.

## Paired benchmark

```bash
agp benchmark run benchmarks/manifests/codex-smoke-v1.json
```

The smoke suite is for plumbing checks. It is not enough evidence for promotion.

## Plugin install

Preview every file and marketplace change:

```bash
agp install
```

Apply only after reviewing the plan:

```bash
agp install --apply
```

The installer records ownership hashes. It refuses to overwrite unmanaged or modified files.

Uninstall is also dry-run first:

```bash
agp uninstall
agp uninstall --apply
```

If any installed file changed, uninstall stops and preserves it.

## Autonomous controller

The `SessionEnd` hook runs one bounded policy cycle. Candidates begin in shadow.
A transition occurs only when the configured paired evidence gate passes.

This automates policy state, not model interception. Codex hooks do not provide
a supported way to replace the model for a task that is already running. Use
`agp run` or a harness adapter that chooses the route before execution when the
policy must affect the actual model and effort.

The controller also does not invent proof for arbitrary work. Verified outcomes
must come from a deterministic evaluator, a benchmark adapter, or another
reviewable oracle. Without that evidence, the candidate stays in shadow.

Harness adapters may enable deterministic lexical evidence completion. This is
not a general answer fixer. It can act only after a verifier identifies missing
paths or missing literals already stated in the original task or answer. Search
scope is limited to verifier-missing paths and paths already cited by the
answer. A bounded file inside the workspace must contain each claimed match.
Every modified answer must be evaluated again.

Manual inspection remains available:

```bash
agp policy evaluate "research:low:none:simple"
agp policy cycle
```

`policy cycle` is dry-run unless `--apply` is present. The plugin session-end
cycle is the intended hands-off policy-state surface after installation.

## Real-project rollout

Do not treat the bundled synthetic benchmark as proof for a private production repository. For each real task bucket:

1. keep the existing route as baseline;
2. register a candidate in shadow;
3. create deterministic or reviewable obligations;
4. collect paired, privacy-safe outcomes;
5. inspect rejected and passed cases;
6. allow the controller to canary only after every gate passes;
7. retain an emergency rollback path.
