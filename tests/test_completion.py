from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from agent_goodput.completion import (
    complete_missing_evidence_paths,
    missing_evidence_paths_only,
    repairable_evidence_gaps,
)
from agent_goodput.models import ObligationResult


class CompletionTests(unittest.TestCase):
    def test_extracts_only_path_only_verifier_failures(self) -> None:
        obligations = (
            ObligationResult("execution", True, critical=True),
            ObligationResult(
                "answer",
                False,
                critical=True,
                evidence=(
                    "answer_sha256=abc; missing evidence path: tests/check.test.ts; "
                    "missing evidence path: docs/check.md"
                ),
            ),
        )
        self.assertEqual(
            ("tests/check.test.ts", "docs/check.md"),
            missing_evidence_paths_only(obligations),
        )

    def test_rejects_mixed_semantic_failure(self) -> None:
        obligations = (
            ObligationResult(
                "answer",
                False,
                evidence=(
                    "answer_sha256=abc; missing evidence path: tests/check.test.ts; "
                    "missing evidence fact: FEATURE_FLAG"
                ),
            ),
        )
        self.assertIsNone(missing_evidence_paths_only(obligations))

    def test_extracts_path_and_task_explicit_fact_gaps(self) -> None:
        obligations = (
            ObligationResult(
                "answer",
                False,
                evidence=(
                    "answer_sha256=abc; missing evidence path: tests/check.test.ts; "
                    "missing evidence fact: ASSERTED"
                ),
            ),
        )
        gaps = repairable_evidence_gaps(obligations)
        self.assertIsNotNone(gaps)
        self.assertEqual(("tests/check.test.ts",), gaps.paths)  # type: ignore[union-attr]
        self.assertEqual(("ASSERTED",), gaps.facts)  # type: ignore[union-attr]

    def test_extracts_task_explicit_fact_only_gap(self) -> None:
        obligations = (
            ObligationResult(
                "answer",
                False,
                evidence="answer_sha256=abc; missing evidence fact: ASSERTED",
            ),
        )
        gaps = repairable_evidence_gaps(obligations)
        self.assertIsNotNone(gaps)
        self.assertEqual((), gaps.paths)  # type: ignore[union-attr]
        self.assertEqual(("ASSERTED",), gaps.facts)  # type: ignore[union-attr]

    def test_completes_path_from_terms_already_in_task_and_answer(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "tests").mkdir()
            (root / "tests" / "check.test.ts").write_text(
                "expect(result.kind).toBe('FEATURE_FLAG');\n",
                encoding="utf-8",
            )
            answer = {
                "task_id": "task",
                "conclusion": "FEATURE_FLAG",
                "evidence": [
                    {
                        "path": "src/check.ts",
                        "fact": "FEATURE_FLAG is selected by the source branch.",
                    }
                ],
                "uncertainties": [],
            }
            (root / "answer.json").write_text(json.dumps(answer), encoding="utf-8")

            completed = complete_missing_evidence_paths(
                workspace=root,
                answer_file="answer.json",
                missing_paths=("tests/check.test.ts",),
                task_text="Cite the `FEATURE_FLAG` regression evidence.",
            )

            self.assertTrue(completed.applied)
            self.assertTrue(completed.completed)
            self.assertEqual(1, completed.added_path_count)
            self.assertEqual(1, completed.certificate_count)
            updated = json.loads((root / "answer.json").read_text(encoding="utf-8"))
            self.assertEqual("tests/check.test.ts", updated["evidence"][1]["path"])
            self.assertIn("FEATURE_FLAG", updated["evidence"][1]["fact"])

    def test_fails_closed_without_a_source_match(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "tests").mkdir()
            (root / "tests" / "check.test.ts").write_text(
                "unrelated assertion\n",
                encoding="utf-8",
            )
            original = {
                "task_id": "task",
                "conclusion": "FEATURE_FLAG",
                "evidence": [{"path": "src/check.ts", "fact": "FEATURE_FLAG"}],
                "uncertainties": [],
            }
            path = root / "answer.json"
            path.write_text(json.dumps(original), encoding="utf-8")

            completed = complete_missing_evidence_paths(
                workspace=root,
                answer_file=path,
                missing_paths=("tests/check.test.ts",),
                task_text="Inspect `FEATURE_FLAG`.",
            )

            self.assertFalse(completed.completed)
            self.assertEqual("no-source-match", completed.reason_code)
            self.assertEqual(original, json.loads(path.read_text(encoding="utf-8")))

    def test_completes_path_and_fact_when_task_and_source_both_contain_it(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "tests").mkdir()
            (root / "tests" / "check.test.ts").write_text(
                "expect(FEATURE_FLAG).toBe(true); // ASSERTED\n",
                encoding="utf-8",
            )
            path = root / "answer.json"
            path.write_text(
                json.dumps(
                    {
                        "task_id": "task",
                        "conclusion": "FEATURE_FLAG",
                        "evidence": [{"path": "src/check.ts", "fact": "FEATURE_FLAG"}],
                        "uncertainties": [],
                    }
                ),
                encoding="utf-8",
            )

            completed = complete_missing_evidence_paths(
                workspace=root,
                answer_file=path,
                missing_paths=("tests/check.test.ts",),
                missing_facts=("ASSERTED",),
                task_text="The evidence must include `ASSERTED`.",
            )

            self.assertTrue(completed.completed)
            self.assertEqual(1, completed.added_path_count)
            self.assertEqual(1, completed.certificate_count)
            self.assertEqual(1, completed.matched_fact_count)
            updated = json.loads(path.read_text(encoding="utf-8"))
            self.assertIn("ASSERTED", updated["evidence"][1]["fact"])
            self.assertNotIn("expect(FEATURE_FLAG)", updated["evidence"][1]["fact"])
            self.assertIn("lines=L1", updated["evidence"][1]["fact"])

    def test_completes_task_explicit_fact_from_answer_cited_path(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "src").mkdir()
            (root / "src" / "safety.ts").write_text(
                "const audit = 'No messages were sent.';\n",
                encoding="utf-8",
            )
            path = root / "answer.json"
            path.write_text(
                json.dumps(
                    {
                        "task_id": "task",
                        "conclusion": "REVIEW_ONLY",
                        "evidence": [
                            {
                                "path": "src/safety.ts:1",
                                "fact": "The operation remains review-only.",
                            }
                        ],
                        "uncertainties": [],
                    }
                ),
                encoding="utf-8",
            )

            completed = complete_missing_evidence_paths(
                workspace=root,
                answer_file=path,
                missing_paths=(),
                missing_facts=("No messages were sent",),
                task_text="The evidence must explicitly include `No messages were sent`.",
            )

            self.assertTrue(completed.completed)
            self.assertEqual(0, completed.added_path_count)
            self.assertEqual(1, completed.certificate_count)
            self.assertEqual(1, completed.matched_fact_count)
            updated = json.loads(path.read_text(encoding="utf-8"))
            self.assertEqual("src/safety.ts", updated["evidence"][1]["path"])
            self.assertIn("No messages were sent", updated["evidence"][1]["fact"])
            self.assertNotIn("const audit", updated["evidence"][1]["fact"])

    def test_sources_missing_fact_from_existing_path_separately(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "src").mkdir()
            (root / "src" / "existing.ts").write_text(
                "// promote the durable owner link\n",
                encoding="utf-8",
            )
            (root / "src" / "missing.ts").write_text(
                "const resolvedBrokerId = session.brokerId;\n",
                encoding="utf-8",
            )
            path = root / "answer.json"
            path.write_text(
                json.dumps(
                    {
                        "task_id": "task",
                        "conclusion": "resolvedBrokerId",
                        "evidence": [
                            {
                                "path": "src/existing.ts",
                                "fact": "The owner link is promoted.",
                            }
                        ],
                        "uncertainties": [],
                    }
                ),
                encoding="utf-8",
            )

            completed = complete_missing_evidence_paths(
                workspace=root,
                answer_file=path,
                missing_paths=("src/missing.ts",),
                missing_facts=("durable",),
                task_text=(
                    "Cite both paths and explain the `durable` owner link using `resolvedBrokerId`."
                ),
            )

            self.assertTrue(completed.completed)
            self.assertEqual(1, completed.added_path_count)
            self.assertEqual(2, completed.certificate_count)
            self.assertEqual(1, completed.matched_fact_count)
            updated = json.loads(path.read_text(encoding="utf-8"))
            self.assertEqual(
                ["src/existing.ts", "src/missing.ts", "src/existing.ts"],
                [item["path"] for item in updated["evidence"]],
            )

    def test_refuses_fact_not_already_present_in_task_or_answer(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "tests").mkdir()
            (root / "tests" / "check.test.ts").write_text(
                "expect(FEATURE_FLAG).toBe(true); // HIDDEN_FACT\n",
                encoding="utf-8",
            )
            path = root / "answer.json"
            path.write_text(
                json.dumps(
                    {
                        "task_id": "task",
                        "conclusion": "FEATURE_FLAG",
                        "evidence": [{"path": "src/check.ts", "fact": "FEATURE_FLAG"}],
                        "uncertainties": [],
                    }
                ),
                encoding="utf-8",
            )
            completed = complete_missing_evidence_paths(
                workspace=root,
                answer_file=path,
                missing_paths=("tests/check.test.ts",),
                missing_facts=("HIDDEN_FACT",),
                task_text="Inspect `FEATURE_FLAG`.",
            )
            self.assertFalse(completed.completed)
            self.assertEqual("untrusted-missing-fact", completed.reason_code)

    def test_refuses_oversized_verifier_fact(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "tests").mkdir()
            oversized = "A" * 81
            (root / "tests" / "check.test.ts").write_text(
                f"const marker = '{oversized}';\n",
                encoding="utf-8",
            )
            path = root / "answer.json"
            path.write_text(
                json.dumps(
                    {
                        "task_id": "task",
                        "conclusion": oversized,
                        "evidence": [],
                        "uncertainties": [],
                    }
                ),
                encoding="utf-8",
            )

            completed = complete_missing_evidence_paths(
                workspace=root,
                answer_file=path,
                missing_paths=("tests/check.test.ts",),
                missing_facts=(oversized,),
                task_text=f"Verify {oversized}.",
            )

            self.assertFalse(completed.completed)
            self.assertEqual("limit-exceeded", completed.reason_code)

    def test_rejects_path_escape(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            path = root / "answer.json"
            path.write_text(
                json.dumps(
                    {
                        "task_id": "task",
                        "conclusion": "FEATURE_FLAG",
                        "evidence": [{"path": "src/check.ts", "fact": "FEATURE_FLAG"}],
                        "uncertainties": [],
                    }
                ),
                encoding="utf-8",
            )
            completed = complete_missing_evidence_paths(
                workspace=root,
                answer_file=path,
                missing_paths=("../secret.txt",),
                task_text="Inspect `FEATURE_FLAG`.",
            )
            self.assertFalse(completed.completed)
            self.assertEqual("unsafe-or-missing-path", completed.reason_code)

    def test_rejects_parent_symlink_source_path(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            outside = root / "outside"
            workspace = root / "workspace"
            outside.mkdir()
            workspace.mkdir()
            (outside / "check.ts").write_text(
                "export const FEATURE_FLAG = true;\n",
                encoding="utf-8",
            )
            (workspace / "linked").symlink_to(outside, target_is_directory=True)
            path = workspace / "answer.json"
            path.write_text(
                json.dumps(
                    {
                        "task_id": "task",
                        "conclusion": "FEATURE_FLAG",
                        "evidence": [],
                        "uncertainties": [],
                    }
                ),
                encoding="utf-8",
            )

            completed = complete_missing_evidence_paths(
                workspace=workspace,
                answer_file=path,
                missing_paths=("linked/check.ts",),
                task_text="Inspect `FEATURE_FLAG`.",
            )

            self.assertFalse(completed.completed)
            self.assertEqual("unsafe-or-missing-path", completed.reason_code)

    def test_rejects_answer_path_outside_workspace(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            workspace = root / "workspace"
            workspace.mkdir()
            outside = root / "answer.json"
            outside.write_text("{}", encoding="utf-8")
            completed = complete_missing_evidence_paths(
                workspace=workspace,
                answer_file=outside,
                missing_paths=("tests/check.test.ts",),
                task_text="Inspect `FEATURE_FLAG`.",
            )
            self.assertFalse(completed.applied)
            self.assertEqual("unsafe-answer-path", completed.reason_code)


if __name__ == "__main__":
    unittest.main()
