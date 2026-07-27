import assert from "node:assert/strict";
import { access, readFile } from "node:fs/promises";
import test from "node:test";

async function render() {
  const workerUrl = new URL("../dist/server/index.js", import.meta.url);
  workerUrl.searchParams.set("test", `${process.pid}-${Date.now()}`);
  const { default: worker } = await import(workerUrl.href);

  return worker.fetch(
    new Request("http://localhost/", {
      headers: { accept: "text/html" },
    }),
    {
      ASSETS: {
        fetch: async () => new Response("Not found", { status: 404 }),
      },
    },
    {
      waitUntil() {},
      passThroughOnException() {},
    },
  );
}

test("server-renders the evidence-first product page", async () => {
  const response = await render();
  assert.equal(response.status, 200);
  assert.match(response.headers.get("content-type") ?? "", /^text\/html\b/i);

  const html = await response.text();
  assert.match(
    html,
    /<title>Agent Goodput \| Verified token efficiency for Codex<\/title>/i,
  );
  assert.match(html, /Spend less reasoning\./);
  assert.match(html, /Keep the result\./);
  assert.match(html, /39\.6%/);
  assert.match(html, /29\.8%/);
  assert.match(html, /Rejected/);
  assert.match(html, /40 paired tasks/);
  assert.match(html, /35 \/ 35 on both routes/);
  assert.match(html, /Canary eligible/);
  assert.match(html, /not an independently reproducible benchmark/);
  assert.match(html, /Failed work/);
  assert.match(html, /0 goodput/);
  assert.match(html, /Every gate passes, or nothing changes\./);
  assert.match(html, /Live Codex configuration left untouched/);
  assert.match(html, /they cannot replace the model for a task/);
  assert.match(html, /No evaluator means/);
  assert.match(html, /og-card\.png/);
  assert.match(html, /Skip to content/);
  assert.doesNotMatch(html, /Your site is taking shape/);
  assert.doesNotMatch(html, /react-loading-skeleton/);
});

test("keeps proof claims and accessibility safeguards in source", async () => {
  const [page, css, layout, packageJson] = await Promise.all([
    readFile(new URL("../app/page.tsx", import.meta.url), "utf8"),
    readFile(new URL("../app/globals.css", import.meta.url), "utf8"),
    readFile(new URL("../app/layout.tsx", import.meta.url), "utf8"),
    readFile(new URL("../package.json", import.meta.url), "utf8"),
  ]);

  assert.match(page, /feature and method comparison, not a performance claim/);
  assert.match(page, /Current performance evidence compares one/);
  assert.match(page, /not\s+installed into the live\s+Codex environment/);
  assert.match(page, /public and reproducible/);
  assert.match(page, /aria-label="Primary navigation"/);
  assert.match(page, /role="region"/);
  assert.match(css, /prefers-reduced-motion:\s*reduce/);
  assert.match(css, /:focus-visible/);
  assert.match(css, /\.skip-link/);
  assert.doesNotMatch(page, /SkeletonPreview/);
  assert.doesNotMatch(packageJson, /react-loading-skeleton/);
  assert.doesNotMatch(layout, /example\.com(?!\.invalid)/);
  await access(new URL("../public/og-card.png", import.meta.url));
});
