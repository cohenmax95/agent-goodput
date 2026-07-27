# Claim rules

- "Token savings" means the paired change in raw input plus output tokens.
- Cached input, uncached input, output, reasoning, calls, latency, and monetary cost stay visible as separate fields.
- "Cost-equivalent tokens" is a weighted view, not literal token consumption.
- "Verified goodput" is verified obligation weight per effective million tokens. Failed tasks contribute zero useful work and keep their full token cost.
- A public result needs a pinned manifest, task fixtures, model and effort, randomized paired order, at least three seeds where nondeterminism exists, deterministic evaluators, artifact hashes, and confidence intervals.
- Simulations, estimates, shadow observations, and single-user traces must be labeled and cannot support a general savings claim.
- Report negative, null, and rejected experiments.
