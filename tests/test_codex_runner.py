from __future__ import annotations

import json
import unittest

from agent_goodput.codex_runner import parse_codex_events


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


if __name__ == "__main__":
    unittest.main()
