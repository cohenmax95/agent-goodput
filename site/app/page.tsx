import type { Metadata } from "next";

export const metadata: Metadata = {
  title: {
    absolute: "Agent Goodput | Verified token efficiency for Codex",
  },
  description:
    "A quality-gated control layer that saves tokens only when verified work survives.",
};

const proofChecks = [
  "Every task has deterministic obligations",
  "Critical failures erase the quality score",
  "Failed work keeps every token in the denominator",
  "Cheaper routes start in shadow",
  "Fresh evidence is required at every phase",
];

const controlLoop = [
  {
    number: "01",
    label: "Classify",
    title: "Measure the task before choosing a route",
    body: "Risk, scope, sensitivity, complexity, and deterministic work are identified without asking a model.",
  },
  {
    number: "02",
    label: "Compile",
    title: "Load only the context that earns its place",
    body: "Required instructions stay intact. Conditional and optional packets are measured, deduplicated, and budgeted.",
  },
  {
    number: "03",
    label: "Route",
    title: "Try cheaper work only inside a safe envelope",
    body: "Bounded low-risk tasks may enter shadow evaluation. High-stakes work stays on Sol High.",
  },
  {
    number: "04",
    label: "Verify",
    title: "Score obligations, not confidence",
    body: "The evaluator checks citations, conclusions, safety rules, and task-specific facts outside the candidate answer.",
  },
  {
    number: "05",
    label: "Promote",
    title: "Require statistical evidence before live use",
    body: "Quality noninferiority, critical safety, provider telemetry, and token savings must all pass together.",
  },
];

const mechanisms = [
  {
    title: "Context compiler",
    body: "Measures global rules, project instructions, skills, tools, files, and prior context. Required material is never silently cut.",
    signal: "less repeated context",
  },
  {
    title: "Deterministic prework",
    body: "Moves inventories, diffs, log filtering, schema checks, and result parsing outside the reasoning loop.",
    signal: "fewer reasoning steps",
  },
  {
    title: "Selective escalation",
    body: "Sends only failed claims and missing evidence to a stronger route instead of restarting the whole task.",
    signal: "repair, not replay",
  },
  {
    title: "Delegation ROI gate",
    body: "Estimates duplicated context and verification cost before a support agent can be considered.",
    signal: "no reflexive fan-out",
  },
  {
    title: "Conservative learning",
    body: "Learns from verified outcomes, corrections, failures, and cost. New policies begin in shadow and can roll back.",
    signal: "evidence before action",
  },
];

const gateRows = [
  ["Paired outcomes", "30 or more"],
  ["Independent projects", "2 or more"],
  ["Task families", "3 or more"],
  ["Candidate critical failures", "exactly 0"],
  ["Quality lower bound", "within 1 point"],
  ["Savings lower bound", "10% or more"],
  ["Token source", "provider reported"],
];

const surfaces = [
  ["Output compression", "Reduces noisy command results", "Measured as one input"],
  ["Repository indexing", "Finds relevant code quickly", "Measured as one input"],
  ["Model routing", "Changes model or effort", "Quality-gated policy"],
  ["Subagent orchestration", "Splits independent work", "ROI-gated policy"],
  ["Agent Goodput", "Controls the combined route", "Verified outcome per token"],
];

