# Public benchmark results

Files in this directory are produced from private local reports by
`agp benchmark sanitize`. They contain per-run usage, obligations, routes,
timing, hashes, and aggregate statistics without raw answers, private paths, or
original run identifiers.

## Results

| File | Pairs | Quality | Raw-token difference | Disposition |
| --- | ---: | ---: | ---: | --- |
| [`codex-confirmatory-v1.json`](codex-confirmatory-v1.json) | 35 | 34/35 baseline, 34/35 candidate | Candidate used 30.7% fewer overall | Rejected |
| [`codex-confirmatory-v2.json`](codex-confirmatory-v2.json) | 35 | 35/35 baseline, 35/35 candidate | Candidate used 29.8% fewer overall | Canary eligible |
| [`real-workload-confirmatory-v1.json`](real-workload-confirmatory-v1.json) | 32 | 27/32 baseline, 25/32 candidate | Candidate used 37.1% fewer overall | Rejected |
| [`real-workload-confirmatory-v2.json`](real-workload-confirmatory-v2.json) | 32 | 31/32 baseline, 31/32 candidate | Candidate recorded 29.6% fewer overall | Rejected |
| [`real-workload-confirmatory-v3.json`](real-workload-confirmatory-v3.json) | 32 | 31/32 baseline, 28/32 candidate | Candidate used 28.8% fewer overall | Rejected |

Confirmation v1 is not a passing efficiency claim. The candidate had one
critical lexical-contract failure, and quality noninferiority was not
established. See
[`docs/NEGATIVE_RESULTS.md`](../../docs/NEGATIVE_RESULTS.md) for the diagnosis.

The JSON provenance object contains the private source-report checksum and the
public payload checksum. The private report itself is not published.

Confirmation v2 passed every preregistered gate. Its result is limited to the
published synthetic task envelope and did not change a live policy.

Private-workload confirmation v1 used pseudonymous tasks derived from four
private day-to-day application codebases. Its proprietary fixtures are not
published, so it is not independently reproducible. The run is included because
its seven candidate critical failures blocked publication and exposed the
missing selective-repair execution link. It is not a passing efficiency claim.

Private-workload confirmation v2 exercised the repair path five times, but one
repair failed complete revalidation and one baseline run ended without exact
usage. The result is rejected. Both private-workload reports hash obligation
evidence instead of exposing relative source paths or evaluator literals.

Private-workload confirmation v3 used exact provider telemetry throughout. Its
targeted repair passed only 3 of 7 attempts, leaving four candidate critical
failures. Its token reduction is not a win. All private-workload reports hash
obligation evidence.
