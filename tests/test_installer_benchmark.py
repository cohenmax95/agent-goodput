from __future__ import annotations

import hashlib
import json
import os
import shlex
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from agent_goodput.benchmark import (
    ManifestError,
    benchmark_bundle_hash,
    normalize_evidence_path,
    run_benchmark,
    validate_manifest,
    validate_runtime_lock,
)
from agent_goodput.installer import bundle_files, install, uninstall


class InstallerTests(unittest.TestCase):
    def test_packaged_bundle_fallback_is_complete(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            files = bundle_files(directory)
        self.assertIn(".codex-plugin/plugin.json", files)
        self.assertIn("hooks/hooks.json", files)
        self.assertIn("hooks/agent_goodput_hook.py", files)
        self.assertIn("skills/agent-goodput/SKILL.md", files)
        self.assertIn("src/agent_goodput/hook.py", files)

    def test_packaged_plugin_assets_match_repository_assets(self) -> None:
        root = Path(__file__).resolve().parents[1]
        packaged = root / "src" / "agent_goodput" / "assets"
        pairs = (
            (".codex-plugin/plugin.json", ".codex-plugin/plugin.json"),
            ("hooks/hooks.json", "hooks/hooks.json"),
            ("hooks/agent_goodput_hook.py", "hooks/agent_goodput_hook.py"),
            ("skills/agent-goodput/SKILL.md", "skills/agent-goodput/SKILL.md"),
            (
                "skills/agent-goodput/references/metrics.md",
                "skills/agent-goodput/references/metrics.md",
            ),
            (
                "skills/agent-goodput/agents/openai.yaml",
                "skills/agent-goodput/agents/openai.yaml",
            ),
        )
        for repository_path, packaged_path in pairs:
            with self.subTest(path=repository_path):
                self.assertEqual(
                    (root / repository_path).read_bytes(),
                    (packaged / packaged_path).read_bytes(),
                )

    def test_install_and_uninstall_are_hash_owned(self) -> None:
        source = Path(__file__).resolve().parents[1]
        with tempfile.TemporaryDirectory() as directory:
            home = Path(directory) / ".agents"
            preview = install(source, home, apply=False)
            self.assertTrue(preview.apply_allowed)
            self.assertTrue(preview.actions)
            install(source, home, apply=True)
            target = home / "plugins" / "agent-goodput"
            self.assertTrue((target / ".codex-plugin" / "plugin.json").exists())
            marketplace = json.loads(
                (home / "plugins" / "marketplace.json").read_text(encoding="utf-8")
            )
            entry = next(item for item in marketplace["plugins"] if item["name"] == "agent-goodput")
            self.assertEqual("./.agents/plugins/agent-goodput", entry["source"]["path"])
            self.assertEqual(
                target.resolve(),
                (home.parent / entry["source"]["path"]).resolve(),
            )
            hooks = json.loads((target / "hooks" / "hooks.json").read_text(encoding="utf-8"))
            commands = [
                hook["command"]
                for groups in hooks["hooks"].values()
                for group in groups
                for hook in group["hooks"]
            ]
            self.assertTrue(commands)
            expected_prefix = f"{shlex.quote(sys.executable)} -B "
            self.assertTrue(all(command.startswith(expected_prefix) for command in commands))
            self.assertFalse(install(source, home, apply=False).actions)
            payload = {
                "hook_event_name": "UserPromptSubmit",
                "session_id": "test-session",
                "turn_id": "test-turn",
                "cwd": directory,
                "model": "gpt-5.6-sol",
                "prompt": "Read one small file.",
            }
            environment = dict(os.environ)
            environment.update(
                {
                    "PLUGIN_ROOT": str(target),
                    "PLUGIN_DATA": str(Path(directory) / "plugin-data"),
                }
            )
            completed = subprocess.run(
                [
                    sys.executable,
                    "-B",
                    str(target / "hooks" / "agent_goodput_hook.py"),
                ],
                input=json.dumps(payload),
                capture_output=True,
                check=True,
                text=True,
                env=environment,
            )
            self.assertIn("advisory-hook", completed.stdout)
            self.assertFalse(any(target.rglob("__pycache__")))
            removal = uninstall(home, apply=False)
            self.assertTrue(removal.apply_allowed)
            uninstall(home, apply=True)
            self.assertFalse(target.exists())

    def test_legacy_marketplace_entry_is_migrated_when_install_is_owned(self) -> None:
        source = Path(__file__).resolve().parents[1]
        with tempfile.TemporaryDirectory() as directory:
            home = Path(directory) / ".agents"
            install(source, home, apply=True)
            marketplace_path = home / "plugins" / "marketplace.json"
            marketplace = json.loads(marketplace_path.read_text(encoding="utf-8"))
            entry = next(item for item in marketplace["plugins"] if item["name"] == "agent-goodput")
            entry["source"]["path"] = "./agent-goodput"
            marketplace_path.write_text(
                json.dumps(marketplace, indent=2) + "\n",
                encoding="utf-8",
            )

            preview = install(source, home, apply=False)
            self.assertTrue(preview.apply_allowed)
            self.assertIn("update personal marketplace entry", preview.actions)
            install(source, home, apply=True)

            migrated = json.loads(marketplace_path.read_text(encoding="utf-8"))
            migrated_entry = next(
                item for item in migrated["plugins"] if item["name"] == "agent-goodput"
            )
            self.assertEqual(
                "./.agents/plugins/agent-goodput",
                migrated_entry["source"]["path"],
            )

    def test_modified_installed_file_is_preserved(self) -> None:
        source = Path(__file__).resolve().parents[1]
        with tempfile.TemporaryDirectory() as directory:
            home = Path(directory) / ".agents"
            install(source, home, apply=True)
            path = home / "plugins" / "agent-goodput" / "hooks" / "hooks.json"
            path.write_text("{}\n", encoding="utf-8")
            removal = uninstall(home, apply=False)
            self.assertFalse(removal.apply_allowed)
            self.assertTrue(removal.conflicts)
            self.assertTrue(path.exists())

    def test_symlinked_plugin_target_is_refused(self) -> None:
        source = Path(__file__).resolve().parents[1]
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            home = root / ".agents"
            outside = root / "outside"
            outside.mkdir()
            plugins = home / "plugins"
            plugins.mkdir(parents=True)
            (plugins / "agent-goodput").symlink_to(outside, target_is_directory=True)
            plan = install(source, home, apply=False)
            self.assertFalse(plan.apply_allowed)
            self.assertIn("symlinked", plan.conflicts[0])
            with self.assertRaisesRegex(RuntimeError, "conflicts"):
                install(source, home, apply=True)
            self.assertFalse(any(outside.iterdir()))

    def test_symlinked_managed_file_is_preserved_on_uninstall(self) -> None:
        source = Path(__file__).resolve().parents[1]
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            home = root / ".agents"
            install(source, home, apply=True)
            target = home / "plugins" / "agent-goodput"
            path = target / "hooks" / "hooks.json"
            outside = root / "outside.json"
            outside.write_text(path.read_text(encoding="utf-8"), encoding="utf-8")
            path.unlink()
            path.symlink_to(outside)
            plan = uninstall(home, apply=False)
            self.assertFalse(plan.apply_allowed)
            self.assertTrue(any("symlinked" in conflict for conflict in plan.conflicts))
            self.assertTrue(outside.exists())


class BenchmarkTests(unittest.TestCase):
    def _fixture(self, root: Path) -> Path:
        fixture = root / "fixture"
        fixture.mkdir()
        (fixture / "input.txt").write_text("source\n", encoding="utf-8")
        driver = root / "driver.py"
        driver.write_text(
            """
import json
import os
from pathlib import Path

workspace = Path(os.environ["AGP_WORKSPACE"])
variant = os.environ["AGP_VARIANT"]
(workspace / "result.txt").write_text("correct\\n", encoding="utf-8")
tokens = 100 if variant == "baseline" else 60
(workspace / ".usage.json").write_text(json.dumps({
    "input_tokens": tokens,
    "output_tokens": 0,
    "calls": 1,
    "source": "reported"
}), encoding="utf-8")
print("done")
""".strip()
            + "\n",
            encoding="utf-8",
        )
        manifest = {
            "schema_version": 1,
            "name": "unit",
            "random_seed": 7,
            "variants": {
                "baseline": {
                    "route_name": "baseline",
                    "command": [sys.executable, str(driver)],
                    "usage_file": ".usage.json",
                },
                "candidate": {
                    "route_name": "candidate",
                    "command": [sys.executable, str(driver)],
                    "usage_file": ".usage.json",
                },
            },
            "tasks": [
                {
                    "id": "task",
                    "family": "code",
                    "fixture": "fixture",
                    "instruction": "Produce result.txt",
                    "seeds": [1],
                    "evaluators": [
                        {
                            "type": "exit_code",
                            "name": "execution",
                            "critical": True,
                        },
                        {
                            "type": "file_contains",
                            "name": "correct-output",
                            "path": "result.txt",
                            "value": "correct",
                            "critical": True,
                        },
                    ],
                }
            ],
        }
        path = root / "manifest.json"
        path.write_text(json.dumps(manifest), encoding="utf-8")
        return path

    def test_paired_runner_reports_quality_and_savings(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            result = run_benchmark(self._fixture(root), root / "results")
            summary = result.summary()
            self.assertEqual(1, summary["pair_count"])
            self.assertEqual(1, summary["baseline"]["pass_rate"])
            self.assertEqual(1, summary["candidate"]["pass_rate"])
            self.assertAlmostEqual(0.4, summary["raw_token_savings"])
            self.assertFalse(summary["promotion"]["eligible"])
            self.assertIn(
                "need 29 more paired outcomes",
                summary["promotion"]["reasons"],
            )

    def test_candidate_repairs_only_failed_allowed_obligations_once(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            fixture = root / "fixture"
            fixture.mkdir()
            (fixture / "input.txt").write_text("source\n", encoding="utf-8")
            driver = root / "repair_driver.py"
            driver.write_text(
                """
import json
import os
from pathlib import Path

workspace = Path(os.environ["AGP_WORKSPACE"])
variant = os.environ["AGP_VARIANT"]
repair = variant.endswith("-repair")
correct = variant == "baseline" or repair
result = "correct\\n" if correct else "incomplete\\n"
(workspace / "result.txt").write_text(result, encoding="utf-8")
usage_file = ".repair-usage.json" if repair else ".usage.json"
tokens = 20 if repair else (100 if variant == "baseline" else 60)
(workspace / usage_file).write_text(json.dumps({
    "input_tokens": tokens,
    "output_tokens": 0,
    "calls": 1,
    "call_count_source": "agent-run",
    "source": "reported"
}), encoding="utf-8")
print("done")
""".strip()
                + "\n",
                encoding="utf-8",
            )
            manifest = {
                "schema_version": 1,
                "name": "repair-unit",
                "random_seed": 7,
                "variants": {
                    "baseline": {
                        "route_name": "baseline",
                        "command": [sys.executable, str(driver)],
                        "usage_file": ".usage.json",
                    },
                    "candidate": {
                        "route_name": "candidate",
                        "command": [sys.executable, str(driver)],
                        "usage_file": ".usage.json",
                        "repair": {
                            "route_name": "strong-repair",
                            "command": [sys.executable, str(driver)],
                            "usage_file": ".repair-usage.json",
                            "on_evaluator_types": ["file_contains"],
                        },
                    },
                },
                "tasks": [
                    {
                        "id": "task",
                        "family": "code",
                        "fixture": "fixture",
                        "instruction": "Produce the required result.",
                        "seeds": [1],
                        "evaluators": [
                            {
                                "type": "exit_code",
                                "name": "execution",
                                "critical": True,
                            },
                            {
                                "type": "file_contains",
                                "name": "complete",
                                "path": "result.txt",
                                "value": "correct",
                                "critical": True,
                            },
                        ],
                    }
                ],
            }
            manifest_path = root / "manifest.json"
            manifest_path.write_text(json.dumps(manifest), encoding="utf-8")

            result = run_benchmark(manifest_path, root / "results")
            candidate = next(item for item in result.outcomes if item.variant == "candidate")
            baseline = next(item for item in result.outcomes if item.variant == "baseline")
            self.assertTrue(candidate.passed)
            self.assertTrue(baseline.passed)
            self.assertEqual(80, candidate.usage.raw_total_tokens)
            self.assertEqual(2, candidate.usage.calls)
            self.assertEqual("candidate+strong-repair", candidate.route_name)
            escalation = candidate.metadata["selective_escalation"]
            self.assertTrue(escalation["applied"])
            self.assertTrue(escalation["repaired"])
            self.assertEqual(1, escalation["initial_failure_count"])
            self.assertEqual(0, escalation["final_failure_count"])
            summary = result.summary()["candidate"]
            self.assertEqual(1, summary["repair_count"])
            self.assertEqual(1, summary["repair_success_count"])
            self.assertEqual(20, summary["repair_raw_tokens"])
            self.assertEqual(2, summary["agent_run_invocations"])
            self.assertEqual(80, summary["input_tokens"])
            benchmark_dir = root / "results" / result.benchmark_id
            self.assertFalse(any(benchmark_dir.rglob("instruction.txt")))
            self.assertFalse(any(benchmark_dir.rglob(".agent-goodput-repair-packet.txt")))

    def test_candidate_completes_lexical_evidence_without_an_agent_retry(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            fixture = root / "fixture"
            (fixture / "src").mkdir(parents=True)
            (fixture / "tests").mkdir()
            (fixture / "src" / "check.ts").write_text(
                "export const FEATURE_FLAG = true;\n",
                encoding="utf-8",
            )
            (fixture / "tests" / "check.test.ts").write_text(
                "expect(FEATURE_FLAG).toBe(true); // ASSERTED\n",
                encoding="utf-8",
            )
            driver = root / "completion_driver.py"
            driver.write_text(
                """
import json
import os
from pathlib import Path

workspace = Path(os.environ["AGP_WORKSPACE"])
variant = os.environ["AGP_VARIANT"]
evidence = [
    {"path": "src/check.ts", "fact": "FEATURE_FLAG is true."},
    {
        "path": "tests/check.test.ts",
        "fact": (
            "FEATURE_FLAG is ASSERTED."
            if variant == "baseline"
            else "FEATURE_FLAG is covered by regression evidence."
        ),
    },
]
(workspace / "answer.json").write_text(json.dumps({
    "task_id": "task",
    "conclusion": "FEATURE_FLAG",
    "evidence": evidence,
    "uncertainties": []
}), encoding="utf-8")
(workspace / ".usage.json").write_text(json.dumps({
    "input_tokens": 100 if variant == "baseline" else 60,
    "output_tokens": 0,
    "calls": 1,
    "call_count_source": "agent-run",
    "source": "reported"
}), encoding="utf-8")
print("done")
""".strip()
                + "\n",
                encoding="utf-8",
            )
            manifest = {
                "schema_version": 1,
                "name": "completion-unit",
                "random_seed": 7,
                "variants": {
                    "baseline": {
                        "route_name": "baseline",
                        "command": [sys.executable, str(driver)],
                        "usage_file": ".usage.json",
                    },
                    "candidate": {
                        "route_name": "candidate",
                        "command": [sys.executable, str(driver)],
                        "usage_file": ".usage.json",
                        "deterministic_completion": {
                            "kind": "evidence-path-certificate",
                            "max_files": 2,
                            "max_file_bytes": 1000,
                        },
                    },
                },
                "tasks": [
                    {
                        "id": "task",
                        "family": "read",
                        "fixture": "fixture",
                        "instruction": (
                            "Cite source and regression evidence for `FEATURE_FLAG`. "
                            "The evidence must include `ASSERTED`."
                        ),
                        "seeds": [1],
                        "evaluators": [
                            {
                                "type": "exit_code",
                                "name": "execution",
                                "critical": True,
                            },
                            {
                                "type": "answer_contract",
                                "name": "answer",
                                "critical": True,
                                "path": "answer.json",
                                "task_id": "task",
                                "conclusion": "FEATURE_FLAG",
                                "required_paths": [
                                    "src/check.ts",
                                    "tests/check.test.ts",
                                ],
                                "fact_contains": ["FEATURE_FLAG", "ASSERTED"],
                            },
                        ],
                    }
                ],
            }
            manifest_path = root / "manifest.json"
            manifest_path.write_text(json.dumps(manifest), encoding="utf-8")

            result = run_benchmark(manifest_path, root / "results")
            candidate = next(item for item in result.outcomes if item.variant == "candidate")
            self.assertTrue(candidate.passed)
            self.assertEqual(1, candidate.usage.calls)
            completion = candidate.metadata["deterministic_completion"]
            self.assertTrue(completion["applied"])
            self.assertTrue(completion["completed"])
            self.assertEqual(0, completion["added_path_count"])
            self.assertEqual(1, completion["certificate_count"])
            self.assertEqual(1, completion["matched_fact_count"])
            summary = result.summary()["candidate"]
            self.assertEqual(1, summary["deterministic_completion_count"])
            self.assertEqual(1, summary["deterministic_completion_attempt_count"])
            self.assertEqual(0, summary["deterministic_completion_refusal_count"])
            self.assertEqual(1, summary["deterministic_completion_success_count"])
            self.assertEqual(1, summary["deterministic_completion_certificates_added"])
            self.assertEqual(1, summary["deterministic_completion_facts_matched"])

    def test_candidate_sources_fact_from_a_separate_answer_cited_path(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            fixture = root / "fixture"
            (fixture / "src").mkdir(parents=True)
            (fixture / "src" / "primary.ts").write_text(
                "const resolvedBrokerId = session.brokerId;\n",
                encoding="utf-8",
            )
            (fixture / "src" / "context.ts").write_text(
                "// promote the durable owner link\n",
                encoding="utf-8",
            )
            driver = root / "completion_driver.py"
            driver.write_text(
                """
import json
import os
from pathlib import Path

workspace = Path(os.environ["AGP_WORKSPACE"])
variant = os.environ["AGP_VARIANT"]
if variant == "baseline":
    evidence = [
        {"path": "src/primary.ts", "fact": "resolvedBrokerId is durable."},
        {"path": "src/context.ts", "fact": "The durable owner link is promoted."},
    ]
else:
    evidence = [
        {"path": "src/context.ts", "fact": "The owner link is promoted."},
    ]
(workspace / "answer.json").write_text(json.dumps({
    "task_id": "task",
    "conclusion": "resolvedBrokerId",
    "evidence": evidence,
    "uncertainties": []
}), encoding="utf-8")
(workspace / ".usage.json").write_text(json.dumps({
    "input_tokens": 100 if variant == "baseline" else 60,
    "output_tokens": 0,
    "calls": 1,
    "call_count_source": "agent-run",
    "source": "reported"
}), encoding="utf-8")
print("done")
""".strip()
                + "\n",
                encoding="utf-8",
            )
            manifest = {
                "schema_version": 1,
                "name": "completion-cross-path-unit",
                "random_seed": 11,
                "variants": {
                    "baseline": {
                        "route_name": "baseline",
                        "command": [sys.executable, str(driver)],
                        "usage_file": ".usage.json",
                    },
                    "candidate": {
                        "route_name": "candidate",
                        "command": [sys.executable, str(driver)],
                        "usage_file": ".usage.json",
                        "deterministic_completion": {
                            "kind": "evidence-path-certificate",
                            "max_files": 2,
                            "max_file_bytes": 1000,
                        },
                    },
                },
                "tasks": [
                    {
                        "id": "task",
                        "family": "read",
                        "fixture": "fixture",
                        "instruction": (
                            "Cite both paths for `resolvedBrokerId` and explain the "
                            "`durable` owner link."
                        ),
                        "seeds": [1],
                        "evaluators": [
                            {
                                "type": "exit_code",
                                "name": "execution",
                                "critical": True,
                            },
                            {
                                "type": "answer_contract",
                                "name": "answer",
                                "critical": True,
                                "path": "answer.json",
                                "task_id": "task",
                                "conclusion": "resolvedBrokerId",
                                "required_paths": [
                                    "src/primary.ts",
                                    "src/context.ts",
                                ],
                                "fact_contains": ["resolvedBrokerId", "durable"],
                            },
                        ],
                    }
                ],
            }
            manifest_path = root / "manifest.json"
            manifest_path.write_text(json.dumps(manifest), encoding="utf-8")

            result = run_benchmark(manifest_path, root / "results")
            candidate = next(item for item in result.outcomes if item.variant == "candidate")
            self.assertTrue(candidate.passed)
            self.assertEqual(1, candidate.usage.calls)
            completion = candidate.metadata["deterministic_completion"]
            self.assertTrue(completion["completed"])
            self.assertEqual(1, completion["added_path_count"])
            self.assertEqual(2, completion["certificate_count"])
            self.assertEqual(2, completion["matched_fact_count"])

    def test_clean_retry_does_not_receive_targeted_failure_packet(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            fixture = root / "fixture"
            fixture.mkdir()
            driver = root / "clean_retry_driver.py"
            driver.write_text(
                """
import json
import os
from pathlib import Path

workspace = Path(os.environ["AGP_WORKSPACE"])
variant = os.environ["AGP_VARIANT"]
repair = variant.endswith("-repair")
clean = repair and "AGP_REPAIR_PACKET_FILE" not in os.environ
correct = variant == "baseline" or clean
(workspace / "result.txt").write_text("correct\\n" if correct else "incomplete\\n")
usage_file = ".repair-usage.json" if repair else ".usage.json"
(workspace / usage_file).write_text(json.dumps({
    "input_tokens": 20 if repair else (100 if variant == "baseline" else 60),
    "output_tokens": 0,
    "calls": 1,
    "call_count_source": "agent-run",
    "source": "reported"
}), encoding="utf-8")
print("done")
""".strip()
                + "\n",
                encoding="utf-8",
            )
            manifest = {
                "schema_version": 1,
                "name": "clean-retry-unit",
                "random_seed": 7,
                "variants": {
                    "baseline": {
                        "route_name": "baseline",
                        "command": [sys.executable, str(driver)],
                        "usage_file": ".usage.json",
                    },
                    "candidate": {
                        "route_name": "candidate",
                        "command": [sys.executable, str(driver)],
                        "usage_file": ".usage.json",
                        "repair": {
                            "mode": "clean-retry",
                            "route_name": "strong-clean-retry",
                            "command": [sys.executable, str(driver)],
                            "usage_file": ".repair-usage.json",
                            "on_evaluator_types": ["file_contains"],
                        },
                    },
                },
                "tasks": [
                    {
                        "id": "task",
                        "family": "code",
                        "fixture": "fixture",
                        "instruction": "Produce the required result.",
                        "seeds": [1],
                        "evaluators": [
                            {
                                "type": "exit_code",
                                "name": "execution",
                                "critical": True,
                            },
                            {
                                "type": "file_contains",
                                "name": "complete",
                                "path": "result.txt",
                                "value": "correct",
                                "critical": True,
                            },
                        ],
                    }
                ],
            }
            manifest_path = root / "manifest.json"
            manifest_path.write_text(json.dumps(manifest), encoding="utf-8")

            result = run_benchmark(manifest_path, root / "results")
            candidate = next(item for item in result.outcomes if item.variant == "candidate")
            self.assertTrue(candidate.passed)
            escalation = candidate.metadata["selective_escalation"]
            self.assertEqual("clean-retry", escalation["mode"])
            self.assertTrue(escalation["repaired"])

    def test_selective_repair_does_not_run_for_unallowed_failure_type(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            manifest_path = self._fixture(root)
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
            manifest["variants"]["candidate"]["repair"] = {
                "route_name": "repair",
                "command": manifest["variants"]["candidate"]["command"],
                "usage_file": ".usage.json",
                "on_evaluator_types": ["answer_contract"],
            }
            manifest["tasks"][0]["evaluators"][1]["value"] = "not-present"
            manifest_path.write_text(json.dumps(manifest), encoding="utf-8")

            result = run_benchmark(manifest_path, root / "results")
            candidate = next(item for item in result.outcomes if item.variant == "candidate")
            self.assertFalse(candidate.passed)
            self.assertFalse(candidate.metadata["selective_escalation"]["applied"])
            self.assertEqual(1, candidate.usage.calls)

    def test_benchmark_resumes_from_atomic_checkpoint(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            manifest = self._fixture(root)
            result = run_benchmark(manifest, root / "results")
            benchmark_dir = root / "results" / result.benchmark_id
            checkpoint_path = benchmark_dir / "checkpoint.json"
            checkpoint = json.loads(checkpoint_path.read_text(encoding="utf-8"))
            checkpoint["status"] = "running"
            checkpoint["completed_at"] = None
            checkpoint["outcomes"].pop()
            checkpoint_path.write_text(json.dumps(checkpoint), encoding="utf-8")

            resumed = run_benchmark(
                manifest,
                root / "unused",
                resume_from=benchmark_dir,
            )
            self.assertEqual(result.benchmark_id, resumed.benchmark_id)
            self.assertEqual(2, len(resumed.outcomes))
            completed = json.loads(checkpoint_path.read_text(encoding="utf-8"))
            self.assertEqual("complete", completed["status"])

    def test_manifest_rejects_missing_evaluators(self) -> None:
        with self.assertRaises(ManifestError):
            validate_manifest(
                {
                    "schema_version": 1,
                    "name": "bad",
                    "variants": {
                        "baseline": {"route_name": "a", "command": ["x"]},
                        "candidate": {"route_name": "b", "command": ["x"]},
                    },
                    "tasks": [{"id": "task", "family": "code", "fixture": "."}],
                }
            )

    def test_manifest_rejects_unknown_repair_and_completion_modes(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            manifest_path = self._fixture(root)
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
            manifest["variants"]["candidate"]["repair"] = {
                "mode": "retry-forever",
                "route_name": "repair",
                "command": ["x"],
                "on_evaluator_types": ["answer_contract"],
            }
            with self.assertRaisesRegex(ManifestError, "repair mode"):
                validate_manifest(manifest)
            del manifest["variants"]["candidate"]["repair"]
            manifest["variants"]["candidate"]["deterministic_completion"] = {
                "kind": "oracle-answer",
            }
            with self.assertRaisesRegex(ManifestError, "deterministic_completion kind"):
                validate_manifest(manifest)

    def test_bundle_hash_changes_with_fixture_content(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            manifest = self._fixture(root)
            first = benchmark_bundle_hash(manifest)
            (root / "fixture" / "input.txt").write_text(
                "changed\n",
                encoding="utf-8",
            )
            second = benchmark_bundle_hash(manifest)
            self.assertNotEqual(first, second)

    def test_bundle_hash_covers_repair_command_asset(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            manifest_path = self._fixture(root)
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
            repair_driver = root / "repair.py"
            repair_driver.write_text("print('repair one')\n", encoding="utf-8")
            manifest["variants"]["candidate"]["repair"] = {
                "route_name": "repair",
                "command": [sys.executable, str(repair_driver)],
                "on_evaluator_types": ["file_contains"],
            }
            manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
            first = benchmark_bundle_hash(manifest_path)
            repair_driver.write_text("print('repair two')\n", encoding="utf-8")
            second = benchmark_bundle_hash(manifest_path)
            self.assertNotEqual(first, second)

    def test_runtime_lock_pins_binary_version_and_checksum(self) -> None:
        binary = Path(sys.executable).resolve()
        version = subprocess.run(
            [str(binary), "--version"],
            check=True,
            capture_output=True,
            text=True,
        )
        manifest = {
            "runtime_lock": {
                "codex_binary": str(binary),
                "codex_version": (version.stdout or version.stderr).strip(),
                "codex_sha256": hashlib.sha256(binary.read_bytes()).hexdigest(),
            },
            "variants": {
                "baseline": {"env": {"CODEX_BINARY": str(binary)}},
                "candidate": {"env": {"CODEX_BINARY": str(binary)}},
            },
        }
        actual = validate_runtime_lock(manifest)
        self.assertEqual(manifest["runtime_lock"]["codex_version"], actual["codex_version"])
        self.assertEqual(
            manifest["runtime_lock"]["codex_sha256"],
            actual["codex_binary_sha256"],
        )

    def test_runtime_lock_rejects_checksum_drift(self) -> None:
        binary = Path(sys.executable).resolve()
        manifest = {
            "runtime_lock": {
                "codex_binary": str(binary),
                "codex_version": "unused",
                "codex_sha256": "0" * 64,
            },
            "variants": {
                "baseline": {"env": {"CODEX_BINARY": str(binary)}},
                "candidate": {"env": {"CODEX_BINARY": str(binary)}},
            },
        }
        with self.assertRaisesRegex(ManifestError, "checksum does not match"):
            validate_runtime_lock(manifest)

    def test_evidence_paths_accept_line_citations(self) -> None:
        self.assertEqual("src/file.py", normalize_evidence_path("src/file.py:12"))
        self.assertEqual("src/file.py", normalize_evidence_path("./src/file.py#L12-L15"))


if __name__ == "__main__":
    unittest.main()
