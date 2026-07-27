import type { Metadata } from "next";

export const metadata: Metadata = {
  title: {
    absolute: "Agent Goodput | Quality-gated token routing for Codex",
  },
  description:
    "Measures the full Codex route and permits cheaper policies only after task-specific quality checks pass.",
};

const proofChecks = [
  "Each benchmark task defines deterministic obligations",
  "A critical failure sets verified work to zero",
  "Tokens from failed attempts still count",
  "Candidate routes begin in shadow mode",
  "Each promotion phase requires fresh evidence",
];

const controlLoop = [
  {
    number: "01",
    label: "Classify",
    title: "Classify task risk without a model",
    body: "Local rules identify scope, sensitivity, complexity, and deterministic work before a route is considered.",
  },
  {
    number: "02",
    label: "Compile",
    title: "Measure required, conditional, and optional context",
    body: "Required instructions stay intact. Other packets are measured, deduplicated, and loaded only when the task needs them.",
  },
  {
    number: "03",
    label: "Route",
    title: "Keep high-risk work on Sol High",
    body: "Only bounded, low-risk work can enter shadow evaluation on a cheaper candidate route.",
  },
  {
    number: "04",
    label: "Verify",
    title: "Check task-specific obligations",
    body: "A separate evaluator checks citations, conclusions, safety rules, and required facts outside the candidate answer.",
  },
  {
    number: "05",
    label: "Promote",
    title: "Change policy only after the frozen gates pass",
    body: "Quality noninferiority, zero critical failures, provider telemetry, and token savings must pass together.",
  },
];

