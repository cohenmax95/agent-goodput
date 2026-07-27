from __future__ import annotations

import unittest

from agent_goodput.accounting import (
    ApproximateTokenCounter,
    TokenWeights,
    effective_tokens,
    verified_goodput,
)
from agent_goodput.models import ObligationResult, RunOutcome, TokenUsage


def outcome(*, passed: bool, critical: bool = False) -> RunOutcome:
    return RunOutcome(
        run_id=f"run-{passed}-{critical}",
        task_id="task",
        project_id="project",
        task_family="code",
        route_name="route",
        usage=TokenUsage(
            input_tokens=100,
            cached_input_tokens=20,
            output_tokens=10,
        ),
        obligations=(
            ObligationResult(
                "test",
                passed=passed,
                weight=2,
                critical=critical,
            ),
        ),
        elapsed_ms=50,
    )


class TokenUsageTests(unittest.TestCase):
    def test_cached_tokens_must_be_subset(self) -> None:
        with self.assertRaises(ValueError):
            TokenUsage(input_tokens=3, cached_input_tokens=4)

    def test_raw_total_does_not_double_count_reasoning(self) -> None:
        usage = TokenUsage(
            input_tokens=10,
            output_tokens=7,
            reasoning_tokens=5,
            response_cycles=3,
            response_cycle_source="codex:token-count-events",
        )
        self.assertEqual(17, usage.raw_total_tokens)
        self.assertEqual(3, usage.response_cycles)

    def test_effective_token_weights_are_explicit(self) -> None:
        usage = TokenUsage(input_tokens=100, cached_input_tokens=40, output_tokens=5)
        total = effective_tokens(
            usage,
            TokenWeights(uncached_input=1, cached_input=0.1, output=8),
        )
        self.assertEqual(104, total)

    def test_approximate_counter_labels_itself(self) -> None:
        counter = ApproximateTokenCounter()
        self.assertFalse(counter.exact)
        self.assertEqual(1, counter.count("abc"))
        self.assertEqual(2, counter.count("12345"))


class OutcomeTests(unittest.TestCase):
    def test_failed_task_contributes_zero_verified_work(self) -> None:
        failed = outcome(passed=False)
        self.assertEqual(0, failed.verified_work_units)
        self.assertEqual(0, verified_goodput([failed]))

    def test_passed_task_contributes_weighted_work(self) -> None:
        passed = outcome(passed=True)
        self.assertEqual(2, passed.verified_work_units)
        self.assertGreater(verified_goodput([passed]), 0)

    def test_critical_failure_zeros_partial_quality(self) -> None:
        run = RunOutcome(
            run_id="run",
            task_id="task",
            project_id="project",
            task_family="security",
            route_name="route",
            usage=TokenUsage(input_tokens=1),
            obligations=(
                ObligationResult("style", True),
                ObligationResult("no-secret", False, critical=True),
            ),
            elapsed_ms=1,
        )
        self.assertTrue(run.critical_failure)
        self.assertEqual(0, run.quality_score)

    def test_round_trip(self) -> None:
        original = outcome(passed=True)
        restored = RunOutcome.from_dict(original.to_dict())
        self.assertEqual(original, restored)


if __name__ == "__main__":
    unittest.main()
