from __future__ import annotations

import hashlib
from dataclasses import dataclass
from typing import Any, Literal

from .models import Decision, RiskLevel, Route, TaskFeatures
from .util import canonical_json

BASELINE_ROUTE = Route(
    name="sol-high",
    model="gpt-5.6-sol",
    reasoning_effort="high",
    max_subagents=0,
    context_budget_tokens=96_000,
    tool_call_budget=80,
    requires_verification=True,
    allowed_risk=RiskLevel.CRITICAL,
)

BOUNDED_READ_ROUTE = Route(
    name="terra-medium-bounded-read",
    model="gpt-5.6-terra",
    reasoning_effort="medium",
    max_subagents=0,
    context_budget_tokens=48_000,
    tool_call_budget=30,
    requires_verification=True,
    allowed_risk=RiskLevel.LOW,
)

ROUTINE_ROUTE = Route(
    name="sol-medium",
    model="gpt-5.6-sol",
    reasoning_effort="medium",
    max_subagents=0,
    context_budget_tokens=64_000,
    tool_call_budget=50,
    requires_verification=True,
    allowed_risk=RiskLevel.MEDIUM,
)


@dataclass(frozen=True)
class BucketPolicy:
    route_name: str
    status: Literal["shadow", "canary", "active", "rolled_back"] = "shadow"
    canary_fraction: float = 0.0
    evidence_hash: str | None = None
    evidence_cursor: int = 0

    @classmethod
    def from_dict(cls, value: dict[str, Any]) -> BucketPolicy:
        return cls(**value)

    def to_dict(self) -> dict[str, Any]:
        return {
            "route_name": self.route_name,
            "status": self.status,
            "canary_fraction": self.canary_fraction,
            "evidence_hash": self.evidence_hash,
            "evidence_cursor": self.evidence_cursor,
        }


@dataclass(frozen=True)
class PolicySnapshot:
    version: int
    baseline: Route
    routes: dict[str, Route]
    buckets: dict[str, BucketPolicy]
    minimum_verification_strength: float = 0.5
    max_subagents: int = 2
    parent_digest: str | None = None
    created_at: str | None = None

    @classmethod
    def default(cls) -> PolicySnapshot:
        routes = {
            route.name: route
            for route in (
                BASELINE_ROUTE,
                BOUNDED_READ_ROUTE,
                ROUTINE_ROUTE,
            )
        }
        return cls(version=1, baseline=BASELINE_ROUTE, routes=routes, buckets={})

    @classmethod
    def from_dict(cls, value: dict[str, Any]) -> PolicySnapshot:
        routes = {name: Route.from_dict(raw) for name, raw in value["routes"].items()}
        baseline_name = value.get("baseline_route", "sol-high")
        return cls(
            version=int(value["version"]),
            baseline=routes[baseline_name],
            routes=routes,
            buckets={
                name: BucketPolicy.from_dict(raw) for name, raw in value.get("buckets", {}).items()
            },
            minimum_verification_strength=float(value.get("minimum_verification_strength", 0.5)),
            max_subagents=int(value.get("max_subagents", 2)),
            parent_digest=value.get("parent_digest"),
            created_at=value.get("created_at"),
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "version": self.version,
            "baseline_route": self.baseline.name,
            "routes": {name: route.to_dict() for name, route in self.routes.items()},
            "buckets": {name: policy.to_dict() for name, policy in self.buckets.items()},
            "minimum_verification_strength": self.minimum_verification_strength,
            "max_subagents": self.max_subagents,
            "parent_digest": self.parent_digest,
            "created_at": self.created_at,
        }

    @property
    def digest(self) -> str:
        return hashlib.sha256(canonical_json(self.to_dict()).encode()).hexdigest()


def proposed_route(features: TaskFeatures) -> Route | None:
    if features.explicit_quality_request or features.risk >= RiskLevel.HIGH:
        return None
    if (
        features.write_scope == "none"
        and features.risk == RiskLevel.LOW
        and features.task_kind in {"research", "general", "diagnosis"}
        and features.complexity < 0.72
    ):
        return BOUNDED_READ_ROUTE
    if (
        features.write_scope == "local"
        and features.risk <= RiskLevel.MEDIUM
        and features.complexity < 0.48
        and features.ambiguity < 0.45
    ):
        return ROUTINE_ROUTE
    return None


def _canary_selected(fingerprint: str, fraction: float) -> bool:
    if fraction <= 0:
        return False
    if fraction >= 1:
        return True
    slot = int(hashlib.sha256(fingerprint.encode()).hexdigest()[:8], 16) / 0xFFFFFFFF
    return slot < fraction


def decide(features: TaskFeatures, snapshot: PolicySnapshot | None = None) -> Decision:
    selected = snapshot or PolicySnapshot.default()
    candidate = proposed_route(features)
    if candidate is None:
        return Decision(
            task_bucket=features.bucket,
            applied_route=selected.baseline,
            candidate_route=None,
            mode="baseline",
            reason="The task is outside every cheaper route's proven eligibility envelope.",
            verification_required=True,
            policy_version=selected.version,
            prework=features.deterministic_prework,
        )
    if features.risk > candidate.allowed_risk:
        return Decision(
            task_bucket=features.bucket,
            applied_route=selected.baseline,
            candidate_route=candidate,
            mode="shadow",
            reason="The candidate route does not satisfy the task's risk floor.",
            verification_required=True,
            policy_version=selected.version,
            prework=features.deterministic_prework,
        )

    bucket = selected.buckets.get(features.bucket)
    if bucket is None or bucket.route_name != candidate.name or bucket.status == "shadow":
        return Decision(
            task_bucket=features.bucket,
            applied_route=selected.baseline,
            candidate_route=candidate,
            mode="shadow",
            reason=(
                "The cheaper route is collecting paired evidence and cannot affect execution yet."
            ),
            verification_required=True,
            policy_version=selected.version,
            prework=features.deterministic_prework,
        )
    if bucket.status == "rolled_back":
        return Decision(
            task_bucket=features.bucket,
            applied_route=selected.baseline,
            candidate_route=candidate,
            mode="shadow",
            reason="The candidate was rolled back and must earn new independent evidence.",
            verification_required=True,
            policy_version=selected.version,
            prework=features.deterministic_prework,
        )
    if bucket.status == "canary" and not _canary_selected(
        features.fingerprint, bucket.canary_fraction
    ):
        return Decision(
            task_bucket=features.bucket,
            applied_route=selected.baseline,
            candidate_route=candidate,
            mode="canary",
            reason="This task is in the baseline share of a deterministic canary.",
            verification_required=True,
            policy_version=selected.version,
            prework=features.deterministic_prework,
        )

    return Decision(
        task_bucket=features.bucket,
        applied_route=candidate,
        candidate_route=candidate,
        mode="active" if bucket.status == "active" else "canary",
        reason="Verified evidence permits the candidate inside this task bucket.",
        verification_required=candidate.requires_verification,
        policy_version=selected.version,
        prework=features.deterministic_prework,
    )
