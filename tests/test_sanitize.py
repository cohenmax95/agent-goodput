from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from agent_goodput.sanitize import (
    sanitize_benchmark_file,
    sanitize_benchmark_report,
)


def report() -> dict[str, object]:
    usage = {
        "input_tokens": 100,
        "cached_input_tokens": 20,
        "output_tokens": 10,
        "reasoning_tokens": 0,
        "calls": 1,
        "call_count_source": "agent-run",
        "source": "codex",
    }
    return {
        "benchmark_id": "benchmark-1",
        "manifest_name": "manifest",
        "manifest_hash": "a" * 64,
        "bundle_hash": "e" * 64,
        "started_at": "2026-01-01T00:00:00Z",
        "completed_at": "2026-01-01T00:01:00Z",
        "environment": {
            "platform": "macOS-26.3-arm64",
            "machine": "arm64",
            "python": "3.13.0",
            "codex_version": "codex-cli 1.0",
            "codex_binary_sha256": "f" * 64,
        },
        "outcomes": [
            {
                "run_id": "private-random-id",
                "task_id": "task",
                "project_id": "synthetic-project",
                "task_family": "read",
                "route_name": "sol-high",
                "usage": usage,
                "obligations": [
                    {
                        "name": "correct",
                        "passed": True,
                        "weight": 1.0,
                        "critical": True,
                        "evidence": "sha256=" + "b" * 64,
                    }
                ],
                "elapsed_ms": 100,
                "seed": 1,
                "variant": "baseline",
                "error": None,
                "metadata": {
                    "bucket": "read:low:none:simple",
                    "stdout_sha256": "c" * 64,
                    "selective_escalation": {
                        "configured": True,
                        "applied": True,
                        "attempt_count": 2,
                        "initial_failure_count": 1,
                        "final_failure_count": 0,
                        "repaired": True,
                        "repair_route_name": "sol-high-selective-repair",
                        "repair_elapsed_ms": 25,
                        "repair_usage": usage,
                        "private_note": "must not be public",
                    },
                    "deterministic_completion": {
                        "configured": True,
                        "eligible": True,
                        "applied": True,
                        "completed": True,
                        "reason_code": "completed",
                        "requested_path_count": 1,
                        "requested_fact_count": 1,
                        "added_path_count": 1,
                        "certificate_count": 1,
                        "matched_line_count": 1,
                        "matched_fact_count": 1,
                        "elapsed_ms": 2,
                        "answer_before_sha256": "1" * 64,
                        "answer_after_sha256": "2" * 64,
                        "final_failure_count": 0,
                        "private_path": "tests/private.test.ts",
                    },
                    "ignored_note": "should not be public",
                },
                "passed": True,
                "critical_failure": False,
                "quality_score": 1.0,
                "verified_work_units": 1.0,
            }
        ],
        "randomized_order": ["task:baseline:1"],
        "summary": {"pair_count": 0},
    }


class SanitizerTests(unittest.TestCase):
    def test_hashes_run_id_and_generalizes_environment(self) -> None:
        public = sanitize_benchmark_report(report(), source_sha256="d" * 64)
        self.assertNotEqual(
            "private-random-id",
            public["outcomes"][0]["run_key"],
        )
        self.assertRegex(public["outcomes"][0]["run_key"], r"^run-[0-9a-f]{12}$")
        self.assertEqual("macOS", public["environment"]["operating_system"])
        self.assertEqual("codex-cli 1.0", public["environment"]["codex_version"])
        self.assertFalse(public["provenance"]["raw_answers_included"])
        self.assertEqual(64, len(public["provenance"]["sanitizer_source_sha256"]))
        self.assertNotIn("ignored_note", public["outcomes"][0]["metadata"])
        escalation = public["outcomes"][0]["metadata"]["selective_escalation"]
        self.assertTrue(escalation["applied"])
        self.assertTrue(escalation["repaired"])
        self.assertEqual(2, escalation["attempt_count"])
        self.assertEqual(25, escalation["repair_elapsed_ms"])
        self.assertEqual(100, escalation["repair_usage"]["input_tokens"])
        self.assertNotIn("private_note", escalation)
        completion = public["outcomes"][0]["metadata"]["deterministic_completion"]
        self.assertTrue(completion["completed"])
        self.assertEqual(1, completion["added_path_count"])
        self.assertEqual(1, completion["certificate_count"])
        self.assertEqual(1, completion["matched_fact_count"])
        self.assertNotIn("private_path", completion)

    def test_rejects_private_path(self) -> None:
        value = report()
        value["outcomes"][0]["metadata"]["source"] = "/Users/private/Developer/project"
        with self.assertRaisesRegex(ValueError, "private filesystem path"):
            sanitize_benchmark_report(value, source_sha256="d" * 64)

    def test_rejects_raw_answer_field(self) -> None:
        for key in ("stdout", "answer", "modelOutput", "raw-answer", "messages"):
            with self.subTest(key=key):
                value = report()
                value["outcomes"][0]["metadata"][key] = "private answer"
                with self.assertRaisesRegex(ValueError, "private benchmark field"):
                    sanitize_benchmark_report(value, source_sha256="d" * 64)

    def test_redacts_execution_error_text(self) -> None:
        value = report()
        value["outcomes"][0]["error"] = "private exception narrative"
        public = sanitize_benchmark_report(value, source_sha256="d" * 64)
        outcome = public["outcomes"][0]
        self.assertEqual("redacted", outcome["error"])
        self.assertNotEqual(
            "private exception narrative",
            outcome["error_sha256"],
        )

    def test_can_redact_obligation_evidence_for_private_workloads(self) -> None:
        public = sanitize_benchmark_report(
            report(),
            source_sha256="d" * 64,
            redact_obligation_evidence=True,
        )
        obligation = public["outcomes"][0]["obligations"][0]
        self.assertEqual("redacted", obligation["evidence"])
        self.assertEqual(64, len(obligation["evidence_sha256"]))
        self.assertTrue(public["provenance"]["obligation_evidence_redacted"])

    def test_file_output_contains_no_source_path(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = root / "private-report.json"
            destination = root / "public-report.json"
            source.write_text(json.dumps(report()), encoding="utf-8")
            sanitize_benchmark_file(source, destination)
            text = destination.read_text(encoding="utf-8")
            self.assertNotIn(str(root), text)
            self.assertIn("public_payload_sha256", text)


if __name__ == "__main__":
    unittest.main()
