from __future__ import annotations

import re
from pathlib import Path
from typing import Any

from .util import canonical_json, read_json, sha256_bytes, sha256_text, write_json

_FORBIDDEN_KEYS = {
    "answer",
    "assistant_message",
    "assistant_output",
    "command",
    "completion",
    "content",
    "conversation",
    "cwd",
    "messages",
    "model_output",
    "prompt",
    "raw_answer",
    "raw_content",
    "raw_output",
    "request",
    "response",
    "stderr",
    "stdout",
    "tool_input",
    "tool_output",
    "transcript",
}
_PRIVATE_PATH = re.compile(
    r"(?:^|[\s\"'])"
    r"(?:/Users/[^/\s]+/|/home/[^/\s]+/|[A-Za-z]:\\Users\\[^\\\s]+\\)"
)
_SAFE_PREWORK = {
    "diff-summary",
    "inventory",
    "result-filter",
    "schema-check",
}
_SAFE_ROUTE_KEYS = {
    "allowed_risk",
    "context_budget_tokens",
    "max_subagents",
    "model",
    "name",
    "reasoning_effort",
    "requires_verification",
    "tool_call_budget",
}


def _normalized_key(value: Any) -> str:
    return re.sub(r"[^a-z0-9]+", "", str(value).casefold())


_FORBIDDEN_COMPACT_KEYS = {_normalized_key(key) for key in _FORBIDDEN_KEYS}


def _assert_public_safe(value: Any, path: str = "report") -> None:
    if isinstance(value, dict):
        for key, child in value.items():
            if _normalized_key(key) in _FORBIDDEN_COMPACT_KEYS:
                raise ValueError(f"private benchmark field at {path}.{key}")
            _assert_public_safe(child, f"{path}.{key}")
        return
    if isinstance(value, list):
        for index, child in enumerate(value):
            _assert_public_safe(child, f"{path}[{index}]")
        return
    if isinstance(value, str) and (_PRIVATE_PATH.search(value) or "file://" in value.casefold()):
        raise ValueError(f"private filesystem path at {path}")


def _public_environment(raw: Any) -> dict[str, str]:
    value = raw if isinstance(raw, dict) else {}
    machine = str(value.get("machine", "unknown"))
    platform = str(value.get("platform", "unknown")).casefold()
    if "macos" in platform:
        operating_system = "macOS"
    elif "linux" in platform:
        operating_system = "Linux"
    elif "windows" in platform:
        operating_system = "Windows"
    else:
        operating_system = "unknown"
    public = {
        "operating_system": operating_system,
        "machine": machine,
        "python": str(value.get("python", "unknown")),
    }
    for key in ("codex_version", "codex_binary_sha256"):
        if key in value:
            public[key] = str(value[key])
    return public


def _public_usage(raw: Any) -> dict[str, Any]:
    value = raw if isinstance(raw, dict) else {}
    public = {
        "input_tokens": int(value.get("input_tokens", 0)),
        "cached_input_tokens": int(value.get("cached_input_tokens", 0)),
        "output_tokens": int(value.get("output_tokens", 0)),
        "reasoning_tokens": int(value.get("reasoning_tokens", 0)),
        "calls": int(value.get("calls", 1)),
        "call_count_source": str(value.get("call_count_source", "agent-run")),
        "source": str(value.get("source", "unknown")),
    }
    if value.get("response_cycles") is not None:
        public["response_cycles"] = int(value["response_cycles"])
        public["response_cycle_source"] = str(value.get("response_cycle_source", "unknown"))
    return public


def _public_obligations(
    raw: Any,
    *,
    redact_evidence: bool,
) -> list[dict[str, Any]]:
    values = raw if isinstance(raw, list) else []
    obligations: list[dict[str, Any]] = []
    for item in values:
        if not isinstance(item, dict):
            raise ValueError("benchmark obligation must be an object")
        evidence = str(item.get("evidence", ""))[:2_000]
        public_item: dict[str, Any] = {
            "name": str(item.get("name", "unknown")),
            "passed": bool(item.get("passed", False)),
            "weight": float(item.get("weight", 1.0)),
            "critical": bool(item.get("critical", False)),
        }
        if redact_evidence:
            public_item["evidence"] = "redacted"
            public_item["evidence_sha256"] = sha256_text(evidence)
        else:
            public_item["evidence"] = evidence
        obligations.append(public_item)
    return obligations


