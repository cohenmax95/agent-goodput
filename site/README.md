# Agent Goodput site

This is the evidence site for Agent Goodput. It is intentionally separate from
the Python package so the proof surface can be built and tested independently.

Production: <https://agent-goodput.netlify.app>

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

The tracked Netlify fallback builds the same page as a static export:

```bash
npm run build:static
```

The rendered-page test checks the core evidence language, honest claim boundary,
and accessibility safeguards. Confirmatory numbers must be copied only from a
sanitized public benchmark report.
