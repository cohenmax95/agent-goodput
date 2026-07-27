from __future__ import annotations

import sqlite3
import tempfile
import unittest
from contextlib import closing
from pathlib import Path

from agent_goodput.evidence import EvidenceStore
from agent_goodput.models import ObligationResult, RunOutcome, TokenUsage
from agent_goodput.stats import (
    PromotionThresholds,
    evaluate_promotion,
    exact_two_sided_sign_test,
    wilson_interval,
)


def paired_outcomes(
    *,
    pairs: int = 6,
    candidate_tokens: int = 60,
    candidate_pass: bool = True,
    source: str = "reported",
    critical: bool = False,
) -> list[RunOutcome]:
    outcomes: list[RunOutcome] = []
    for index in range(pairs):
        for variant, tokens, passed in (
            ("baseline", 100, True),
            ("candidate", candidate_tokens, candidate_pass),
        ):
            outcomes.append(
                RunOutcome(
                    run_id=f"{index}-{variant}",
                    task_id=f"task-{index}",
                    project_id=f"project-{index % 2}",
                    task_family=f"family-{index % 3}",
                    route_name=variant,
                    usage=TokenUsage(input_tokens=tokens, source=source),
                    obligations=(
                        ObligationResult(
                            "correct",
                            passed,
                            critical=critical and variant == "candidate",
                        ),
                    ),
                    elapsed_ms=1,
                    seed=index,
                    variant=variant,
                    metadata={"bucket": "test"},
                )
            )
    return outcomes


class EvidenceTests(unittest.TestCase):
    def test_hash_chain_round_trip(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            store = EvidenceStore(Path(directory) / "evidence.sqlite3")
            store.append_many(paired_outcomes(pairs=1))
            self.assertTrue(store.verify_chain()[0])
            self.assertEqual(2, len(store.outcomes(bucket="test")))

    def test_tamper_is_detected(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "evidence.sqlite3"
            store = EvidenceStore(path)
            store.append_event("safe", {"counter": 1})
            with closing(sqlite3.connect(path)) as connection, connection:
                connection.execute(
                    "UPDATE events SET payload_json = ?",
                    ('{"counter":2}',),
                )
            self.assertFalse(store.verify_chain()[0])

    def test_raw_prompt_field_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            store = EvidenceStore(Path(directory) / "evidence.sqlite3")
            with self.assertRaises(ValueError):
                store.append_event("unsafe", {"prompt": "secret"})

    def test_duplicate_outcome_does_not_orphan_an_event(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            store = EvidenceStore(Path(directory) / "evidence.sqlite3")
            item = paired_outcomes(pairs=1)[0]
            store.append_outcome(item)
            cursor = store.cursor
            with self.assertRaises(sqlite3.IntegrityError):
                store.append_outcome(item)
            self.assertEqual(cursor, store.cursor)
            self.assertTrue(store.verify_chain()[0])


class StatisticsTests(unittest.TestCase):
    def setUp(self) -> None:
        self.thresholds = PromotionThresholds(
            min_pairs=6,
            min_projects=2,
            min_task_families=3,
            minimum_raw_token_savings=0.1,
            bootstrap_iterations=500,
        )

    def test_promotes_quality_equal_savings(self) -> None:
        report = evaluate_promotion(
            paired_outcomes(),
            thresholds=self.thresholds,
            current_phase="shadow",
        )
        self.assertTrue(report.eligible)
        self.assertEqual("canary", report.disposition)
        self.assertAlmostEqual(0.4, report.raw_token_savings_mean)

    def test_critical_failure_forces_rollback(self) -> None:
        report = evaluate_promotion(
            paired_outcomes(candidate_pass=False, critical=True),
            thresholds=self.thresholds,
            current_phase="active",
        )
        self.assertFalse(report.eligible)
        self.assertEqual("rollback", report.disposition)

    def test_estimated_usage_cannot_promote(self) -> None:
        report = evaluate_promotion(
            paired_outcomes(source="estimated:test"),
            thresholds=self.thresholds,
        )
        self.assertFalse(report.eligible)
        self.assertIn(
            "token usage includes estimated or mixed measurements",
            report.reasons,
        )

    def test_wilson_bounds(self) -> None:
        low, high = wilson_interval(10, 10)
        self.assertLess(low, 1)
        self.assertAlmostEqual(1, high)

    def test_sign_test(self) -> None:
        self.assertLess(exact_two_sided_sign_test(10, 0), 0.01)
        self.assertEqual(1, exact_two_sided_sign_test(0, 0))


if __name__ == "__main__":
    unittest.main()
