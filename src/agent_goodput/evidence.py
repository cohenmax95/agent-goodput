from __future__ import annotations

import json
import os
import sqlite3
from collections.abc import Generator, Iterable, Iterator
from contextlib import contextmanager
from pathlib import Path
from typing import Any

from .models import RunOutcome
from .util import canonical_json, sha256_text, utc_now

_FORBIDDEN_KEYS = {
    "assistant_output",
    "credential",
    "password",
    "prompt",
    "raw_output",
    "secret",
    "tool_input",
    "tool_output",
    "transcript",
}


def _assert_privacy_safe(value: Any, path: str = "payload") -> None:
    if isinstance(value, dict):
        for key, child in value.items():
            normalized = str(key).strip().casefold()
            if normalized in _FORBIDDEN_KEYS:
                raise ValueError(f"privacy-unsafe key at {path}.{key}")
            _assert_privacy_safe(child, f"{path}.{key}")
    elif isinstance(value, (list, tuple)):
        for index, child in enumerate(value):
            _assert_privacy_safe(child, f"{path}[{index}]")


class EvidenceStore:
    """Local, append-only, hash-chained evidence.

    The store rejects common raw-content fields. It is designed for task
    fingerprints, counters, route decisions, and deterministic evaluator
    results rather than prompts or model output.
    """

    def __init__(self, path: str | Path) -> None:
        self.path = Path(path).expanduser().resolve()
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._initialize()
        os.chmod(self.path, 0o600)

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.path, timeout=10)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys = ON")
        connection.execute("PRAGMA journal_mode = WAL")
        connection.execute("PRAGMA synchronous = FULL")
        return connection

    @contextmanager
    def _connection(self) -> Generator[sqlite3.Connection, None, None]:
        connection = self._connect()
        try:
            with connection:
                yield connection
        finally:
            connection.close()

    def _initialize(self) -> None:
        with self._connection() as connection:
            connection.executescript(
                """
                CREATE TABLE IF NOT EXISTS events (
                    seq INTEGER PRIMARY KEY AUTOINCREMENT,
                    created_at TEXT NOT NULL,
                    event_type TEXT NOT NULL,
                    payload_json TEXT NOT NULL,
                    payload_hash TEXT NOT NULL,
                    previous_hash TEXT NOT NULL,
                    event_hash TEXT NOT NULL UNIQUE
                );

                CREATE TABLE IF NOT EXISTS outcomes (
                    run_id TEXT PRIMARY KEY,
                    task_id TEXT NOT NULL,
                    project_id TEXT NOT NULL,
                    task_family TEXT NOT NULL,
                    route_name TEXT NOT NULL,
                    variant TEXT NOT NULL,
                    seed INTEGER,
                    bucket TEXT,
                    passed INTEGER NOT NULL,
                    critical_failure INTEGER NOT NULL,
                    quality_score REAL NOT NULL,
                    raw_tokens INTEGER NOT NULL,
                    elapsed_ms INTEGER NOT NULL,
                    event_seq INTEGER NOT NULL,
                    payload_json TEXT NOT NULL,
                    FOREIGN KEY(event_seq) REFERENCES events(seq)
                );

                CREATE INDEX IF NOT EXISTS outcomes_pair_idx
                    ON outcomes(task_id, project_id, seed, variant);
                CREATE INDEX IF NOT EXISTS outcomes_bucket_idx
                    ON outcomes(bucket, event_seq);
                """
            )

    @property
    def cursor(self) -> int:
        with self._connection() as connection:
            row = connection.execute("SELECT COALESCE(MAX(seq), 0) AS seq FROM events").fetchone()
            return int(row["seq"])

    @property
    def outcome_cursor(self) -> int:
        with self._connection() as connection:
            row = connection.execute(
                "SELECT COALESCE(MAX(event_seq), 0) AS seq FROM outcomes"
            ).fetchone()
            return int(row["seq"])

    @property
    def head_hash(self) -> str:
        with self._connection() as connection:
            row = connection.execute(
                "SELECT event_hash FROM events ORDER BY seq DESC LIMIT 1"
            ).fetchone()
            return str(row["event_hash"]) if row else "0" * 64

    def _append_event(
        self,
        connection: sqlite3.Connection,
        event_type: str,
        payload: dict[str, Any],
    ) -> tuple[int, str]:
        _assert_privacy_safe(payload)
        payload_json = canonical_json(payload)
        payload_hash = sha256_text(payload_json)
        created_at = utc_now()
        prior = connection.execute(
            "SELECT event_hash FROM events ORDER BY seq DESC LIMIT 1"
        ).fetchone()
        previous_hash = str(prior["event_hash"]) if prior else "0" * 64
        event_hash = sha256_text(
            canonical_json(
                {
                    "created_at": created_at,
                    "event_type": event_type,
                    "payload_hash": payload_hash,
                    "previous_hash": previous_hash,
                }
            )
        )
        cursor = connection.execute(
            """
            INSERT INTO events(
                created_at, event_type, payload_json, payload_hash,
                previous_hash, event_hash
            ) VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                created_at,
                event_type,
                payload_json,
                payload_hash,
                previous_hash,
                event_hash,
            ),
        )
        if cursor.lastrowid is None:
            raise RuntimeError("event insert did not return a sequence")
        return cursor.lastrowid, event_hash

    def append_event(self, event_type: str, payload: dict[str, Any]) -> tuple[int, str]:
        with self._connection() as connection:
            connection.execute("BEGIN IMMEDIATE")
            return self._append_event(connection, event_type, payload)

    def append_outcome(self, outcome: RunOutcome) -> tuple[int, str]:
        payload = outcome.to_dict()
        bucket = outcome.metadata.get("bucket")
        with self._connection() as connection:
            connection.execute("BEGIN IMMEDIATE")
            sequence, event_hash = self._append_event(
                connection,
                "run_outcome",
                payload,
            )
            connection.execute(
                """
                INSERT INTO outcomes(
                    run_id, task_id, project_id, task_family, route_name,
                    variant, seed, bucket, passed, critical_failure,
                    quality_score, raw_tokens, elapsed_ms, event_seq, payload_json
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    outcome.run_id,
                    outcome.task_id,
                    outcome.project_id,
                    outcome.task_family,
                    outcome.route_name,
                    outcome.variant,
                    outcome.seed,
                    bucket,
                    int(outcome.passed),
                    int(outcome.critical_failure),
                    outcome.quality_score,
                    outcome.usage.raw_total_tokens,
                    outcome.elapsed_ms,
                    sequence,
                    canonical_json(payload),
                ),
            )
        return sequence, event_hash

    def outcomes(
        self,
        *,
        bucket: str | None = None,
        after_cursor: int = 0,
        variant: str | None = None,
    ) -> list[RunOutcome]:
        parameters: list[Any]
        if bucket is not None and variant is not None:
            statement = (
                "SELECT payload_json FROM outcomes "
                "WHERE event_seq > ? AND bucket = ? AND variant = ? ORDER BY event_seq"
            )
            parameters = [after_cursor, bucket, variant]
        elif bucket is not None:
            statement = (
                "SELECT payload_json FROM outcomes "
                "WHERE event_seq > ? AND bucket = ? ORDER BY event_seq"
            )
            parameters = [after_cursor, bucket]
        elif variant is not None:
            statement = (
                "SELECT payload_json FROM outcomes "
                "WHERE event_seq > ? AND variant = ? ORDER BY event_seq"
            )
            parameters = [after_cursor, variant]
        else:
            statement = "SELECT payload_json FROM outcomes WHERE event_seq > ? ORDER BY event_seq"
            parameters = [after_cursor]
        with self._connection() as connection:
            rows = connection.execute(statement, parameters).fetchall()
        return [RunOutcome.from_dict(json.loads(row["payload_json"])) for row in rows]

    def events(self) -> Iterator[dict[str, Any]]:
        with self._connection() as connection:
            rows = connection.execute("SELECT * FROM events ORDER BY seq").fetchall()
        for row in rows:
            yield dict(row)

    def verify_chain(self) -> tuple[bool, str]:
        previous = "0" * 64
        expected_sequence = 1
        for event in self.events():
            if int(event["seq"]) != expected_sequence:
                return False, f"missing or reordered event at sequence {expected_sequence}"
            if event["previous_hash"] != previous:
                return False, f"previous hash mismatch at sequence {expected_sequence}"
            if sha256_text(event["payload_json"]) != event["payload_hash"]:
                return False, f"payload hash mismatch at sequence {expected_sequence}"
            expected_hash = sha256_text(
                canonical_json(
                    {
                        "created_at": event["created_at"],
                        "event_type": event["event_type"],
                        "payload_hash": event["payload_hash"],
                        "previous_hash": event["previous_hash"],
                    }
                )
            )
            if expected_hash != event["event_hash"]:
                return False, f"event hash mismatch at sequence {expected_sequence}"
            previous = expected_hash
            expected_sequence += 1
        return True, f"verified {expected_sequence - 1} events"

    def append_many(self, outcomes: Iterable[RunOutcome]) -> None:
        for outcome in outcomes:
            self.append_outcome(outcome)
