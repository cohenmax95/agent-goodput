from __future__ import annotations

from dataclasses import replace
from pathlib import Path
from typing import Any

from .evidence import EvidenceStore
from .policy import BucketPolicy, PolicySnapshot
from .stats import PromotionThresholds, evaluate_promotion
from .util import (
    file_lock,
    load_or_create_secret,
    read_json,
    sign_value,
    utc_now,
    verify_signature,
    write_json,
)


class PolicyIntegrityError(RuntimeError):
    pass


class PolicyController:
    def __init__(
        self,
        state_root: str | Path,
        *,
        thresholds: PromotionThresholds | None = None,
    ) -> None:
        self.root = Path(state_root).expanduser().resolve()
        self.root.mkdir(parents=True, exist_ok=True)
        self.policy_path = self.root / "policy.json"
        self.history_dir = self.root / "policy-history"
        self.cycle_path = self.root / "controller-cycle.json"
        self.cycle_lock_path = self.root / "controller-cycle.lock"
        self.secret = load_or_create_secret(self.root)
        self.evidence = EvidenceStore(self.root / "evidence.sqlite3")
        self.thresholds = thresholds or PromotionThresholds()
        if not self.policy_path.exists():
            self._write(PolicySnapshot.default())

    def _envelope(self, snapshot: PolicySnapshot) -> dict[str, Any]:
        payload = snapshot.to_dict()
        return {
            "payload": payload,
            "signature": sign_value(payload, self.secret),
        }

    def _write(self, snapshot: PolicySnapshot) -> None:
        envelope = self._envelope(snapshot)
        if self.policy_path.exists():
            existing = self.load()
            self.history_dir.mkdir(parents=True, exist_ok=True)
            write_json(
                self.history_dir / f"{existing.version:06d}-{existing.digest[:12]}.json",
                self._envelope(existing),
            )
        write_json(self.policy_path, envelope)

    def load(self) -> PolicySnapshot:
        envelope = read_json(self.policy_path)
        if (
            not isinstance(envelope, dict)
            or "payload" not in envelope
            or "signature" not in envelope
        ):
            raise PolicyIntegrityError("policy envelope is malformed")
        payload = envelope["payload"]
        if not verify_signature(payload, str(envelope["signature"]), self.secret):
            raise PolicyIntegrityError("policy signature does not match")
        return PolicySnapshot.from_dict(payload)

    def evaluate(self, bucket: str) -> dict[str, Any]:
        snapshot = self.load()
        current = snapshot.buckets.get(bucket)
        if current is None:
            raise KeyError(f"bucket has no registered candidate: {bucket}")
        phase = "shadow" if current.status == "rolled_back" else current.status
        outcomes = self.evidence.outcomes(bucket=bucket, after_cursor=current.evidence_cursor)
        report = evaluate_promotion(
            outcomes,
            thresholds=self.thresholds,
            current_phase=phase,
        )
        return {
            "bucket": bucket,
            "phase": current.status,
            "evidence_cursor": current.evidence_cursor,
            "current_evidence_cursor": self.evidence.cursor,
            "report": report.to_dict(),
        }

    def register_shadow(self, bucket: str, route_name: str) -> PolicySnapshot:
        snapshot = self.load()
        if route_name not in snapshot.routes:
            raise KeyError(f"unknown route: {route_name}")
        existing = snapshot.buckets.get(bucket)
        if existing and existing.route_name == route_name and existing.status != "rolled_back":
            return snapshot
        buckets = dict(snapshot.buckets)
        buckets[bucket] = BucketPolicy(
            route_name=route_name,
            status="shadow",
            canary_fraction=0.0,
            evidence_cursor=self.evidence.cursor,
        )
        updated = replace(
            snapshot,
            version=snapshot.version + 1,
            buckets=buckets,
            parent_digest=snapshot.digest,
            created_at=utc_now(),
        )
        self._write(updated)
        self.evidence.append_event(
            "policy_shadow_registered",
            {
                "bucket": bucket,
                "route_name": route_name,
                "policy_version": updated.version,
                "policy_digest": updated.digest,
            },
        )
        return updated

    def apply_evaluation(self, bucket: str) -> PolicySnapshot:
        snapshot = self.load()
        current = snapshot.buckets.get(bucket)
        if current is None:
            raise KeyError(f"bucket has no registered candidate: {bucket}")
        evaluation = self.evaluate(bucket)
        report = evaluation["report"]
        disposition = report["disposition"]
        if disposition == "hold":
            return snapshot
        status = current.status
        canary_fraction = current.canary_fraction
        if disposition == "rollback":
            status = "rolled_back"
            canary_fraction = 0.0
        elif disposition == "canary":
            status = "canary"
            canary_fraction = 0.10
        elif disposition == "promote":
            status = "active"
            canary_fraction = 1.0

        buckets = dict(snapshot.buckets)
        buckets[bucket] = replace(
            current,
            status=status,
            canary_fraction=canary_fraction,
            evidence_hash=self.evidence.head_hash,
            evidence_cursor=self.evidence.cursor,
        )
        updated = replace(
            snapshot,
            version=snapshot.version + 1,
            buckets=buckets,
            parent_digest=snapshot.digest,
            created_at=utc_now(),
        )
        self._write(updated)
        self.evidence.append_event(
            "policy_transition",
            {
                "bucket": bucket,
                "from_status": current.status,
                "to_status": status,
                "route_name": current.route_name,
                "policy_version": updated.version,
                "policy_digest": updated.digest,
                "evaluation": report,
            },
        )
        return updated

    def emergency_rollback(self, bucket: str, reason_code: str) -> PolicySnapshot:
        if not reason_code or len(reason_code) > 120:
            raise ValueError("reason_code must be 1-120 characters")
        snapshot = self.load()
        current = snapshot.buckets.get(bucket)
        if current is None:
            raise KeyError(f"bucket has no registered candidate: {bucket}")
        buckets = dict(snapshot.buckets)
        buckets[bucket] = replace(
            current,
            status="rolled_back",
            canary_fraction=0.0,
            evidence_cursor=self.evidence.cursor,
        )
        updated = replace(
            snapshot,
            version=snapshot.version + 1,
            buckets=buckets,
            parent_digest=snapshot.digest,
            created_at=utc_now(),
        )
        self._write(updated)
        self.evidence.append_event(
            "emergency_rollback",
            {
                "bucket": bucket,
                "route_name": current.route_name,
                "reason_code": reason_code,
                "policy_version": updated.version,
                "policy_digest": updated.digest,
            },
        )
        return updated

    def _run_cycle_unlocked(self) -> dict[str, Any]:
        before = self.load()
        transitions: list[dict[str, Any]] = []
        held: list[dict[str, Any]] = []
        for bucket in sorted(before.buckets):
            evaluation = self.evaluate(bucket)
            disposition = evaluation["report"]["disposition"]
            if disposition == "hold":
                held.append(evaluation)
                continue
            prior_status = self.load().buckets[bucket].status
            updated = self.apply_evaluation(bucket)
            transitions.append(
                {
                    "bucket": bucket,
                    "from_status": prior_status,
                    "to_status": updated.buckets[bucket].status,
                    "policy_version": updated.version,
                }
            )
        after = self.load()
        return {
            "started_policy_version": before.version,
            "completed_policy_version": after.version,
            "transitions": transitions,
            "held": held,
            "evidence_cursor": self.evidence.cursor,
        }

    def _last_cycle_outcome_cursor(self) -> int:
        envelope = read_json(self.cycle_path)
        if not isinstance(envelope, dict):
            return 0
        payload = envelope.get("payload")
        signature = envelope.get("signature")
        if not isinstance(payload, dict) or not isinstance(signature, str):
            return 0
        if not verify_signature(payload, signature, self.secret):
            return 0
        cursor = payload.get("outcome_cursor")
        if isinstance(cursor, bool) or not isinstance(cursor, int) or cursor < 0:
            return 0
        return cursor

    def _record_cycle(
        self,
        result: dict[str, Any],
        *,
        outcome_cursor: int,
        trigger: str,
    ) -> dict[str, Any]:
        sequence, _ = self.evidence.append_event(
            "controller_cycle_completed",
            {
                "trigger": trigger,
                "outcome_cursor": outcome_cursor,
                "started_policy_version": result["started_policy_version"],
                "completed_policy_version": result["completed_policy_version"],
                "transition_count": len(result["transitions"]),
                "held_count": len(result["held"]),
            },
        )
        payload = {
            "outcome_cursor": outcome_cursor,
            "completed_policy_version": result["completed_policy_version"],
            "completion_event_seq": sequence,
            "completed_at": utc_now(),
        }
        write_json(
            self.cycle_path,
            {
                "payload": payload,
                "signature": sign_value(payload, self.secret),
            },
        )
        return {
            **result,
            "skipped": False,
            "trigger": trigger,
            "evidence_cursor": self.evidence.cursor,
        }

    def run_cycle(self, *, trigger: str = "manual") -> dict[str, Any]:
        """Evaluate every registered bucket and apply only gated transitions."""

        with file_lock(self.cycle_lock_path):
            outcome_cursor = self.evidence.outcome_cursor
            result = self._run_cycle_unlocked()
            return self._record_cycle(
                result,
                outcome_cursor=outcome_cursor,
                trigger=trigger,
            )

    def run_cycle_if_needed(self, *, trigger: str) -> dict[str, Any]:
        """Run once for each new set of verified outcomes.

        Turn and session hooks may both fire for the same work. The signed
        outcome cursor makes the second call a cheap no-op and prevents a
        modified marker from silently suppressing evaluation.
        """

        with file_lock(self.cycle_lock_path):
            outcome_cursor = self.evidence.outcome_cursor
            last_outcome_cursor = self._last_cycle_outcome_cursor()
            if outcome_cursor == last_outcome_cursor:
                return {
                    "skipped": True,
                    "trigger": trigger,
                    "reason": "no-new-outcomes",
                    "outcome_cursor": outcome_cursor,
                    "evidence_cursor": self.evidence.cursor,
                }
            result = self._run_cycle_unlocked()
            return self._record_cycle(
                result,
                outcome_cursor=outcome_cursor,
                trigger=trigger,
            )