const mechanisms = [
  {
    title: "Context compiler",
    body: "Measures global rules, project instructions, skills, tools, files, and prior context. It does not remove required material.",
    signal: "less repeated context",
  },
  {
    title: "Deterministic prework",
    body: "Moves inventories, diffs, log filtering, schema checks, and result parsing outside the reasoning loop.",
    signal: "fewer reasoning steps",
  },
  {
    title: "Deterministic evidence compiler",
    body: "Completes only verifier-reported, task-explicit lexical evidence gaps from bounded trusted files, then revalidates the full answer.",
    signal: "mechanical work, no second run",
  },
  {
    title: "Delegation ROI gate",
    body: "Estimates duplicated context and verification cost before a support agent can be considered.",
    signal: "no reflexive fan-out",
  },
  {
    title: "Conservative learning",
    body: "Updates policy from verified outcomes, corrections, failures, and cost. New policies begin in shadow and can roll back.",
    signal: "verified changes only",
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
          <a href="https://github.com/cohenmax95/agent-goodput">GitHub</a>
        </nav>
        <span className="alpha-badge">Public alpha</span>
      </header>

      <main id="main" tabIndex={-1}>
        <section className="hero" id="top" aria-labelledby="hero-title">
          <div className="hero-grid" aria-hidden="true" />
          <div className="signal-orbit orbit-one" aria-hidden="true" />
          <div className="signal-orbit orbit-two" aria-hidden="true" />

          <div className="hero-copy">
            <p className="eyebrow">
              <span className="live-dot" aria-hidden="true" />
              Measured token routing for Codex
            </p>
            <h1 id="hero-title">
              Test cheaper routes against
              <span>the same quality requirements.</span>
            </h1>
            <p className="hero-lede">
              Agent Goodput measures context, deterministic work, model effort,
              tools, and delegation as one route. A cheaper policy can advance
              only after the finished work passes task-specific checks.
            </p>
            <div className="hero-actions">
              <a className="button button-primary" href="#evidence">
                Read the results
                <span aria-hidden="true">↘</span>
              </a>
              <a className="button button-secondary" href="#method">
                How it works
              </a>
              <a
                className="button button-secondary"
                href="https://github.com/cohenmax95/agent-goodput"
              >
                Source code
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
              <h2>Two tests passed under different evidence limits.</h2>
            </div>
            <p>
              A private-workload shadow tests practical behavior. A public
              synthetic suite lets anyone inspect and rerun the method. Neither
              supports a universal savings claim.
            </p>
          </div>

          <div className="evidence-grid">
            <article className="result-card featured-result">
              <div className="result-header">
                <div>
                  <span className="result-label">
                    Private-workload confirmation v6
                  </span>
                  <h3>40 paired tasks</h3>
                </div>
                <span className="decision passed">Canary eligible</span>
              </div>
              <div className="result-number">
                <strong>39.6%</strong>
                <span>fewer raw tokens overall</span>
              </div>
              <div className="interval">
                <div className="interval-track" aria-hidden="true">
                  <span className="interval-range" />
                  <span className="interval-point" />
                </div>
                <div className="interval-labels">
                  <span>32.6%</span>
                  <span>95% savings interval</span>
                  <span>44.3%</span>
                </div>
              </div>
              <dl className="result-stats">
                <div>
                  <dt>Baseline quality</dt>
                  <dd>32 / 40</dd>
                </div>
                <div>
                  <dt>Candidate quality</dt>
                  <dd>40 / 40</dd>
                </div>
                <div>
                  <dt>Candidate time</dt>
                  <dd>42.5% less</dd>
                </div>
              </dl>
              <p className="pass-note">
                <span aria-hidden="true">✓</span>
                Passed all frozen gates: 40 complete pairs, zero candidate
                critical failures, provider-reported usage, and a 32.6% savings
                lower bound.
              </p>
              <p className="scope-note">
                The four source projects are pseudonymous and the proprietary
                fixtures are not published. This is practical shadow evidence,
                not an independently reproducible benchmark.
              </p>
            </article>

            <div className="evidence-stack">
              <article className="result-card confirmatory-card">
                <div className="result-header">
                  <div>
                    <span className="result-label">
                      Public synthetic confirmation v2
                    </span>
                    <h3>35 / 35 on both routes</h3>
                  </div>
                  <span className="decision passed">Reproducible</span>
                </div>
                <p>
                  The candidate used 29.8% fewer raw tokens overall. The 95%
                  paired savings interval was 25.5% to 34.4%. Tasks, fixtures,
                  evaluators, manifest, and sanitized results are public.
                </p>
                <div className="run-meter static-meter" aria-hidden="true">
                  <span style={{ width: "100%" }} />
                </div>
                <div className="run-meta">
                  <span>35 pairs</span>
                  <span>7 projects</span>
                  <span>7 task families</span>
                </div>
              </article>

              <article className="result-card confirmatory-card">
                <div className="result-header">
                  <div>
                    <span className="result-label">
                      Private-workload confirmation v5
                    </span>
                    <h3>38 / 40 candidate tasks passed</h3>
                  </div>
                  <span className="decision rejected">Rejected</span>
                </div>
                <p>
                  The candidate used 40.0% fewer raw tokens, but two critical
                  failures blocked it. The run was preserved and the v6 test
                  used a fresh, frozen contract.
                </p>
              </article>

              <article className="result-card zero-card">
                <p className="section-kicker">Failed tasks score zero</p>
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
              <p className="section-kicker">Policy lifecycle</p>
              <h2>A cheaper route must pass the same checks.</h2>
            </div>
            <p>
              The controller measures the full route, then checks the finished
              work against the task contract.
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
              <p className="section-kicker">Five controls</p>
              <h2>Five controls reduce measured waste.</h2>
            </div>
            <p>
              The controller combines context, deterministic work, lexical
              completion, delegation, and verified outcome data. Each control
              has a defined failure condition.
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
            <h2>A route changes only after every gate passes.</h2>
            <p>
              Average quality, one plausible answer, or a single cheap run
              cannot advance a route.
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
              <p className="section-kicker">What other tools cover</p>
              <h2>Agent Goodput evaluates the combined route.</h2>
            </div>
            <p>
              Other projects reduce output, index repositories, route models,
              or coordinate subagents. Agent Goodput treats those choices as
              inputs and measures the verified result of the complete route.
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
            against those projects. Current performance evidence compares one
            candidate policy with an always-Sol-High baseline. The 35-pair
            synthetic suite is public and reproducible. The 40-pair private
            shadow exposes sanitized per-run evidence, but its proprietary
            fixtures are not independently inspectable.
          </p>
        </section>

        <section className="section trust-section">
          <div className="trust-card">
            <div>
              <p className="section-kicker">What the release records</p>
              <h2>Claims stay tied to their evidence.</h2>
              <p>
                Signed policy snapshots, a hash-chained local ledger, frozen
                benchmark assets, rerunnable evaluators, and public payload
                hashes preserve the basis for each claim.
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
                Live installation is hash-owned and reversible
              </li>
              <li>
                <span aria-hidden="true">05</span>
                Hook review and trust stay explicit
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
          <p className="section-kicker">Current release</p>
          <h2>
            The release includes
            <span>its evidence and limits.</span>
          </h2>
          <p>
            This public alpha includes one reproducible synthetic confirmation,
            one passing private-workload shadow, and a tested live plugin
            installation. These results do not support a universal savings claim.
          </p>
          <a
            className="button button-primary"
            href="https://github.com/cohenmax95/agent-goodput"
          >
            Open the repository
            <span aria-hidden="true">↗</span>
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
        <p>
          <a href="https://github.com/cohenmax95/agent-goodput">
            Apache-2.0 public alpha
          </a>
        </p>
        <p>Public benchmark data and rejected runs are in the repository.</p>
      </footer>
    </>
  );
}
