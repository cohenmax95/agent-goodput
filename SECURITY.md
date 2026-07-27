# Security policy

Agent Goodput is alpha software that can influence model routing and collect local usage evidence. Treat policy changes and hooks as sensitive infrastructure.

## Supported versions

Only the latest release is supported during the alpha period.

## Reporting a vulnerability

When this repository is published, use a private GitHub Security Advisory if available. Do not include credentials, private prompts, model outputs, customer data, or private project paths in a public issue.

Include:

- affected version or commit;
- minimal reproduction using synthetic data;
- expected and actual behavior;
- impact on policy integrity, privacy, installation safety, or quality gates.

## Security properties

The project aims to:

- keep raw prompts, outputs, tool inputs, tool outputs, credentials, and transcripts out of telemetry;
- fail closed on policy integrity errors;
- fail open on hook errors because hooks are not a security boundary;
- preserve a proven baseline until paired quality gates pass;
- roll back on critical candidate failure;
- pin installed hooks to the supported Python interpreter used for install;
- refuse symlinked plugin and marketplace destination paths;
- avoid overwriting or deleting files the installer cannot prove it owns.

See [the threat model](docs/THREAT_MODEL.md) for assumptions and exclusions.