def _public_count_map(raw: Any, *, nested: bool = False) -> dict[str, Any]:
    value = raw if isinstance(raw, dict) else {}
    result: dict[str, Any] = {}
    for key, item in value.items():
        normalized = str(key)
        if not re.fullmatch(r"[A-Za-z0-9_.:-]{1,80}", normalized):
            raise ValueError(f"unsafe telemetry counter name: {normalized!r}")
        if nested:
            result[normalized] = _public_count_map(item)
        else:
            result[normalized] = int(item)
    return result


def _public_execution(raw: Any) -> dict[str, Any]:
    value = raw if isinstance(raw, dict) else {}
    route = value.get("route")
    route_value = route if isinstance(route, dict) else {}
    prework = value.get("prework")
    prework_values = prework if isinstance(prework, list) else []
    if not all(str(item) in _SAFE_PREWORK for item in prework_values):
        raise ValueError("execution metadata contains an unknown prework kind")
    public: dict[str, Any] = {
        "answer_sha256": str(value.get("answer_sha256", "")),
        "elapsed_ms": int(value.get("elapsed_ms", 0)),
        "event_count": int(value.get("event_count", 0)),
        "event_types": _public_count_map(value.get("event_types")),
        "instruction_sha256": str(value.get("instruction_sha256", "")),
        "item_events": _public_count_map(value.get("item_events"), nested=True),
        "item_types": _public_count_map(value.get("item_types")),
        "prework": [str(item) for item in prework_values],
        "return_code": int(value.get("return_code", 0)),
        "route": {key: route_value[key] for key in sorted(_SAFE_ROUTE_KEYS) if key in route_value},
        "runtime_version": str(value.get("runtime_version", "unknown")),
        "stderr_sha256": str(value.get("stderr_sha256", "")),
        "usage": _public_usage(value.get("usage")),
    }
    return public


def _public_selective_escalation(raw: Any) -> dict[str, Any]:
    value = raw if isinstance(raw, dict) else {}
    repair_route = value.get("repair_route_name")
    repair_usage = value.get("repair_usage")
    return {
        "configured": bool(value.get("configured", False)),
        "applied": bool(value.get("applied", False)),
        "attempt_count": int(value.get("attempt_count", 1)),
        "mode": (None if value.get("mode") is None else str(value.get("mode"))),
        "initial_failure_count": int(value.get("initial_failure_count", 0)),
        "post_completion_failure_count": int(value.get("post_completion_failure_count", 0)),
        "final_failure_count": int(value.get("final_failure_count", 0)),
        "repaired": bool(value.get("repaired", False)),
        "repair_route_name": None if repair_route is None else str(repair_route),
        "repair_elapsed_ms": int(value.get("repair_elapsed_ms", 0)),
        "repair_usage": (_public_usage(repair_usage) if isinstance(repair_usage, dict) else None),
    }


def _public_deterministic_completion(raw: Any) -> dict[str, Any]:
    value = raw if isinstance(raw, dict) else {}
    return {
        "configured": bool(value.get("configured", False)),
        "eligible": bool(value.get("eligible", False)),
        "applied": bool(value.get("applied", False)),
        "completed": bool(value.get("completed", False)),
        "reason_code": str(value.get("reason_code", "unknown")),
        "requested_path_count": int(value.get("requested_path_count", 0)),
        "requested_fact_count": int(value.get("requested_fact_count", 0)),
        "added_path_count": int(value.get("added_path_count", 0)),
        "certificate_count": int(value.get("certificate_count", 0)),
        "matched_line_count": int(value.get("matched_line_count", 0)),
        "matched_fact_count": int(value.get("matched_fact_count", 0)),
        "elapsed_ms": int(value.get("elapsed_ms", 0)),
        "answer_before_sha256": str(value.get("answer_before_sha256", "")),
        "answer_after_sha256": str(value.get("answer_after_sha256", "")),
        "final_failure_count": int(value.get("final_failure_count", 0)),
    }


