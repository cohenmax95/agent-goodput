from __future__ import annotations

import math
import random
from dataclasses import dataclass
from statistics import fmean

from .models import PromotionReport, RunOutcome


@dataclass(frozen=True)
class PromotionThresholds:
    min_pairs: int = 30
    min_projects: int = 2
    min_task_families: int = 3
    noninferiority_margin: float = 0.01
    minimum_raw_token_savings: float = 0.10
    bootstrap_iterations: int = 5_000
    confidence: float = 0.95

    def __post_init__(self) -> None:
        if self.min_pairs < 1 or self.min_projects < 1 or self.min_task_families < 1:
            raise ValueError("minimum evidence counts must be positive")
        if not 0 < self.confidence < 1:
            raise ValueError("confidence must be between zero and one")
        if self.bootstrap_iterations < 100:
            raise ValueError("bootstrap_iterations must be at least 100")


def wilson_interval(
    successes: int, total: int, z: float = 1.959963984540054
) -> tuple[float, float]:
    if total <= 0:
        return (0.0, 1.0)
    proportion = successes / total
    denominator = 1 + z * z / total
    center = (proportion + z * z / (2 * total)) / denominator
    radius = (
        z
        * math.sqrt(proportion * (1 - proportion) / total + z * z / (4 * total * total))
        / denominator
    )
    return max(0.0, center - radius), min(1.0, center + radius)


def paired_bootstrap_interval(
    values: list[float],
    *,
    iterations: int = 5_000,
    confidence: float = 0.95,
    seed: int = 0,
) -> tuple[float, float]:
    if not values:
        return (0.0, 0.0)
    if len(values) == 1:
        return (values[0], values[0])
    # The seed makes the statistical interval reproducible, not unpredictable.
    generator = random.Random(seed)  # nosec B311
    count = len(values)
    estimates = sorted(
        fmean(values[generator.randrange(count)] for _ in range(count)) for _ in range(iterations)
    )
    tail = (1 - confidence) / 2
    low_index = max(0, min(iterations - 1, math.floor(tail * iterations)))
    high_index = max(
        0,
        min(iterations - 1, math.ceil((1 - tail) * iterations) - 1),
    )
    return estimates[low_index], estimates[high_index]


def exact_two_sided_sign_test(positive: int, negative: int) -> float:
    trials = positive + negative
    if trials == 0:
        return 1.0
    smaller = min(positive, negative)
    tail = sum(math.comb(trials, k) for k in range(smaller + 1)) / 2**trials
    return float(min(1.0, 2 * tail))


def pair_outcomes(
    outcomes: list[RunOutcome] | tuple[RunOutcome, ...],
) -> list[tuple[RunOutcome, RunOutcome]]:
    groups: dict[tuple[str, str, int | None], dict[str, RunOutcome]] = {}
    for item in outcomes:
        key = (item.task_id, item.project_id, item.seed)
        variants = groups.setdefault(key, {})
        if item.variant in variants:
            raise ValueError(f"duplicate {item.variant} result for paired task {key}")
        variants[item.variant] = item
    pairs: list[tuple[RunOutcome, RunOutcome]] = []
    for variants in groups.values():
        if "baseline" in variants and "candidate" in variants:
            pairs.append((variants["baseline"], variants["candidate"]))
    return pairs


def evaluate_promotion(
    outcomes: list[RunOutcome] | tuple[RunOutcome, ...],
    *,
    thresholds: PromotionThresholds | None = None,
    current_phase: str = "shadow",
) -> PromotionReport:
    selected = thresholds or PromotionThresholds()
    pairs = pair_outcomes(outcomes)
    quality_deltas = [
        candidate.quality_score - baseline.quality_score for baseline, candidate in pairs
    ]
    savings = [
        (baseline.usage.raw_total_tokens - candidate.usage.raw_total_tokens)
        / baseline.usage.raw_total_tokens
        for baseline, candidate in pairs
        if baseline.usage.raw_total_tokens > 0
    ]
    candidate_failures = sum(
        item.critical_failure for item in outcomes if item.variant == "candidate"
    )
    projects = {candidate.project_id for _, candidate in pairs}
    families = {candidate.task_family for _, candidate in pairs}
    candidate_passes = sum(candidate.passed for _, candidate in pairs)
    baseline_passes = sum(baseline.passed for baseline, _ in pairs)
    count = len(pairs)

    quality_mean = fmean(quality_deltas) if quality_deltas else 0.0
    savings_mean = fmean(savings) if savings else 0.0
    quality_ci = paired_bootstrap_interval(
        quality_deltas,
        iterations=selected.bootstrap_iterations,
        confidence=selected.confidence,
        seed=1729,
    )
    savings_ci = paired_bootstrap_interval(
        savings,
        iterations=selected.bootstrap_iterations,
        confidence=selected.confidence,
        seed=2718,
    )

    reasons: list[str] = []
    if count < selected.min_pairs:
        reasons.append(f"need {selected.min_pairs - count} more paired outcomes")
    if len(projects) < selected.min_projects:
        reasons.append("evidence does not span enough independent projects")
    if len(families) < selected.min_task_families:
        reasons.append("evidence does not span enough task families")
    if candidate_failures:
        reasons.append("candidate has a safety-critical or execution failure")
    if quality_ci[0] < -selected.noninferiority_margin:
        reasons.append("quality noninferiority is not established")
    if not savings or savings_ci[0] < selected.minimum_raw_token_savings:
        reasons.append("the lower confidence bound on raw token savings is too small")
    if candidate_passes < baseline_passes:
        reasons.append("candidate completed fewer paired tasks than baseline")
    unverified_usage = [
        item.usage.source
        for pair in pairs
        for item in pair
        if item.usage.source not in {"reported", "provider", "codex"}
    ]
    if unverified_usage:
        reasons.append("token usage includes estimated or mixed measurements")

    eligible = not reasons
    disposition = "hold"
    if candidate_failures and current_phase in {"canary", "active"}:
        disposition = "rollback"
    elif eligible and current_phase == "shadow":
        disposition = "canary"
    elif eligible and current_phase == "canary":
        disposition = "promote"

    return PromotionReport(
        eligible=eligible,
        disposition=disposition,  # type: ignore[arg-type]
        sample_pairs=count,
        project_count=len(projects),
        task_family_count=len(families),
        candidate_critical_failures=candidate_failures,
        quality_delta_mean=quality_mean,
        quality_delta_ci=quality_ci,
        raw_token_savings_mean=savings_mean,
        raw_token_savings_ci=savings_ci,
        pass_rate_candidate=candidate_passes / count if count else 0.0,
        pass_rate_baseline=baseline_passes / count if count else 0.0,
        reasons=tuple(reasons),
    )
