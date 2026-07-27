from __future__ import annotations

import unittest
from dataclasses import replace
from pathlib import Path

from agent_goodput.accounting import ApproximateTokenCounter
from agent_goodput.classify import classify_task
from agent_goodput.models import RiskLevel
from agent_goodput.policy import BucketPolicy, PolicySnapshot, decide, proposed_route


class ClassifierTests(unittest.TestCase):
    def test_read_only_research_is_low_risk(self) -> None:
        features = classify_task(
            "Scan this repository and summarize its architecture.",
            counter=ApproximateTokenCounter(),
        )
        self.assertEqual(RiskLevel.LOW, features.risk)
        self.assertEqual("none", features.write_scope)
        self.assertEqual("research", features.task_kind)
        self.assertIn("inventory", features.deterministic_prework)

    def test_external_destructive_action_is_critical(self) -> None:
        features = classify_task(
            "Delete the production database and deploy the reset.",
            counter=ApproximateTokenCounter(),
        )
        self.assertEqual(RiskLevel.CRITICAL, features.risk)
        self.assertEqual("external", features.write_scope)

    def test_negative_constraints_do_not_become_actions(self) -> None:
        features = classify_task(
            "Read the repository. Do not edit files, publish, or delete anything.",
            counter=ApproximateTokenCounter(),
        )
        self.assertEqual(RiskLevel.LOW, features.risk)
        self.assertEqual("none", features.write_scope)

    def test_consumption_tokens_are_not_access_tokens(self) -> None:
        features = classify_task(
            "Audit token consumption and explain the total.",
            counter=ApproximateTokenCounter(),
        )
        self.assertFalse(features.sensitive)
        self.assertEqual(RiskLevel.LOW, features.risk)

    def test_security_review_stays_on_baseline(self) -> None:
        features = classify_task(
            "Perform a read-only security review for path traversal.",
            counter=ApproximateTokenCounter(),
        )
        self.assertEqual(RiskLevel.HIGH, features.risk)
        self.assertIsNone(proposed_route(features))

    def test_commercial_closing_stays_on_baseline(self) -> None:
        features = classify_task(
            "Review the commercial property closing package for Monday and reconcile "
            "the executed PSA, title exceptions, loan commitment, and wire instructions.",
            counter=ApproximateTokenCounter(),
        )
        self.assertEqual(RiskLevel.HIGH, features.risk)
        self.assertIsNone(proposed_route(features))

    def test_closing_a_local_file_is_not_a_property_closing(self) -> None:
        features = classify_task(
            "Read this function and explain how it closes a local file handle.",
            counter=ApproximateTokenCounter(),
        )
        self.assertEqual(RiskLevel.LOW, features.risk)

    def test_quality_request_keeps_baseline(self) -> None:
        features = classify_task(
            "Do the deepest possible audit and maintain quality.",
            counter=ApproximateTokenCounter(),
        )
        self.assertTrue(features.explicit_quality_request)
        self.assertIsNone(proposed_route(features))

    def test_prompt_is_fingerprinted_not_retained(self) -> None:
        prompt = "private unique words"
        features = classify_task(prompt, counter=ApproximateTokenCounter())
        self.assertNotIn(prompt, str(features.to_dict()))

    def test_confirmatory_tasks_match_declared_candidate_routes(self) -> None:
        root = Path(__file__).resolve().parents[1] / "benchmarks" / "tasks"
        expected = {
            "mailbox-state.md": "terra-medium-bounded-read",
            "config-precedence-confirmatory.md": "terra-medium-bounded-read",
            "call-identity.md": "terra-medium-bounded-read",
            "log-diagnosis.md": "terra-medium-bounded-read",
            "path-traversal.md": None,
            "closing-ambiguity.md": None,
            "phone-normalizer.md": "sol-medium",
        }
        for filename, route_name in expected.items():
            with self.subTest(filename=filename):
                features = classify_task(
                    (root / filename).read_text(encoding="utf-8"),
                    counter=ApproximateTokenCounter(),
                )
                route = proposed_route(features)
                self.assertEqual(route_name, route.name if route else None)


class PolicyTests(unittest.TestCase):
    def test_candidate_starts_in_shadow(self) -> None:
        features = classify_task(
            "Scan the files and summarize them.",
            counter=ApproximateTokenCounter(),
        )
        decision = decide(features)
        self.assertEqual("shadow", decision.mode)
        self.assertEqual("sol-high", decision.applied_route.name)
        self.assertIsNotNone(decision.candidate_route)

    def test_active_bucket_applies_candidate(self) -> None:
        features = classify_task(
            "Scan the files and summarize them.",
            counter=ApproximateTokenCounter(),
        )
        candidate = proposed_route(features)
        self.assertIsNotNone(candidate)
        snapshot = PolicySnapshot.default()
        snapshot = replace(
            snapshot,
            buckets={
                features.bucket: BucketPolicy(
                    route_name=candidate.name,  # type: ignore[union-attr]
                    status="active",
                    canary_fraction=1,
                )
            },
        )
        decision = decide(features, snapshot)
        self.assertEqual("active", decision.mode)
        self.assertEqual(candidate, decision.applied_route)

    def test_canary_assignment_is_deterministic(self) -> None:
        features = classify_task(
            "Scan this repository for patterns.",
            counter=ApproximateTokenCounter(),
        )
        candidate = proposed_route(features)
        snapshot = replace(
            PolicySnapshot.default(),
            buckets={
                features.bucket: BucketPolicy(
                    route_name=candidate.name,  # type: ignore[union-attr]
                    status="canary",
                    canary_fraction=0.5,
                )
            },
        )
        first = decide(features, snapshot)
        second = decide(features, snapshot)
        self.assertEqual(first.applied_route, second.applied_route)
        self.assertEqual(first.mode, second.mode)


if __name__ == "__main__":
    unittest.main()
