from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from agent_goodput.accounting import ApproximateTokenCounter
from agent_goodput.classify import classify_task
from agent_goodput.context import ContextItem, audit_paths, compile_context
from agent_goodput.delegation import delegation_gate


class ContextTests(unittest.TestCase):
    def test_deduplicates_repeated_instruction_lines(self) -> None:
        result = compile_context(
            [
                ContextItem(
                    "global",
                    "rules",
                    "Never send messages.\nKeep evidence.",
                    requirement="required",
                ),
                ContextItem("project", "rules", "Never send messages.\nRun tests."),
            ],
            token_budget=100,
            counter=ApproximateTokenCounter(),
        )
        self.assertEqual(1, result.duplicate_lines_removed)
        self.assertEqual(1, result.packet.count("Never send messages."))

    def test_required_context_never_silently_truncates(self) -> None:
        with self.assertRaises(ValueError):
            compile_context(
                [ContextItem("rules", "rules", "x" * 100, requirement="required")],
                token_budget=1,
                counter=ApproximateTokenCounter(),
            )

    def test_optional_context_can_be_omitted(self) -> None:
        result = compile_context(
            [
                ContextItem("required", "rules", "must", requirement="required"),
                ContextItem("optional", "notes", "x" * 1_000, requirement="optional"),
            ],
            token_budget=20,
            counter=ApproximateTokenCounter(),
        )
        self.assertEqual(1, len(result.selected))
        self.assertEqual(1, len(result.omitted))

    def test_audit_reports_counter_provenance(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "AGENTS.md"
            path.write_text("Run tests.", encoding="utf-8")
            result = audit_paths([path], counter=ApproximateTokenCounter())
            self.assertEqual("utf8-bytes-over-four", result[0].counter)
            self.assertFalse(result[0].exact)


class DelegationTests(unittest.TestCase):
    def test_allows_independent_time_saving_work(self) -> None:
        features = classify_task(
            "Compare multiple repositories in parallel and summarize them.",
            counter=ApproximateTokenCounter(),
        )
        result = delegation_gate(
            features,
            requested_agents=2,
            independent_work_items=2,
            duplicated_context_tokens=100,
            expected_tokens_per_agent=500,
            verification_tokens=100,
            expected_serial_ms=30_000,
            expected_parallel_ms=10_000,
            max_token_overhead_ratio=2,
        )
        self.assertTrue(result.allowed)
        self.assertEqual(2, result.recommended_agents)

    def test_denies_non_independent_work(self) -> None:
        features = classify_task(
            "Fix this one function.",
            counter=ApproximateTokenCounter(),
        )
        result = delegation_gate(
            features,
            requested_agents=2,
            independent_work_items=1,
            duplicated_context_tokens=100,
            expected_tokens_per_agent=500,
            verification_tokens=100,
            expected_serial_ms=30_000,
            expected_parallel_ms=10_000,
        )
        self.assertFalse(result.allowed)

    def test_denies_high_risk_mutation(self) -> None:
        features = classify_task(
            "Deploy production changes across multiple projects in parallel.",
            counter=ApproximateTokenCounter(),
        )
        result = delegation_gate(
            features,
            requested_agents=2,
            independent_work_items=2,
            duplicated_context_tokens=10,
            expected_tokens_per_agent=10,
            verification_tokens=10,
            expected_serial_ms=30_000,
            expected_parallel_ms=1_000,
            max_token_overhead_ratio=10,
        )
        self.assertFalse(result.allowed)


if __name__ == "__main__":
    unittest.main()
