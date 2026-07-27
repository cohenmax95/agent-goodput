# Publication checklist

Do not publish from an automated task. Publication requires an explicit human decision after this checklist passes.

## Repository

- [x] Repository history contains no competitor clone, private benchmark output, credentials, personal path, or live Codex file.
- [x] License, security policy, contribution guide, architecture, metrics, benchmark protocol, threat model, prior art, competitive audit, limitations, and negative results are present.
- [x] Package name and project name have been checked again for conflicts.
- [x] No nested Git repository or generated build cache is tracked.
- [x] Source distribution and wheel contain only intended files.

## Quality

- [x] Unit tests pass on every supported Python version.
- [x] Ruff check and format check pass.
- [x] Strict mypy passes.
- [x] Wheel and source distribution build.
- [x] Plugin, hook, policy, benchmark, and answer-schema JSON validate.
- [x] Installer dry-run, isolated install, conflict refusal, safe uninstall, and modified-file preservation pass.
- [x] Installer refuses symlinked plugin, marketplace, and managed-file paths.
- [x] Evidence hash-chain tamper and atomicity tests pass.
- [x] Hook privacy tests pass.
- [x] Response-cycle attribution passes unit and live isolated-runtime checks
      without retaining rollout content.
- [x] Site lint, build, and rendered HTML tests pass.

## Benchmark

- [x] Confirmatory manifest was frozen before execution.
- [x] Confirmatory Codex binary, version, and checksum were locked before execution.
- [x] At least 30 paired outcomes span at least 2 projects and 3 task families.
- [x] Baseline and candidate use equivalent task contracts and permissions.
- [x] Every candidate critical obligation passes.
- [x] Candidate pass count is at least baseline pass count.
- [x] Quality noninferiority passes at the configured confidence bound.
- [x] Raw-token-savings lower confidence bound is at least the configured threshold.
- [x] Usage is provider-reported, not estimated or mixed.
- [x] Per-run routes, usage, elapsed time, obligations, hashes, and randomized order are available.
- [x] Public report was produced by the sanitizer.
- [x] Sanitized report contains no raw answer or private path.
- [x] Negative and inconclusive runs remain documented.
- [x] Claims match the tested task envelope and do not generalize beyond it.

## Private-workload publication gate

- [x] Private confirmatory v1 is preserved as a rejected result.
- [x] Private confirmatory v2 is preserved as a rejected result.
- [x] Private confirmatory v3 is preserved as a rejected result.
- [x] Private confirmatory v5 is preserved as a rejected result.
- [x] No proprietary fixture, instruction, source path, raw answer, or project name enters Git.
- [x] The missing selective-repair execution link has unit and live fault-injection coverage.
- [x] A fresh preregistered private-workload confirmation passes after bounded deterministic lexical completion replaces stochastic model repair.
- [x] The sanitized private-workload report passes privacy, secret, and provenance checks.
- [x] Public claims distinguish reproducible synthetic evidence from non-public private-workload evidence.

## Safety

- [x] Live Codex configuration still matches the frozen pre-development hashes.
- [x] No global plugin installation occurred during development.
- [x] Default policy remains Sol High.
- [x] Cheaper routes start in shadow.
- [x] Automatic transition requires fresh evidence at every phase.
- [x] Critical failure and integrity-error rollback paths are tested.
- [x] Hooks are described as fail-open lifecycle helpers, not enforcement.

## Release decision

- [x] Max explicitly delegated the release decision after the quality and safety gates pass.
- [x] Max explicitly authorized repository creation and push.
- [x] Remote visibility, owner, repository name, and license were confirmed.
- [x] First release is tagged and published as a GitHub prerelease.
- [x] Release checksums and GitHub build provenance verify against the tagged commit.
- [x] The permanent evidence site passes production response, security-header,
      desktop/mobile accessibility, and reduced-motion checks.
