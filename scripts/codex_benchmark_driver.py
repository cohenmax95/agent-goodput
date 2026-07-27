#!/usr/bin/env python3
from __future__ import annotations

import os
import sys
from pathlib import Path

REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
SOURCE_ROOT = REPOSITORY_ROOT / "src"
if str(SOURCE_ROOT) not in sys.path:
    sys.path.insert(0, str(SOURCE_ROOT))

from agent_goodput.codex_runner import CodexRunner  # noqa: E402
from agent_goodput.escalation import build_repair_prompt  # noqa: E402
from agent_goodput.models import RiskLevel, Route  # noqa: E402
from agent_goodput.preflight import run_preflight  # noqa: E402
from agent_goodput.util import sha256_text, write_json  # noqa: E402


def main() -> int:
    workspace = Path(os.environ["AGP_WORKSPACE"]).resolve()
    instruction_path = Path(os.environ["AGP_INSTRUCTION_FILE"]).resolve()
    instruction = instruction_path.read_text(encoding="utf-8")
    repair_packet_path = os.environ.get("AGP_REPAIR_PACKET_FILE")
    repair_packet = (
        Path(repair_packet_path).resolve().read_text(encoding="utf-8")
        if repair_packet_path
        else None
    )
    model = os.environ.get("AGP_MODEL", "gpt-5.6-sol")
    effort = os.environ.get("AGP_EFFORT", "high")
    route = Route(
        name=f"{model}-{effort}",
        model=model,
        reasoning_effort=effort,
        allowed_risk=RiskLevel.CRITICAL,
    )
    prework_kinds = tuple(
        item.strip() for item in os.environ.get("AGP_PREWORK", "").split(",") if item.strip()
    )
    if repair_packet is not None:
        answer_path = workspace / "answer.json"
        current_answer = answer_path.read_text(encoding="utf-8") if answer_path.exists() else "{}"
        prompt = build_repair_prompt(
            repair_packet,
            current_answer=current_answer,
        )
    elif prework_kinds:
        results = run_preflight(workspace, prework_kinds)
        packet = "\n\n".join(
            f"[{item.kind}]\n{item.output[:4000]}" for item in results if item.output
        )
        prompt = (
            "Deterministic preflight follows. Treat it as an index, verify any claim from source, "
            "and do not repeat inventory work unless the packet is insufficient.\n\n"
            f"{packet}\n\n[task]\n{instruction}"
        )
    else:
        prompt = instruction
    schema = os.environ.get("AGP_OUTPUT_SCHEMA")
    runner = CodexRunner(codex=os.environ.get("CODEX_BINARY"))
    execution = runner.run(
        prompt,
        cwd=workspace,
        route=route,
        sandbox=os.environ.get("AGP_SANDBOX", "read-only"),
        timeout_seconds=int(os.environ.get("AGP_CODEX_TIMEOUT", "600")),
        output_schema=schema if schema else None,
        isolated=True,
    )
    (workspace / "answer.json").write_text(execution.answer, encoding="utf-8")
    usage_file = os.environ.get("AGP_USAGE_FILE", ".usage.json")
    execution_file = os.environ.get("AGP_EXECUTION_FILE", ".execution.json")
    write_json(
        workspace / usage_file,
        execution.usage.to_dict(),
        mode=0o644,
    )
    write_json(
        workspace / execution_file,
        {
            "route": execution.route.to_dict(),
            "runtime_version": execution.runtime_version,
            "return_code": execution.return_code,
            "elapsed_ms": execution.elapsed_ms,
            "usage": execution.usage.to_dict(),
            "answer_sha256": execution.answer_sha256,
            "stderr_sha256": execution.stderr_sha256,
            "event_count": execution.event_count,
            "event_types": execution.event_types,
            "item_types": execution.item_types,
            "item_events": execution.item_events,
            "prework": list(prework_kinds),
            "instruction_sha256": sha256_text(instruction),
            "repair_packet_sha256": (
                sha256_text(repair_packet) if repair_packet is not None else None
            ),
        },
        mode=0o644,
    )
    print(execution.answer)
    if execution.return_code != 0:
        return execution.return_code
    if execution.usage.source != "codex":
        return 3
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
