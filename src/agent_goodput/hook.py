from __future__ import annotations

import json
import os
import sys
from pathlib import Path
from typing import Any

from .classify import classify_task
from .controller import PolicyController
from .policy import decide, proposed_route
from .util import (
    bounded_text,
    canonical_json,
    file_lock,
    private_project_id,
    read_json,
    sha256_text,
    state_dir,
    utc_now,
    write_json,
)

_SESSION_END_REASONS = {
    "clear",
    "logout",
    "other",
    "prompt_input_exit",
}


def _session_state_path(root: Path, session_id: str) -> Path:
    safe = sha256_text(session_id)[:24]
    return root / "sessions" / f"{safe}.json"


def _load_session(root: Path, session_id: str) -> dict[str, Any]:
    value = read_json(
        _session_state_path(root, session_id),
        {
            "session_hash": sha256_text(session_id)[:24],
            "turns": {},
            "created_at": utc_now(),
        },
    )
    if not isinstance(value, dict):
        raise ValueError("session state must be an object")
    return dict(value)


def _save_session(root: Path, session_id: str, value: dict[str, Any]) -> None:
    write_json(_session_state_path(root, session_id), value)


def _compact_context(
    decision_data: dict[str, Any],
    features: dict[str, Any],
    *,
    observed_model: str,
) -> str:
    candidate = decision_data.get("candidate_route")
    candidate_text = "none"
    if candidate:
        candidate_text = f"{candidate['model']} {candidate['reasoning_effort']}"
    prework = ", ".join(decision_data.get("prework", [])) or "none"
    return bounded_text(
        (
            "Agent Goodput route certificate: "
            f"mode={decision_data['mode']}; "
            f"policy_target={decision_data['applied_route']['model']} "
            f"{decision_data['applied_route']['reasoning_effort']}; "
            f"observed_model={observed_model}; "
            "enforcement=advisory-hook; "
            f"shadow_candidate={candidate_text}; "
            f"risk={features['risk']}; "
            f"deterministic_prework={prework}. "
            "This hook does not switch models. Do not lower quality or skip validation. "
            "Only failed obligations may be escalated."
        ),
        900,
    )


def _handle_prompt(payload: dict[str, Any], controller: PolicyController) -> dict[str, Any]:
    prompt = str(payload.get("prompt", ""))
    features = classify_task(prompt)
    snapshot = controller.load()
    candidate = proposed_route(features)
    if candidate is not None and features.bucket not in snapshot.buckets:
        snapshot = controller.register_shadow(features.bucket, candidate.name)
    decision = decide(features, snapshot)
    observed_model = str(payload.get("model", "unknown"))
    safe_payload = {
        "session_hash": sha256_text(str(payload.get("session_id", "")))[:24],
        "turn_hash": sha256_text(str(payload.get("turn_id", "")))[:24],
        "project_id": private_project_id(str(payload.get("cwd", ".")), controller.secret),
        "model": observed_model,
        "enforcement": "advisory-hook",
        "task_fingerprint": features.fingerprint,
        "features": features.to_dict(),
        "decision": decision.to_dict(),
    }
    controller.evidence.append_event("hook_route_decision", safe_payload)
    return {
        "hookSpecificOutput": {
            "hookEventName": "UserPromptSubmit",
            "additionalContext": _compact_context(
                decision.to_dict(),
                features.to_dict(),
                observed_model=observed_model,
            ),
        }
    }


def _handle_tool(
    payload: dict[str, Any], controller: PolicyController, root: Path
) -> dict[str, Any]:
    session_id = str(payload.get("session_id", "unknown"))
    turn_id = str(payload.get("turn_id", "unknown"))
    state_path = _session_state_path(root, session_id)
    with file_lock(state_path.with_suffix(".lock")):
        state = _load_session(root, session_id)
        turns = state.setdefault("turns", {})
        turn = turns.setdefault(
            sha256_text(turn_id)[:24],
            {"tool_calls": 0, "tools": {}, "response_bytes": 0},
        )
        turn["tool_calls"] += 1
        tool_name = str(payload.get("tool_name", "unknown"))
        turn["tools"][tool_name] = int(turn["tools"].get(tool_name, 0)) + 1
        response = payload.get("tool_response")
        if response is not None:
            turn["response_bytes"] += len(canonical_json(response).encode("utf-8"))
        _save_session(root, session_id, state)
    controller.evidence.append_event(
        "hook_tool_counter",
        {
            "session_hash": sha256_text(session_id)[:24],
            "turn_hash": sha256_text(turn_id)[:24],
            "tool_name": str(payload.get("tool_name", "unknown")),
            "event": str(payload.get("hook_event_name", "unknown")),
            "response_bytes": (
                len(canonical_json(payload.get("tool_response")).encode("utf-8"))
                if payload.get("tool_response") is not None
                else 0
            ),
        },
    )
    return {}


def _handle_stop(
    payload: dict[str, Any], controller: PolicyController, root: Path
) -> dict[str, Any]:
    session_id = str(payload.get("session_id", "unknown"))
    turn_id = str(payload.get("turn_id", "unknown"))
    state = _load_session(root, session_id)
    turn = state.get("turns", {}).get(sha256_text(turn_id)[:24], {})
    controller.evidence.append_event(
        "hook_turn_stop",
        {
            "session_hash": sha256_text(session_id)[:24],
            "turn_hash": sha256_text(turn_id)[:24],
            "model": str(payload.get("model", "unknown")),
            "tool_calls": int(turn.get("tool_calls", 0)),
            "tools": dict(turn.get("tools", {})),
            "response_bytes": int(turn.get("response_bytes", 0)),
            "already_continued": bool(payload.get("stop_hook_active", False)),
        },
    )
    controller.run_cycle_if_needed(trigger="stop")
    return {}


def handle_hook(payload: dict[str, Any], *, root: Path | None = None) -> dict[str, Any]:
    selected_root = state_dir(root)
    controller = PolicyController(selected_root)
    event = str(payload.get("hook_event_name", ""))
    if event == "UserPromptSubmit":
        return _handle_prompt(payload, controller)
    if event in {"PreToolUse", "PostToolUse"}:
        return _handle_tool(payload, controller, selected_root)
    if event == "Stop":
        return _handle_stop(payload, controller, selected_root)
    if event == "SessionEnd":
        raw_reason = str(payload.get("reason", "other")).strip().casefold()
        controller.evidence.append_event(
            "hook_session_end",
            {
                "session_hash": sha256_text(str(payload.get("session_id", "")))[:24],
                "model": str(payload.get("model", "unknown")),
                "reason": (raw_reason if raw_reason in _SESSION_END_REASONS else "unrecognized"),
            },
        )
        controller.run_cycle_if_needed(trigger="session-end")
    return {}


def main() -> int:
    try:
        payload = json.load(sys.stdin)
        result = handle_hook(payload)
        if result:
            print(json.dumps(result, separators=(",", ":")))
        return 0
    except Exception as error:  # fail open; hook is not a security boundary
        if os.environ.get("AGENT_GOODPUT_DEBUG") == "1":
            print(f"agent-goodput hook skipped: {error}", file=sys.stderr)
        return 0


if __name__ == "__main__":
    raise SystemExit(main())