def _public_metadata(raw: Any) -> dict[str, Any]:
    value = raw if isinstance(raw, dict) else {}
    public: dict[str, Any] = {}
    if "bucket" in value:
        public["bucket"] = str(value["bucket"])
    if "stdout_sha256" in value:
        public["stdout_sha256"] = str(value["stdout_sha256"])
    if "execution" in value:
        public["execution"] = _public_execution(value["execution"])
    if "deterministic_completion" in value:
        public["deterministic_completion"] = _public_deterministic_completion(
            value["deterministic_completion"]
        )
    if "selective_escalation" in value:
        public["selective_escalation"] = _public_selective_escalation(value["selective_escalation"])
    return public


def _public_summary(raw: Any) -> dict[str, Any]:
    value = raw if isinstance(raw, dict) else {}

    def variant(name: str) -> dict[str, Any]:
        selected = value.get(name)
        item = selected if isinstance(selected, dict) else {}
        public = {
            "agent_run_invocations": int(item.get("agent_run_invocations", 0)),
            "cached_input_tokens": int(item.get("cached_input_tokens", 0)),
            "elapsed_ms": int(item.get("elapsed_ms", 0)),
            "input_tokens": int(item.get("input_tokens", 0)),
            "output_tokens": int(item.get("output_tokens", 0)),
            "pass_rate": float(item.get("pass_rate", 0.0)),
            "raw_tokens": int(item.get("raw_tokens", 0)),
            "reasoning_tokens": int(item.get("reasoning_tokens", 0)),
            "repair_count": int(item.get("repair_count", 0)),
            "repair_elapsed_ms": int(item.get("repair_elapsed_ms", 0)),
            "repair_raw_tokens": int(item.get("repair_raw_tokens", 0)),
            "repair_success_count": int(item.get("repair_success_count", 0)),
            "deterministic_completion_count": int(item.get("deterministic_completion_count", 0)),
            "deterministic_completion_attempt_count": int(
                item.get("deterministic_completion_attempt_count", 0)
            ),
            "deterministic_completion_refusal_count": int(
                item.get("deterministic_completion_refusal_count", 0)
            ),
            "deterministic_completion_success_count": int(
                item.get("deterministic_completion_success_count", 0)
            ),
            "deterministic_completion_paths_added": int(
                item.get("deterministic_completion_paths_added", 0)
            ),
            "deterministic_completion_certificates_added": int(
                item.get("deterministic_completion_certificates_added", 0)
            ),
            "deterministic_completion_facts_matched": int(
                item.get("deterministic_completion_facts_matched", 0)
            ),
            "deterministic_completion_elapsed_ms": int(
                item.get("deterministic_completion_elapsed_ms", 0)
            ),
            "uncached_input_tokens": int(item.get("uncached_input_tokens", 0)),
            "verified_goodput": float(item.get("verified_goodput", 0.0)),
        }
        if item.get("response_cycles") is not None:
            public["response_cycles"] = int(item["response_cycles"])
            public["response_cycle_coverage"] = int(item.get("response_cycle_coverage", 0))
        return public

    raw_promotion = value.get("promotion")
    promotion = raw_promotion if isinstance(raw_promotion, dict) else {}
    quality_ci = promotion.get("quality_delta_ci", [0.0, 0.0])
    savings_ci = promotion.get("raw_token_savings_ci", [0.0, 0.0])
    reasons = promotion.get("reasons", [])
    return {
        "benchmark_id": str(value.get("benchmark_id", "")),
        "manifest_name": str(value.get("manifest_name", "")),
        "manifest_hash": str(value.get("manifest_hash", "")),
        "bundle_hash": str(value.get("bundle_hash", "")),
        "pair_count": int(value.get("pair_count", 0)),
        "baseline": variant("baseline"),
        "candidate": variant("candidate"),
        "raw_token_savings": float(value.get("raw_token_savings", 0.0)),
        "promotion": {
            "candidate_critical_failures": int(promotion.get("candidate_critical_failures", 0)),
            "disposition": str(promotion.get("disposition", "hold")),
            "eligible": bool(promotion.get("eligible", False)),
            "pass_rate_baseline": float(promotion.get("pass_rate_baseline", 0.0)),
            "pass_rate_candidate": float(promotion.get("pass_rate_candidate", 0.0)),
            "project_count": int(promotion.get("project_count", 0)),
            "quality_delta_ci": [float(item) for item in quality_ci],
            "quality_delta_mean": float(promotion.get("quality_delta_mean", 0.0)),
            "raw_token_savings_ci": [float(item) for item in savings_ci],
            "raw_token_savings_mean": float(promotion.get("raw_token_savings_mean", 0.0)),
            "reasons": [str(item) for item in reasons],
            "sample_pairs": int(promotion.get("sample_pairs", 0)),
            "task_family_count": int(promotion.get("task_family_count", 0)),
        },
    }


