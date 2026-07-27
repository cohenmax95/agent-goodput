# Threat model

Agent Goodput is designed to prevent accidental quality loss, misleading efficiency claims, unsafe autonomous promotion, and unnecessary retention of private work data.

## Protected assets

- the proven baseline route;
- policy state and phase history;
- benchmark integrity;
- token and quality evidence;
- private prompts, outputs, tool data, credentials, project paths, and transcripts;
- user-managed plugin and marketplace files.

## Main failure modes

### Cheap but wrong wins

A route can use fewer tokens by doing less work or returning an incorrect answer.

Controls:

- deterministic task obligations;
- critical failures reduce verified work to zero;
- failed runs remain in the token denominator;
- pass-count and quality-noninferiority gates;
- rollback from canary or active after a critical failure.
- deterministic lexical completion constrained to bounded in-workspace files
  and literals already present in the original task or answer, with source
  scope limited to verifier-missing and answer-cited paths;
- one-shot stronger-route repair only for manifest-allowlisted evaluator types;
- full revalidation and cumulative accounting after repair.

### Benchmark overfitting

An evaluator can be adjusted after results are seen, or a narrow suite can be presented as universal.

Controls:

- hashed manifests;
- randomized pair order;
- fresh workspaces;
- preregistration for confirmatory runs;
- version changes after any evaluator or task change;
- publication of negative results and limitations.

### Stale evidence reuse

Old successful results can incorrectly advance a new route or a new phase.

Controls:

- evidence cursors on each bucket phase;
- fresh evidence required after registration and each transition;
- policy parent digests and signed snapshots.

### Evidence corruption or partial writes

A crash can leave a policy event without its outcome, or later edits can alter history.

Controls:

- event and outcome insertion in one SQLite transaction;
- full synchronous writes and write-ahead logging;
- a hash chain over event payloads;
- integrity verification before controller decisions.

The hash chain detects edits. It does not make the database immutable against an attacker who can replace the database and signing key together.

### Private data retention

Telemetry can accidentally become a second copy of prompts, outputs, credentials, or project paths.

Controls:

- forbidden raw-content keys at the ledger boundary;
- keyed project identifiers;
- digested session, turn, task, and output identifiers;
- allowlisted session-end reason codes;
- aggregate counters instead of raw tool responses;
- raw benchmark outputs off by default.
- task instructions, repair packets, and completion workspaces kept in
  temporary execution paths and removed during normal cleanup.
- response-cycle attribution reads rollout events only from the isolated
  temporary Codex home and retains only an aggregate count.

If the host process is killed before cleanup, operating-system temporary files
can survive until the host removes them. Private benchmarks should still run on
a trusted local machine with encrypted storage.

This is defense in depth, not a data-loss-prevention system. Custom metadata should still be reviewed before ingestion.

### Unsafe installation or uninstall

An installer can overwrite user changes or remove files it does not own.

Controls:

- dry-run by default;
- per-file ownership hashes;
- installed hooks pinned to the supported Python interpreter used for install;
- refusal to follow symlinked plugin, marketplace, or managed-file paths;
- refusal to overwrite unmanaged or modified files;
- refusal to uninstall without a valid ownership ledger;
- preservation of conflicting marketplace entries.

### Untrusted benchmark manifests

A benchmark manifest defines commands and evaluator commands. Running one is
equivalent to running local code.

Controls:

- bundled manifests are committed and hashed;
- confirmatory manifests and assets are frozen before execution;
- commands use argument arrays and never a shell;
- benchmark workspaces are disposable and Codex permissions are explicit.

Do not run a manifest from an untrusted repository. Agent Goodput does not
sandbox arbitrary host commands declared by a third party.

### Hook bypass or failure

Hooks can time out, be disabled, or fail.

Controls:

- hooks are treated as observation and workflow surfaces, not a security boundary;
- every hook has an explicit short host timeout;
- controller and benchmark gates remain independently callable;
- hook failures do not block the agent;
- the baseline policy remains safe when telemetry is missing.

### Adversarial task text

A prompt can try to misclassify itself or request unsafe routing.

Controls:

- candidates have maximum allowed risk;
- sensitive, external, high-stakes, architecture, and broad mutation signals force the baseline;
- an explicit quality request can only move toward the baseline, never away from it;
- active policy is bucket-specific and signed.

## Out of scope

- protecting a compromised operating system;
- proving that provider token telemetry is correct;
- evaluating subjective answer quality without a task-specific oracle;
- safely executing arbitrary third-party hooks;
- automatically modifying production systems or sending communications.
