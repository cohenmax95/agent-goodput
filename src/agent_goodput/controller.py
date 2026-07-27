from __future__ import annotations

from dataclasses import replace
from pathlib import Path
from typing import Any

from .evidence import EvidenceStore
from .policy import BucketPolicy, PolicySnapshot
from .stats import PromotionThresholds, evaluate_promotion
from .util import (
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

    def run_cycle(self) -> dict[str, Any]:
        """Evaluate every registered bucket and apply only gated transitions."""

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
