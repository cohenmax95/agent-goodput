from __future__ import annotations

from dataclasses import asdict, dataclass

from .models import RiskLevel, TaskFeatures


@dataclass(frozen=True)
class DelegationEstimate:
    allowed: bool
    requested_agents: int
    recommended_agents: int
    duplicated_context_tokens: int
    expected_support_tokens: int
    verification_tokens: int
    estimated_total_extra_tokens: int
    expected_wall_time_saved_ms: int
    reason: str

    def to_dict(self) -> dict[str, object]:
        return asdict(self)


def delegation_gate(
    features: TaskFeatures,
    *,
    requested_agents: int,
    independent_work_items: int,
    duplicated_context_tokens: int,
    expected_tokens_per_agent: int,
    verification_tokens: int,
    expected_serial_ms: int,
    expected_parallel_ms: int,
    max_agents: int = 2,
    minimum_time_saved_ms: int = 5_000,
    max_token_overhead_ratio: float = 0.45,
) -> DelegationEstimate:
    if requested_agents < 1:
        raise ValueError("requested_agents must be positive")
    if (
        min(
            independent_work_items,
            duplicated_context_tokens,
            expected_tokens_per_agent,
            verification_tokens,
            expected_serial_ms,
            expected_parallel_ms,
        )
        < 0
    ):
        raise ValueError("delegation estimates cannot be negative")

    recommended = min(requested_agents, independent_work_items, max_agents)
    extra = (
        recommended * (duplicated_context_tokens + expected_tokens_per_agent) + verification_tokens
    )
    single_agent_estimate = max(
        expected_tokens_per_agent * max(1, independent_work_items),
        1,
    )
    overhead_ratio = extra / single_agent_estimate
    time_saved = max(0, expected_serial_ms - expected_parallel_ms)

    reason = "Independent work is likely to finish materially faster within the token cap."
    allowed = True
    if not features.parallelizable or independent_work_items < 2:
        allowed = False
        reason = "The work has not been shown to split into independent pieces."
    elif recommended < 2:
        allowed = False
        reason = "Fewer than two independent support tasks remain after the agent cap."
    elif features.risk >= RiskLevel.HIGH and features.write_scope != "none":
        allowed = False
        reason = "High-risk mutation stays with the primary agent."
    elif time_saved < minimum_time_saved_ms:
        allowed = False
        reason = "Estimated time saved does not justify duplicated context."
    elif overhead_ratio > max_token_overhead_ratio:
        allowed = False
        reason = "Estimated support-token overhead exceeds the configured ROI ceiling."

    return DelegationEstimate(
        allowed=allowed,
        requested_agents=requested_agents,
        recommended_agents=recommended if allowed else 0,
        duplicated_context_tokens=duplicated_context_tokens,
        expected_support_tokens=recommended * expected_tokens_per_agent,
        verification_tokens=verification_tokens,
        estimated_total_extra_tokens=extra,
        expected_wall_time_saved_ms=time_saved,
        reason=reason,
    )
