from __future__ import annotations

import json
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from agent_goodput.codex_runner import (
    CodexRunner,
    count_rollout_response_cycles,
    parse_codex_events,
)
from agent_goodput.policy import BOUNDED_READ_ROUTE


class CodexEventTests(unittest.TestCase):
    def test_parses_last_cumulative_usage(self) -> None:
        events = "\n".join(
            [
                json.dumps({"type": "thread.started"}),
                json.dumps(
                    {
                        "type": "turn.completed",
                        "usage": {
                            "input_tokens": 100,
                            "cached_input_tokens": 80,
                            "output_tokens": 20,
                        },
                    }
                ),
            ]
        )
        usage, count, types, item_types, item_events = parse_codex_events(events)
        self.assertEqual(2, count)
        self.assertEqual(100, usage.input_tokens)
        self.assertEqual(80, usage.cached_input_tokens)
        self.assertEqual(20, usage.output_tokens)
        self.assertEqual("codex", usage.source)
        self.assertEqual("agent-run", usage.call_count_source)
        self.assertIsNone(usage.response_cycles)
        self.assertEqual(1, types["turn.completed"])
        self.assertEqual({}, item_types)
        self.assertEqual({}, item_events)

    def test_missing_usage_is_not_mislabeled_reported(self) -> None:
        usage, _, _, _, _ = parse_codex_events("{}\n")
        self.assertEqual("missing", usage.source)
        self.assertEqual(0, usage.raw_total_tokens)

    def test_separates_started_and_completed_item_counts(self) -> None:
        events = "\n".join(
            [
                json.dumps(
                    {
                        "type": "item.started",
                        "item": {"type": "command_execution"},
                    }
                ),
                json.dumps(
                    {
                        "type": "item.completed",
                        "item": {"type": "command_execution"},
                    }
                ),
                json.dumps(
                    {
                        "type": "item.completed",
                        "item": {"type": "agent_message"},
                    }
                ),
            ]
        )
        _, _, _, item_types, item_events = parse_codex_events(events)
        self.assertEqual(2, item_types["command_execution"])
        self.assertEqual(
            {"agent_message": 1, "command_execution": 1},
            item_events["item.completed"],
        )

    def test_counts_response_cycles_without_retaining_rollout_content(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            sessions = Path(directory) / "sessions" / "2026" / "07" / "27"
            sessions.mkdir(parents=True)
            rollout = sessions / "rollout.jsonl"
            records = [
                {"type": "session_meta", "payload": {"id": "private"}},
                {
                    "type": "event_msg",
                    "payload": {"type": "token_count", "info": {"total": 1}},
                },
                {
                    "type": "event_msg",
                    "payload": {"type": "token_count", "info": {"total": 2}},
                },
                {
                    "type": "event_msg",
                    "payload": {"type": "token_count", "info": None},
                },
            ]
            rollout.write_text(
                "\n".join(json.dumps(item) for item in records) + "\n",
                encoding="utf-8",
            )
            self.assertEqual(2, count_rollout_response_cycles(Path(directory)))

    def test_response_cycle_scan_fails_closed_on_oversized_rollout(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            sessions = Path(directory) / "sessions"
            sessions.mkdir()
            (sessions / "rollout.jsonl").write_text("x" * 20, encoding="utf-8")
            with patch("agent_goodput.codex_runner._MAX_ROLLOUT_SCAN_BYTES", 10):
                self.assertIsNone(count_rollout_response_cycles(Path(directory)))

    def test_isolated_runner_counts_cycles_then_deletes_rollout(self) -> None:
        seen: dict[str, object] = {}

        def fake_run(
            command: list[str],
            *,
            input: str,
            text: bool,
            capture_output: bool,
            timeout: int,
            env: dict[str, str],
            check: bool,
        ) -> subprocess.CompletedProcess[str]:
            del input, text, capture_output, timeout, check
            codex_home = Path(env["CODEX_HOME"])
            seen["codex_home"] = codex_home
            seen["command"] = command
            sessions = codex_home / "sessions" / "2026" / "07" / "27"
            sessions.mkdir(parents=True)
            records = [
                {
                    "type": "event_msg",
                    "payload": {"type": "token_count", "info": {"total": 1}},
                },
                {
                    "type": "event_msg",
                    "payload": {"type": "token_count", "info": {"total": 2}},
                },
            ]
            (sessions / "rollout.jsonl").write_text(
                "\n".join(json.dumps(item) for item in records) + "\n",
                encoding="utf-8",
            )
            answer_path = Path(command[command.index("--output-last-message") + 1])
            answer_path.write_text("agent-goodput", encoding="utf-8")
            stdout = json.dumps(
                {
                    "type": "turn.completed",
                    "usage": {
                        "input_tokens": 100,
                        "cached_input_tokens": 80,
                        "output_tokens": 10,
                    },
                }
            )
            return subprocess.CompletedProcess(command, 0, stdout=stdout, stderr="")

        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            runner = object.__new__(CodexRunner)
            runner.codex = Path("/usr/bin/false")
            runner.runtime_version = "codex-cli test"
            runner.auth_home = root / "auth"
            (runner.auth_home).mkdir()
            with patch("agent_goodput.codex_runner.subprocess.run", side_effect=fake_run):
                execution = runner.run(
                    "Inspect one file.",
                    cwd=root,
                    route=BOUNDED_READ_ROUTE,
                )

        command = seen["command"]
        self.assertIsInstance(command, list)
        self.assertNotIn("--ephemeral", command)
        self.assertEqual(2, execution.usage.response_cycles)
        self.assertEqual("codex:token-count-events", execution.usage.response_cycle_source)
        self.assertEqual("agent-goodput", execution.answer)
        codex_home = seen["codex_home"]
        self.assertIsInstance(codex_home, Path)
        self.assertFalse(codex_home.exists())

    def test_direct_cycle_signal_is_preserved(self) -> None:
        events = json.dumps(
            {
                "type": "turn.completed",
                "usage": {
                    "input_tokens": 100,
                    "output_tokens": 10,
                    "model_calls": 3,
                },
            }
        )
        usage, _, _, _, _ = parse_codex_events(events)
        self.assertEqual(3, usage.response_cycles)
        self.assertEqual("codex:model_calls", usage.response_cycle_source)

    def test_runner_fails_closed_when_cycle_signals_conflict(self) -> None:
        def fake_run(
            command: list[str],
            **_: object,
        ) -> subprocess.CompletedProcess[str]:
            answer_path = Path(command[command.index("--output-last-message") + 1])
            answer_path.write_text("answer", encoding="utf-8")
            stdout = json.dumps(
                {
                    "type": "turn.completed",
                    "usage": {
                        "input_tokens": 100,
                        "output_tokens": 10,
                        "model_calls": 3,
                    },
                }
            )
            return subprocess.CompletedProcess(command, 0, stdout=stdout, stderr="")

        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            runner = object.__new__(CodexRunner)
            runner.codex = Path("/usr/bin/false")
            runner.runtime_version = "codex-cli test"
            runner.auth_home = root / "auth"
            runner.auth_home.mkdir()
            with (
                patch("agent_goodput.codex_runner.subprocess.run", side_effect=fake_run),
                patch(
                    "agent_goodput.codex_runner.count_rollout_response_cycles",
                    return_value=2,
                ),
            ):
                execution = runner.run(
                    "Inspect one file.",
                    cwd=root,
                    route=BOUNDED_READ_ROUTE,
                )

        self.assertIsNone(execution.usage.response_cycles)
        self.assertEqual(
            "conflicting-codex-signals",
            execution.usage.response_cycle_source,
        )


if __name__ == "__main__":
    unittest.main()
