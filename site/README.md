# Agent Goodput site

This is the local evidence site for Agent Goodput. It is intentionally separate
from the Python package and is not deployed.

## Local use

Requires Node.js 22.13 or newer.

```bash
npm install
npm run dev
```

Validation:

```bash
npm run lint
npm test
```

The rendered-page test checks the core evidence language, honest claim boundary,
and accessibility safeguards. Confirmatory numbers must be copied only from a
sanitized public benchmark report.
