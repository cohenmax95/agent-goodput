from __future__ import annotations

from dataclasses import asdict, dataclass, field
from enum import IntEnum
from typing import Any, Literal


class RiskLevel(IntEnum):
    LOW = 0
    MEDIUM = 1
    HIGH = 2
    CRITICAL = 3

    @classmethod
    def parse(cls, value: str | int | RiskLevel) -> RiskLevel:
        if isinstance(value, cls):
            return value
        if isinstance(value, int):
            return cls(value)
        return cls[value.strip().upper()]

    def label(self) -> str:
        return self.name.lower()


@dataclass(frozen=True)
class Route:
    name: str
    model: str
    reasoning_effort: str
    max_subagents: int = 0
    context_budget_tokens: int | None = None
    tool_call_budget: int | None = None
    requires_verification: bool = True
    allowed_risk: RiskLevel = RiskLevel.LOW

    @classmethod
    def from_dict(cls, raw: dict[str, Any]) -> Route:
        value = dict(raw)
        value["allowed_risk"] = RiskLevel.parse(value.get("allowed_risk", "low"))
        return cls(**value)

    def to_dict(self) -> dict[str, Any]:
        value = asdict(self)
        value["allowed_risk"] = self.allowed_risk.label()
        return value


@dataclass(frozen=True)
class TaskFeatures:
    fingerprint: str
    task_kind: str
    risk: RiskLevel
    write_scope: Literal["none", "local", "external"]
    complexity: float
    ambiguity: float
    verification_strength: float
    estimated_prompt_tokens: int
    deterministic_prework: tuple[str, ...] = ()
    parallelizable: bool = False
    explicit_quality_request: bool = False
    sensitive: bool = False
    reasons: tuple[str, ...] = ()

    @property
    def bucket(self) -> str:
        complexity = "simple" if self.complexity < 0.34 else "moderate"
        if self.complexity >= 0.67:
            complexity = "complex"
        return ":".join(
            (
                self.task_kind,
                self.risk.label(),
                self.write_scope,
                complexity,
            )
        )

    def to_dict(self) -> dict[str, Any]:
        value = asdict(self)
        value["risk"] = self.risk.label()
        return value


@dataclass(frozen=True)
class TokenUsage:
    input_tokens: int
    cached_input_tokens: int = 0
    output_tokens: int = 0
    reasoning_tokens: int = 0
    calls: int = 1
    call_count_source: str = "agent-run"
    source: str = "reported"

    def __post_init__(self) -> None:
        for name in (
            "input_tokens",
            "cached_input_tokens",
            "output_tokens",
            "reasoning_tokens",
            "calls",
        ):
            if getattr(self, name) < 0:
                raise ValueError(f"{name} cannot be negative")
        if self.cached_input_tokens > self.input_tokens:
            raise ValueError("cached_input_tokens cannot exceed input_tokens")

    @property
    def uncached_input_tokens(self) -> int:
        return self.input_tokens - self.cached_input_tokens

    @property
    def raw_total_tokens(self) -> int:
        return self.input_tokens + self.output_tokens

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class ObligationResult:
    name: str
    passed: bool
    weight: float = 1.0
    critical: bool = False
    evidence: str | None = None

    def __post_init__(self) -> None:
        if self.weight <= 0:
            raise ValueError("obligation weight must be positive")


@dataclass(frozen=True)
class RunOutcome:
    run_id: str
    task_id: str
    project_id: str
    task_family: str
    route_name: str
    usage: TokenUsage
    obligations: tuple[ObligationResult, ...]
    elapsed_ms: int
    seed: int | None = None
    variant: str = "candidate"
    error: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

    @property
    def critical_failure(self) -> bool:
        return bool(self.error) or any(
            item.critical and not item.passed for item in self.obligations
        )

    @property
    def passed(self) -> bool:
        return (
            not self.error
            and bool(self.obligations)
            and all(item.passed for item in self.obligations)
        )

    @property
    def quality_score(self) -> float:
        if self.critical_failure or not self.obligations:
            return 0.0
        possible = sum(item.weight for item in self.obligations)
        earned = sum(item.weight for item in self.obligations if item.passed)
        return earned / possible

    @property
    def verified_work_units(self) -> float:
        if not self.passed:
            return 0.0
        return sum(item.weight for item in self.obligations)

    def to_dict(self) -> dict[str, Any]:
        return {
            "run_id": self.run_id,
            "task_id": self.task_id,
            "project_id": self.project_id,
            "task_family": self.task_family,
            "route_name": self.route_name,
            "usage": self.usage.to_dict(),
            "obligations": [asdict(item) for item in self.obligations],
            "elapsed_ms": self.elapsed_ms,
            "seed": self.seed,
            "variant": self.variant,
            "error": self.error,
            "metadata": self.metadata,
            "passed": self.passed,
            "critical_failure": self.critical_failure,
            "quality_score": self.quality_score,
            "verified_work_units": self.verified_work_units,
        }

    @classmethod
    def from_dict(cls, raw: dict[str, Any]) -> RunOutcome:
        usage_raw = raw["usage"]
        obligations_raw = raw["obligations"]
        return cls(
            run_id=str(raw["run_id"]),
            task_id=str(raw["task_id"]),
            project_id=str(raw["project_id"]),
            task_family=str(raw["task_family"]),
            route_name=str(raw["route_name"]),
            usage=TokenUsage(
                input_tokens=int(usage_raw["input_tokens"]),
                cached_input_tokens=int(usage_raw.get("cached_input_tokens", 0)),
                output_tokens=int(usage_raw.get("output_tokens", 0)),
                reasoning_tokens=int(usage_raw.get("reasoning_tokens", 0)),
                calls=int(usage_raw.get("calls", 1)),
                call_count_source=str(usage_raw.get("call_count_source", "agent-run")),
                source=str(usage_raw.get("source", "reported")),
            ),
            obligations=tuple(
                ObligationResult(
                    name=str(item["name"]),
                    passed=bool(item["passed"]),
                    weight=float(item.get("weight", 1.0)),
                    critical=bool(item.get("critical", False)),
                    evidence=item.get("evidence"),
                )
                for item in obligations_raw
            ),
            elapsed_ms=int(raw["elapsed_ms"]),
            seed=int(raw["seed"]) if raw.get("seed") is not None else None,
            variant=str(raw.get("variant", "candidate")),
            error=raw.get("error"),
            metadata=dict(raw.get("metadata", {})),
        )


@dataclass(frozen=True)
class Decision:
    task_bucket: str
    applied_route: Route
    candidate_route: Route | None
    mode: Literal["baseline", "shadow", "canary", "active"]
    reason: str
    verification_required: bool
    policy_version: int
    prework: tuple[str, ...] = ()

    def to_dict(self) -> dict[str, Any]:
        return {
            "task_bucket": self.task_bucket,
            "applied_route": self.applied_route.to_dict(),
            "candidate_route": self.candidate_route.to_dict() if self.candidate_route else None,
            "mode": self.mode,
            "reason": self.reason,
            "verification_required": self.verification_required,
            "policy_version": self.policy_version,
            "prework": list(self.prework),
        }


@dataclass(frozen=True)
class PromotionReport:
    eligible: bool
    disposition: Literal["hold", "canary", "promote", "rollback"]
    sample_pairs: int
    project_count: int
    task_family_count: int
    candidate_critical_failures: int
    quality_delta_mean: float
    quality_delta_ci: tuple[float, float]
    raw_token_savings_mean: float
    raw_token_savings_ci: tuple[float, float]
    pass_rate_candidate: float
    pass_rate_baseline: float
    reasons: tuple[str, ...]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)