def _public_outcome(
    raw: dict[str, Any],
    *,
    redact_obligation_evidence: bool,
) -> dict[str, Any]:
    run_id = str(raw.get("run_id", ""))
    raw_error = raw.get("error")
    return {
        "run_key": f"run-{sha256_text(run_id)[:12]}",
        "task_id": str(raw["task_id"]),
        "project_id": str(raw["project_id"]),
        "task_family": str(raw["task_family"]),
        "route_name": str(raw["route_name"]),
        "variant": str(raw["variant"]),
        "seed": raw.get("seed"),
        "elapsed_ms": int(raw["elapsed_ms"]),
        "usage": _public_usage(raw["usage"]),
        "obligations": _public_obligations(
            raw["obligations"],
            redact_evidence=redact_obligation_evidence,
        ),
        "passed": bool(raw["passed"]),
        "critical_failure": bool(raw["critical_failure"]),
        "quality_score": float(raw["quality_score"]),
        "verified_work_units": float(raw["verified_work_units"]),
        "error": None if raw_error is None else "redacted",
        "error_sha256": (None if raw_error is None else sha256_text(str(raw_error))),
        "metadata": _public_metadata(raw.get("metadata")),
    }


def sanitize_benchmark_report(
    raw: dict[str, Any],
    *,
    source_sha256: str,
    redact_obligation_evidence: bool = False,
) -> dict[str, Any]:
    required = {
        "benchmark_id",
        "manifest_name",
        "manifest_hash",
        "bundle_hash",
        "outcomes",
        "randomized_order",
        "summary",
    }
    missing = required - raw.keys()
    if missing:
        raise ValueError("benchmark report missing fields: " + ", ".join(sorted(missing)))
    outcomes = raw["outcomes"]
    if not isinstance(outcomes, list) or not all(isinstance(item, dict) for item in outcomes):
        raise ValueError("benchmark outcomes must be an object array")
    _assert_public_safe(raw, path="source_report")
    provenance: dict[str, Any] = {
        "source_report_sha256": source_sha256,
        "sanitizer_source_sha256": sha256_bytes(Path(__file__).read_bytes()),
        "raw_answers_included": False,
        "private_paths_included": False,
        "obligation_evidence_redacted": redact_obligation_evidence,
    }
    public: dict[str, Any] = {
        "schema_version": 1,
        "benchmark_id": str(raw["benchmark_id"]),
        "manifest_name": str(raw["manifest_name"]),
        "manifest_hash": str(raw["manifest_hash"]),
        "bundle_hash": str(raw["bundle_hash"]),
        "started_at": raw.get("started_at"),
        "completed_at": raw.get("completed_at"),
        "environment": _public_environment(raw.get("environment")),
        "outcomes": [
            _public_outcome(
                item,
                redact_obligation_evidence=redact_obligation_evidence,
            )
            for item in outcomes
        ],
        "randomized_order": list(raw["randomized_order"]),
        "summary": _public_summary(raw["summary"]),
        "provenance": provenance,
    }
    _assert_public_safe(public)
    digest_input: dict[str, Any] = dict(public)
    digest_input["provenance"] = dict(provenance)
    provenance["public_payload_sha256"] = sha256_text(canonical_json(digest_input))
    return public


def sanitize_benchmark_file(
    source: str | Path,
    destination: str | Path,
    *,
    redact_obligation_evidence: bool = False,
) -> dict[str, Any]:
    source_path = Path(source).expanduser().resolve()
    destination_path = Path(destination).expanduser().resolve()
    raw = read_json(source_path)
    if not isinstance(raw, dict):
        raise ValueError("benchmark report must be a JSON object")
    public = sanitize_benchmark_report(
        raw,
        source_sha256=sha256_bytes(source_path.read_bytes()),
        redact_obligation_evidence=redact_obligation_evidence,
    )
    write_json(destination_path, public, mode=0o644)
    return public