export default function Home() {
  return (
    <>
      <a className="skip-link" href="#main">
        Skip to content
      </a>

      <header className="site-header">
        <a className="wordmark" href="#top" aria-label="Agent Goodput home">
          <span className="wordmark-mark" aria-hidden="true">
            AG
          </span>
          <span>Agent Goodput</span>
        </a>
        <nav aria-label="Primary navigation">
          <a href="#evidence">Evidence</a>
          <a href="#method">Method</a>
          <a href="#gates">Gates</a>
          <a href="#scope">Scope</a>
        </nav>
        <span className="alpha-badge">Local alpha</span>
      </header>

      <main id="main">
        <section className="hero" id="top" aria-labelledby="hero-title">
          <div className="hero-grid" aria-hidden="true" />
          <div className="signal-orbit orbit-one" aria-hidden="true" />
          <div className="signal-orbit orbit-two" aria-hidden="true" />

          <div className="hero-copy">
            <p className="eyebrow">
              <span className="live-dot" aria-hidden="true" />
              Quality-gated token efficiency for Codex
            </p>
            <h1 id="hero-title">
              Spend less reasoning.
              <span>Keep the result.</span>
            </h1>
            <p className="hero-lede">
              Agent Goodput chooses context, prework, model effort, tools, and
              delegation as one policy. Savings count only when the completed
              work passes its obligations.
            </p>
            <div className="hero-actions">
              <a className="button button-primary" href="#evidence">
                Inspect the evidence
                <span aria-hidden="true">↘</span>
              </a>
              <a className="button button-secondary" href="#method">
                See the control loop
              </a>
            </div>
            <dl className="hero-facts">
              <div>
                <dt>Baseline</dt>
                <dd>Sol High</dd>
              </div>
              <div>
                <dt>Cheaper routes</dt>
                <dd>Shadow first</dd>
              </div>
              <div>
                <dt>Failed work</dt>
                <dd>0 goodput</dd>
              </div>
            </dl>
          </div>

          <div className="route-console" aria-label="Example route certificate">
            <div className="console-topbar">
              <div className="console-lights" aria-hidden="true">
                <span />
                <span />
                <span />
              </div>
              <span>route certificate</span>
              <span className="console-status">shadow</span>
            </div>
            <div className="console-body">
              <div className="console-line">
                <span className="line-number">01</span>
                <span className="line-key">task.kind</span>
                <span className="line-value">bounded_read</span>
              </div>
              <div className="console-line">
                <span className="line-number">02</span>
                <span className="line-key">risk</span>
                <span className="line-value safe">low</span>
              </div>
              <div className="console-line">
                <span className="line-number">03</span>
                <span className="line-key">baseline</span>
                <span className="line-value">sol / high</span>
              </div>
              <div className="console-line candidate-line">
                <span className="line-number">04</span>
                <span className="line-key">candidate</span>
                <span className="line-value accent">terra / medium</span>
              </div>
              <div className="console-line">
                <span className="line-number">05</span>
                <span className="line-key">applied</span>
                <span className="line-value">sol / high</span>
              </div>
              <div className="console-divider" />
              <div className="console-check">
                <span className="check-mark" aria-hidden="true">
                  ✓
                </span>
                <div>
                  <span>Candidate observed, not applied</span>
                  <small>Promotion requires fresh paired evidence</small>
                </div>
              </div>
            </div>
            <div className="console-footer">
              <span>policy signed</span>
              <span>raw prompt retained: no</span>
            </div>
          </div>
        </section>

        <section className="proof-strip" aria-label="Core proof rules">
          {proofChecks.map((check) => (
            <div key={check}>
              <span aria-hidden="true">+</span>
              {check}
            </div>
          ))}
        </section>

        <section className="section evidence-section" id="evidence">
          <div className="section-heading">
            <div>
              <p className="section-kicker">Evidence ledger / 2026-07-26</p>
              <h2>The gate passed. The scope stays narrow.</h2>
            </div>
            <p>
              Confirmation v2 preserved every tested obligation and cleared the
              preregistered savings bound. It earns canary eligibility only
              inside this synthetic task envelope.
            </p>
          </div>

          <div className="evidence-grid">
            <article className="result-card featured-result">
              <div className="result-header">
                <div>
                  <span className="result-label">Confirmation v2</span>
                  <h3>35 paired tasks</h3>
                </div>
                <span className="decision passed">Canary eligible</span>
              </div>
              <div className="result-number">
                <strong>29.8%</strong>
                <span>fewer raw tokens overall</span>
              </div>
              <div className="interval">
                <div className="interval-track" aria-hidden="true">
                  <span className="interval-range" />
                  <span className="interval-point" />
                </div>
                <div className="interval-labels">
                  <span>25.5%</span>
                  <span>95% savings interval</span>
                  <span>34.4%</span>
                </div>
              </div>
              <dl className="result-stats">
                <div>
                  <dt>Baseline quality</dt>
                  <dd>35 / 35</dd>
                </div>
                <div>
                  <dt>Candidate quality</dt>
                  <dd>35 / 35</dd>
                </div>
                <div>
                  <dt>Candidate time</dt>
                  <dd>31.0% less</dd>
                </div>
              </dl>
              <p className="pass-note">
                <span aria-hidden="true">✓</span>
                Passed all preregistered gates: 35 complete pairs, zero critical
                failures, equal verified quality, provider-reported usage, and
                a savings lower bound above 10%.
              </p>
            </article>

            <div className="evidence-stack">
              <article className="result-card confirmatory-card">
                <div className="result-header">
                  <div>
                    <span className="result-label">Confirmation v1</span>
                    <h3>34 / 35 on both routes</h3>
                  </div>
                  <span className="decision rejected">Rejected</span>
                </div>
                <p>
                  Each route failed a different hidden lexical obligation. The
                  result was preserved, not rescored, and used to repair the
                  task contract before fresh confirmation.
                </p>
                <div className="run-meter static-meter" aria-hidden="true">
                  <span style={{ width: "100%" }} />
                </div>
                <div className="run-meta">
                  <span>Rejected</span>
                  <span>Not rescored</span>
                  <span>Public-safe evidence</span>
                </div>
              </article>

              <article className="result-card zero-card">
                <p className="section-kicker">The rule that changes the math</p>
                <div className="zero-equation">
                  <span className="failed-task">failed task</span>
                  <span aria-hidden="true">→</span>
                  <strong>0</strong>
                  <span>verified work</span>
                </div>
                <p>
                  Its input and output tokens still count. A cheap wrong answer
                  cannot win the efficiency score.
                </p>
              </article>
            </div>
          </div>
        </section>

        <section className="section method-section" id="method">
          <div className="section-heading narrow-heading">
            <div>
              <p className="section-kicker">The control loop</p>
              <h2>Make the cheap path prove itself.</h2>
            </div>
            <p>
              No single trick is the system. The gain comes from controlling the
              full route and verifying the finished result.
            </p>
          </div>

          <ol className="control-loop">
            {controlLoop.map((step) => (
              <li key={step.number}>
                <div className="step-index">
                  <span>{step.number}</span>
                  <small>{step.label}</small>
                </div>
                <div>
                  <h3>{step.title}</h3>
                  <p>{step.body}</p>
                </div>
              </li>
            ))}
          </ol>
        </section>

        <section className="section mechanisms-section">
          <div className="section-heading">
            <div>
              <p className="section-kicker">Five mechanisms</p>
              <h2>Remove waste without hiding risk.</h2>
            </div>
            <p>
              The controller combines context, deterministic work, escalation,
              delegation, and evidence. Each mechanism has an explicit failure
              mode.
            </p>
          </div>

          <div className="mechanism-grid">
            {mechanisms.map((mechanism, index) => (
              <article key={mechanism.title}>
                <span className="mechanism-number">
                  {String(index + 1).padStart(2, "0")}
                </span>
                <h3>{mechanism.title}</h3>
                <p>{mechanism.body}</p>
                <span className="mechanism-signal">{mechanism.signal}</span>
              </article>
            ))}
          </div>
        </section>

        <section className="section gate-section" id="gates">
          <div className="gate-copy">
            <p className="section-kicker">Promotion contract</p>
            <h2>Every gate passes, or nothing changes.</h2>
            <p>
              A route cannot advance on average quality, a good-looking answer,
              or a single cheap run. Promotion is an all-of-these decision.
            </p>

            <div className="goodput-formula" aria-label="Verified goodput formula">
              <span>verified goodput</span>
              <div>
                <strong>verified work units</strong>
                <span className="fraction-line" />
                <strong>effective tokens</strong>
              </div>
              <span>× 1,000,000</span>
            </div>

            <p className="formula-note">
              Raw-token savings remain the literal consumption claim. Effective
              tokens are a separate, visibly weighted cost view.
            </p>
          </div>

          <div className="gate-panel">
            <div className="gate-panel-header">
              <span>Default promotion gate</span>
              <span className="locked-label">locked before run</span>
            </div>
            <dl>
              {gateRows.map(([label, value]) => (
                <div key={label}>
                  <dt>{label}</dt>
                  <dd>
                    <span aria-hidden="true">✓</span>
                    {value}
                  </dd>
                </div>
              ))}
            </dl>
            <p>
              One critical candidate failure blocks promotion and rolls an
              active policy back to baseline.
            </p>
          </div>
        </section>

        <section className="section scope-section" id="scope">
          <div className="section-heading">
            <div>
              <p className="section-kicker">Competitive scope</p>
              <h2>The missing layer is control.</h2>
            </div>
            <p>
              Existing projects solve valuable pieces of token efficiency.
              Agent Goodput measures those pieces as inputs to one verified
              policy instead of treating any one of them as the outcome.
            </p>
          </div>

          <div className="scope-table" role="region" aria-label="Efficiency surface comparison" tabIndex={0}>
            <table>
              <thead>
                <tr>
                  <th>Surface</th>
                  <th>Useful job</th>
                  <th>Role here</th>
                </tr>
              </thead>
              <tbody>
                {surfaces.map(([surface, job, role]) => (
                  <tr key={surface}>
                    <th scope="row">{surface}</th>
                    <td>{job}</td>
                    <td>{role}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          <p className="scope-note">
            This is a feature and method comparison, not a performance claim
            against those projects. Current performance evidence compares the
            candidate policy with an always-Sol-High baseline on the published
            task suite.
          </p>
        </section>

        <section className="section trust-section">
          <div className="trust-card">
            <div>
              <p className="section-kicker">Built for inspection</p>
              <h2>The evidence survives without the conversation.</h2>
              <p>
                Signed policy snapshots, a hash-chained local ledger, frozen
                benchmark assets, rerunnable evaluators, and public payload
                hashes make each claim inspectable.
              </p>
            </div>
            <ul>
              <li>
                <span aria-hidden="true">01</span>
                No raw prompt or answer in hook telemetry
              </li>
              <li>
                <span aria-hidden="true">02</span>
                Dry-run installation by default
              </li>
              <li>
                <span aria-hidden="true">03</span>
                Hash-owned uninstall and conflict refusal
              </li>
              <li>
                <span aria-hidden="true">04</span>
                Live Codex configuration left untouched
              </li>
            </ul>
          </div>
          <p className="boundary-note">
            Supported boundary: lifecycle hooks can observe work and advance
            signed policy state, but they cannot replace the model for a task
            already running. Actual route enforcement uses the Agent Goodput
            runner or another pre-execution harness adapter. No evaluator means
            no promotion.
          </p>
        </section>

        <section className="final-cta">
          <p className="section-kicker">The standard</p>
          <h2>
            A token is saved only when
            <span>the useful work survives.</span>
          </h2>
          <p>
            Agent Goodput is a local alpha with one passing confirmation inside
            a defined synthetic envelope. It is not installed into the live
            Codex environment and has not been published.
          </p>
          <a className="button button-primary" href="#top">
            Back to the route
            <span aria-hidden="true">↑</span>
          </a>
        </section>
      </main>

      <footer>
        <a className="wordmark footer-wordmark" href="#top">
          <span className="wordmark-mark" aria-hidden="true">
            AG
          </span>
          <span>Agent Goodput</span>
        </a>
        <p>Apache-2.0 local alpha. No public release yet.</p>
        <p>Evidence before savings.</p>
      </footer>
    </>
  );
}
