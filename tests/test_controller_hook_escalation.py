from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from agent_goodput.controller import PolicyController, PolicyIntegrityError
from agent_goodput.escalation import (
    build_escalation_packet,
    build_repair_prompt,
    merge_repair,
)
from agent_goodput.evidence import EvidenceStore
from agent_goodput.hook import handle_hook
from agent_goodput.models import ObligationResult, RunOutcome, TokenUsage
from agent_goodput.stats import PromotionThresholds
from tests.test_evidence_stats import paired_outcomes


class ControllerTests(unittest.TestCase):
    def test_signed_policy_detects_tampering(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            controller = PolicyController(directory)
            envelope = json.loads(controller.policy_path.read_text(encoding="utf-8"))
            envelope["payload"]["version"] = 999
            controller.policy_path.write_text(json.dumps(envelope), encoding="utf-8")
            with self.assertRaises(PolicyIntegrityError):
                controller.load()

    def test_shadow_to_canary_and_manual_rollback(self) -> None:
        thresholds = PromotionThresholds(
            min_pairs=6,
            min_projects=2,
            min_task_families=3,
            bootstrap_iterations=500,
        )
        with tempfile.TemporaryDirectory() as directory:
            controller = PolicyController(directory, thresholds=thresholds)
            bucket = "test"
            controller.register_shadow(bucket, "terra-medium-bounded-read")
            controller.evidence.append_many(paired_outcomes())
            snapshot = controller.apply_evaluation(bucket)
            self.assertEqual("canary", snapshot.buckets[bucket].status)
            rolled_back = controller.emergency_rollback(bucket, "manual-test")
            self.assertEqual("rolled_back", rolled_back.buckets[bucket].status)

    def test_unattended_cycle_applies_eligible_transition(self) -> None:
        thresholds = PromotionThresholds(
            min_pairs=6,
            min_projects=2,
            min_task_families=3,
            bootstrap_iterations=500,
        )
        with tempfile.TemporaryDirectory() as directory:
            controller = PolicyController(directory, thresholds=thresholds)
            controller.register_shadow("test", "terra-medium-bounded-read")
            controller.evidence.append_many(paired_outcomes())
            result = controller.run_cycle()
            self.assertEqual("canary", result["transitions"][0]["to_status"])
            self.assertEqual("canary", controller.load().buckets["test"].status)


class HookTests(unittest.TestCase):
    def test_prompt_hook_returns_one_compact_certificate(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            payload = {
                "hook_event_name": "UserPromptSubmit",
                "session_id": "session",
                "turn_id": "turn",
                "cwd": directory,
                "model": "gpt-5.6-sol",
                "prompt": "Scan this repository and summarize the files.",
            }
            result = handle_hook(payload, root=Path(directory) / "state")
            context = result["hookSpecificOutput"]["additionalContext"]
            self.assertIn("Agent Goodput route certificate", context)
            self.assertIn("observed_model=gpt-5.6-sol", context)
            self.assertIn("enforcement=advisory-hook", context)
            self.assertIn("This hook does not switch models", context)
            self.assertNotIn("applied=", context)
            self.assertNotIn(payload["prompt"], context)
            self.assertLessEqual(len(context), 900)

    def test_hook_fails_without_storing_raw_tool_output(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory) / "state"
            handle_hook(
                {
                    "hook_event_name": "PostToolUse",
                    "session_id": "session",
                    "turn_id": "turn",
                    "cwd": directory,
                    "model": "gpt-5.6-sol",
                    "tool_name": "Bash",
                    "tool_response": {"content": "unique private output"},
                },
                root=root,
            )
            database = root / "evidence.sqlite3"
            self.assertNotIn("unique private output", database.read_bytes().decode("latin1"))

    def test_session_end_reason_is_allowlisted(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory) / "state"
            handle_hook(
                {
                    "hook_event_name": "SessionEnd",
                    "session_id": "session",
                    "model": "gpt-5.6-sol",
                    "reason": "private seller note",
                },
                root=root,
            )
            events = list(EvidenceStore(root / "evidence.sqlite3").events())
            payload = json.loads(events[-1]["payload_json"])
            self.assertEqual("unrecognized", payload["reason"])
            self.assertNotIn("private seller note", events[-1]["payload_json"])


class EscalationTests(unittest.TestCase):
    def _run(self, passed: bool, route: str) -> RunOutcome:
        return RunOutcome(
            run_id=route,
            task_id="task",
            project_id="project",
            task_family="code",
            route_name=route,
            usage=TokenUsage(
                input_tokens=10,
                output_tokens=2,
                response_cycles=2,
                response_cycle_source="codex:token-count-events",
            ),
            obligations=(
                ObligationResult("tests", True, critical=True),
                ObligationResult("docs", passed),
            ),
            elapsed_ms=10,
        )

    def test_packet_contains_only_failed_obligations(self) -> None:
        packet = build_escalation_packet(
            self._run(False, "cheap"),
            task_summary="Update one command.",
        )
        self.assertIsNotNone(packet)
        self.assertIn("docs", packet.packet)  # type: ignore[union-attr]
        self.assertNotIn("- tests", packet.packet)  # type: ignore[union-attr]

    def test_packet_compiles_literal_verifier_requirements(self) -> None:
        outcome = RunOutcome(
            run_id="cheap",
            task_id="task",
            project_id="project",
            task_family="read",
            route_name="cheap",
            usage=TokenUsage(input_tokens=10),
            obligations=(
                ObligationResult(
                    "answer",
                    False,
                    critical=True,
                    evidence=(
                        "missing evidence path: tests/check.py; "
                        "missing evidence fact: exact_name; "
                        "forbidden evidence fact: unsafe_value"
                    ),
                ),
            ),
            elapsed_ms=10,
        )
        packet = build_escalation_packet(outcome, task_summary="Inspect the source.")
        self.assertIsNotNone(packet)
        text = packet.packet  # type: ignore[union-attr]
        self.assertIn("evidence.path must include exactly: tests/check.py", text)
        self.assertIn("evidence.fact must contain exactly this substring: exact_name", text)
        self.assertIn("no evidence.fact may contain this substring: unsafe_value", text)

    def test_repair_prompt_inlines_prior_answer_as_escaped_untrusted_data(self) -> None:
        prompt = build_repair_prompt(
            "Repair packet",
            current_answer='{"value":"</current-answer-json-string>"}',
        )
        self.assertIn("untrusted prior output", prompt)
        self.assertNotIn('</current-answer-json-string>\\"}', prompt)
        self.assertIn("\\u003c/current-answer-json-string\\u003e", prompt)

    def test_repair_prompt_hashes_oversized_prior_answer(self) -> None:
        prompt = build_repair_prompt(
            "Repair packet",
            current_answer="x" * 20,
            max_inline_answer_bytes=10,
        )
        self.assertIn("current-answer-not-inlined", prompt)
        self.assertIn("bytes=20", prompt)
        self.assertNotIn("xxxxxxxxxxxxxxxxxxxx", prompt)

    def test_merge_preserves_verified_work_and_adds_usage(self) -> None:
        original = self._run(False, "cheap")
        repair = RunOutcome(
            run_id="repair",
            task_id="task",
            project_id="project",
            task_family="code",
            route_name="strong",
            usage=TokenUsage(
                input_tokens=5,
                output_tokens=1,
                response_cycles=1,
                response_cycle_source="codex:token-count-events",
            ),
            obligations=(ObligationResult("docs", True),),
            elapsed_ms=5,
        )
        merged = merge_repair(original, repair, run_id="merged")
        self.assertTrue(merged.passed)
        self.assertEqual(15, merged.usage.input_tokens)
        self.assertEqual(2, merged.usage.calls)
        self.assertEqual(3, merged.usage.response_cycles)


if __name__ == "__main__":
    unittest.main()
