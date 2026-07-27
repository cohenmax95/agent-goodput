# Contributing

Contributions are welcome when they preserve the core rule: savings count only inside a verified quality envelope.

## Development setup

```bash
python3 -m venv .venv
. .venv/bin/activate
python -m pip install -e ".[dev]"
```

Run the local checks:

```bash
ruff check .
ruff format --check .
mypy src
pytest
python -m build
```

## Change rules

- Keep the default route conservative.
- Do not add raw prompts, outputs, tool payloads, credentials, transcripts, or private paths to telemetry.
- Keep token source labels exact. An estimate must remain labeled as an estimate.
- Add a deterministic test for every policy, evaluator, installer, privacy, or integrity change.
- Do not weaken a benchmark evaluator to make a candidate pass.
- Any task or evaluator change after results were inspected requires a new manifest version.
- Do not add live model calls to normal CI.
- Preserve dry-run defaults for installation, uninstallation, policy changes, and publication helpers.
- Keep third-party source code out of the repository unless its license, attribution, and need have been reviewed.

## Efficiency claims

A pull request may report a development result, but a public savings claim must include the artifacts listed in [the benchmark protocol](docs/BENCHMARK_PROTOCOL.md). Failed experiments stay visible.

## Pull requests

Explain:

- the specific obligation the change improves;
- how it was verified;
- any new context, token, hook, or installation overhead;
- whether the change affects a benchmark contract;
- the rollback path.

