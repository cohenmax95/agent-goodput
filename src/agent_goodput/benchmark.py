from __future__ import annotations

import hashlib
import json
import os
import platform
import random
import re
import shutil
import subprocess  # nosec B404
import tempfile
import time
import uuid
from collections.abc import Callable
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from .accounting import best_available_counter, verified_goodput
from .completion import complete_missing_evidence_paths, repairable_evidence_gaps
from .escalation import build_escalation_packet
from .evidence import EvidenceStore
from .models import ObligationResult, RunOutcome, TokenUsage
from .stats import PromotionThresholds, evaluate_promotion, pair_outcomes
from .util import (
    canonical_json,
    read_json,
    sha256_bytes,
    sha256_text,
    utc_now,
    write_json,
)


class ManifestError(ValueError):
    pass


def normalize_evidence_path(value: str) -> str:
    normalized = value.strip().replace("\\", "/")
    normalized = normalized.removeprefix("./")
    normalized = re.sub(r"(?:#L\d+(?:-L?\d+)?|:L?\d+(?::\d+)?(?:-\d+)?)$", "", normalized)
    return normalized


@dataclass(frozen=True)
class BenchmarkRun:
    benchmark_id: str
    manifest_name: str
    manifest_hash: str
    bundle_hash: str
    started_at: str
    completed_at: str
    outcomes: tuple[RunOutcome, ...]
    randomized_order: tuple[str, ...]
    environment: dict[str, str]

    def summary(self) -> dict[str, Any]:
        pairs = pair_outcomes(self.outcomes)
        baseline = [item for item in self.outcomes if item.variant == "baseline"]
        candidate = [item for item in self.outcomes if item.variant == "candidate"]
        baseline_tokens = sum(item.usage.raw_total_tokens for item in baseline)
        candidate_tokens = sum(item.usage.raw_total_tokens for item in candidate)

        def variant_summary(items: list[RunOutcome]) -> dict[str, Any]:
            response_cycles = [
                item.usage.response_cycles
                for item in items
                if item.usage.response_cycles is not None
            ]
            escalation_values = [
                value
                for item in items
                if isinstance(
                    (value := item.metadata.get("selective_escalation")),
                    dict,
                )
            ]
            repairs = [value for value in escalation_values if value.get("applied")]
            repair_usage = [
                value
                for repair in repairs
                if isinstance((value := repair.get("repair_usage")), dict)
            ]
            completion_values = [
                value
                for item in items
                if isinstance(
                    (value := item.metadata.get("deterministic_completion")),
                    dict,
                )
            ]
            eligible_completions = [value for value in completion_values if value.get("eligible")]
            completions = [value for value in completion_values if value.get("applied")]
            return {
                "pass_rate": (sum(item.passed for item in items) / len(items) if items else 0.0),
                "input_tokens": sum(item.usage.input_tokens for item in items),
                "cached_input_tokens": sum(item.usage.cached_input_tokens for item in items),
                "uncached_input_tokens": sum(item.usage.uncached_input_tokens for item in items),
                "output_tokens": sum(item.usage.output_tokens for item in items),
                "reasoning_tokens": sum(item.usage.reasoning_tokens for item in items),
                "raw_tokens": sum(item.usage.raw_total_tokens for item in items),
                "verified_goodput": verified_goodput(items),
                "elapsed_ms": sum(item.elapsed_ms for item in items),
                "agent_run_invocations": sum(item.usage.calls for item in items),
                "response_cycles": (
                    sum(response_cycles) if len(response_cycles) == len(items) else None
                ),
                "response_cycle_coverage": len(response_cycles),
                "repair_count": len(repairs),
                "repair_success_count": sum(bool(item.get("repaired")) for item in repairs),
                "repair_raw_tokens": sum(
                    int(item.get("input_tokens", 0)) + int(item.get("output_tokens", 0))
                    for item in repair_usage
                ),
                "repair_elapsed_ms": sum(int(item.get("repair_elapsed_ms", 0)) for item in repairs),
                "deterministic_completion_count": len(completions),
                "deterministic_completion_attempt_count": len(eligible_completions),
                "deterministic_completion_refusal_count": sum(
                    not bool(item.get("completed")) for item in eligible_completions
                ),
                "deterministic_completion_success_count": sum(
                    bool(item.get("completed")) for item in completions
                ),
                "deterministic_completion_paths_added": sum(
                    int(item.get("added_path_count", 0)) for item in completions
                ),
                "deterministic_completion_certificates_added": sum(
                    int(item.get("certificate_count", 0)) for item in completions
                ),
                "deterministic_completion_facts_matched": sum(
                    int(item.get("matched_fact_count", 0)) for item in completions
                ),
                "deterministic_completion_elapsed_ms": sum(
                    int(item.get("elapsed_ms", 0)) for item in completions
                ),
            }

        return {
            "benchmark_id": self.benchmark_id,
            "manifest_name": self.manifest_name,
            "manifest_hash": self.manifest_hash,
            "bundle_hash": self.bundle_hash,
            "pair_count": len(pairs),
            "baseline": variant_summary(baseline),
            "candidate": variant_summary(candidate),
            "raw_token_savings": (
                (baseline_tokens - candidate_tokens) / baseline_tokens if baseline_tokens else 0.0
            ),
            "promotion": evaluate_promotion(
                self.outcomes,
                thresholds=PromotionThresholds(bootstrap_iterations=2_000),
            ).to_dict(),
        }

    def to_dict(self) -> dict[str, Any]:
        return {
            "benchmark_id": self.benchmark_id,
            "manifest_name": self.manifest_name,
            "manifest_hash": self.manifest_hash,
            "bundle_hash": self.bundle_hash,
            "started_at": self.started_at,
            "completed_at": self.completed_at,
            "outcomes": [item.to_dict() for item in self.outcomes],
            "randomized_order": list(self.randomized_order),
            "environment": self.environment,
            "summary": self.summary(),
        }


def load_manifest(path: str | Path) -> tuple[dict[str, Any], str]:
    manifest_path = Path(path).expanduser().resolve()
    with manifest_path.open(encoding="utf-8") as stream:
        manifest = json.load(stream)
    validate_manifest(manifest)
    return manifest, sha256_text(canonical_json(manifest))


def benchmark_bundle_hash(
    manifest_path: str | Path,
    manifest: dict[str, Any] | None = None,
) -> str:
    manifest_file = Path(manifest_path).expanduser().resolve()
    loaded, manifest_hash = (
        (manifest, sha256_text(canonical_json(manifest)))
        if manifest is not None
        else load_manifest(manifest_file)
    )
    if loaded is None:  # Defensive guard for static type narrowing.
        raise ManifestError("benchmark manifest did not load")
    assets: dict[str, str] = {"manifest": manifest_hash}

    def add_file(label: str, path: Path) -> None:
        resolved = path.resolve()
        if path.is_symlink():
            raise ManifestError(f"benchmark asset cannot be a symlink: {label}")
        if not resolved.is_file():
            raise ManifestError(f"benchmark asset does not exist: {label}")
        assets[label] = sha256_bytes(resolved.read_bytes())

    for task in loaded["tasks"]:
        task_id = str(task["id"])
        if task.get("instruction_file"):
            add_file(
                f"task:{task_id}:instruction",
                manifest_file.parent / str(task["instruction_file"]),
            )
        fixture = (manifest_file.parent / str(task["fixture"])).resolve()
        if not fixture.is_dir():
            raise ManifestError(f"fixture directory does not exist: {fixture}")
        for path in sorted(fixture.rglob("*")):
            if not path.is_file():
                continue
            relative = path.relative_to(fixture)
            if "__pycache__" in relative.parts or path.suffix == ".pyc" or path.name == ".DS_Store":
                continue
            add_file(f"task:{task_id}:fixture:{relative.as_posix()}", path)

    repository_root: Path | None = None
    for candidate_root in (manifest_file.parent, *manifest_file.parents):
        if (candidate_root / "src" / "agent_goodput").is_dir():
            repository_root = candidate_root
            break
    if repository_root is not None:
        for path in sorted((repository_root / "src" / "agent_goodput").rglob("*.py")):
            add_file(
                f"runtime:{path.relative_to(repository_root).as_posix()}",
                path,
            )
        project_file = repository_root / "pyproject.toml"
        if project_file.is_file():
            add_file("runtime:pyproject.toml", project_file)

    for variant_name, variant in loaded["variants"].items():
        configs = [("primary", variant)]
        if isinstance(variant.get("repair"), dict):
            configs.append(("repair", variant["repair"]))
        for config_name, config in configs:
            references = [
                (
                    f"variant:{variant_name}:{config_name}:command:{index}",
                    value,
                )
                for index, value in enumerate(config.get("command", []))
            ]
            references.extend(
                (
                    f"variant:{variant_name}:{config_name}:env:{key}",
                    value,
                )
                for key, value in config.get("env", {}).items()
            )
            for label, raw in references:
                value = str(raw).replace(
                    "{manifest_dir}",
                    str(manifest_file.parent),
                )
                if "{" in value or "}" in value:
                    continue
                candidate = Path(value)
                if not candidate.is_absolute():
                    candidate = manifest_file.parent / candidate
                if candidate.is_file() and candidate.suffix.casefold() in {
                    ".json",
                    ".md",
                    ".py",
                    ".sh",
                    ".toml",
                    ".txt",
                    ".yaml",
                    ".yml",
                }:
                    add_file(label, candidate)

    return sha256_text(canonical_json(assets))


def validate_runtime_lock(manifest: dict[str, Any]) -> dict[str, str]:
    raw = manifest.get("runtime_lock")
    if raw is None:
        return {}
    if not isinstance(raw, dict):
        raise ManifestError("runtime_lock must be an object")
    required = {"codex_binary", "codex_version", "codex_sha256"}
    missing = required - raw.keys()
    if missing:
        raise ManifestError("runtime_lock missing fields: " + ", ".join(sorted(missing)))
    binary = Path(str(raw["codex_binary"])).expanduser()
    if not binary.is_absolute():
        raise ManifestError("runtime_lock codex_binary must be an absolute path")
    if not binary.is_file():
        raise ManifestError(f"runtime_lock binary does not exist: {binary}")
    expected_sha256 = str(raw["codex_sha256"]).casefold()
    with binary.open("rb") as stream:
        actual_sha256 = hashlib.file_digest(stream, "sha256").hexdigest()
    if actual_sha256 != expected_sha256:
        raise ManifestError(
            "runtime_lock Codex checksum does not match: "
            f"expected {expected_sha256}, got {actual_sha256}"
        )
    # The executable path is checksum-pinned by the manifest.
    checked = subprocess.run(  # nosec B603
        [str(binary), "--version"],
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        timeout=30,
        check=False,
    )
    actual_version = checked.stdout.strip()
    expected_version = str(raw["codex_version"]).strip()
    if checked.returncode != 0 or actual_version != expected_version:
        raise ManifestError(
            "runtime_lock Codex version does not match: "
            f"expected {expected_version!r}, got {actual_version!r}"
        )
    for variant_name, variant in manifest["variants"].items():
        configured = variant.get("env", {}).get("CODEX_BINARY")
        if configured != str(binary):
            raise ManifestError(f"{variant_name} CODEX_BINARY must match runtime_lock codex_binary")
        repair = variant.get("repair")
        if isinstance(repair, dict):
            repair_binary = repair.get("env", {}).get("CODEX_BINARY")
            if repair_binary != str(binary):
                raise ManifestError(
                    f"{variant_name} repair CODEX_BINARY must match runtime_lock codex_binary"
                )
    return {
        "codex_version": actual_version,
        "codex_binary_sha256": actual_sha256,
    }


def validate_manifest(manifest: dict[str, Any]) -> None:
    required = {"schema_version", "name", "variants", "tasks"}
    missing = required - manifest.keys()
    if missing:
        raise ManifestError(f"manifest missing fields: {', '.join(sorted(missing))}")
    if manifest["schema_version"] != 1:
        raise ManifestError("only benchmark schema_version 1 is supported")
    variants = manifest["variants"]
    if set(variants) != {"baseline", "candidate"}:
        raise ManifestError("variants must contain exactly baseline and candidate")
    for name, variant in variants.items():
        command = variant.get("command")
        if (
            not isinstance(command, list)
            or not command
            or not all(isinstance(item, str) for item in command)
        ):
            raise ManifestError(f"{name} command must be a non-empty string array")
        if not variant.get("route_name"):
            raise ManifestError(f"{name} route_name is required")
        repair = variant.get("repair")
        if repair is not None:
            if not isinstance(repair, dict):
                raise ManifestError(f"{name} repair must be an object")
            repair_command = repair.get("command")
            if (
                not isinstance(repair_command, list)
                or not repair_command
                or not all(isinstance(item, str) for item in repair_command)
            ):
                raise ManifestError(f"{name} repair command must be a non-empty string array")
            if not repair.get("route_name"):
                raise ManifestError(f"{name} repair route_name is required")
            allowed_types = repair.get("on_evaluator_types")
            if (
                not isinstance(allowed_types, list)
                or not allowed_types
                or not all(isinstance(item, str) and item for item in allowed_types)
            ):
                raise ManifestError(
                    f"{name} repair on_evaluator_types must be a non-empty string array"
                )
            repair_mode = str(repair.get("mode", "targeted"))
            if repair_mode not in {"targeted", "clean-retry"}:
                raise ManifestError(f"{name} repair mode must be targeted or clean-retry")
        completion = variant.get("deterministic_completion")
        if completion is not None:
            if not isinstance(completion, dict):
                raise ManifestError(f"{name} deterministic_completion must be an object")
            if completion.get("kind") != "evidence-path-certificate":
                raise ManifestError(
                    f"{name} deterministic_completion kind must be evidence-path-certificate"
                )
            for field, default, maximum in (
                ("max_files", 8, 8),
                ("max_file_bytes", 262_144, 10_000_000),
            ):
                value = completion.get(field, default)
                valid_integer = isinstance(value, int) and not isinstance(value, bool)
                if not valid_integer or not 1 <= value <= maximum:
                    raise ManifestError(
                        f"{name} deterministic_completion {field} must be between 1 and {maximum}"
                    )
    task_ids: set[str] = set()
    for task in manifest["tasks"]:
        task_id = task.get("id")
        if not task_id or task_id in task_ids:
            raise ManifestError("task ids must be non-empty and unique")
        task_ids.add(task_id)
        if not task.get("family") or not task.get("fixture"):
            raise ManifestError(f"task {task_id} needs family and fixture")
        if not isinstance(task.get("evaluators"), list) or not task["evaluators"]:
            raise ManifestError(f"task {task_id} needs deterministic evaluators")


def _format_command(
    command: list[str],
    *,
    manifest_dir: Path,
    workspace: Path,
    instruction_file: Path,
    artifact_dir: Path,
    seed: int,
    variant: dict[str, Any],
) -> list[str]:
    values = {
        "manifest_dir": str(manifest_dir),
        "workspace": str(workspace),
        "instruction_file": str(instruction_file),
        "artifact_dir": str(artifact_dir),
        "seed": str(seed),
        "model": str(variant.get("model", "")),
        "effort": str(variant.get("effort", "")),
    }
    return [part.format_map(values) for part in command]


def _read_usage(
    variant: dict[str, Any],
    workspace: Path,
    *,
    instruction: str,
    stdout: str,
) -> TokenUsage:
    usage_file = variant.get("usage_file")
    if usage_file:
        path = workspace / usage_file
        if path.exists():
            with path.open(encoding="utf-8") as stream:
                value = json.load(stream)
            return TokenUsage(
                input_tokens=int(value["input_tokens"]),
                cached_input_tokens=int(value.get("cached_input_tokens", 0)),
                output_tokens=int(value.get("output_tokens", 0)),
                reasoning_tokens=int(value.get("reasoning_tokens", 0)),
                calls=int(value.get("calls", 1)),
                call_count_source=str(value.get("call_count_source", "agent-run")),
                response_cycles=(
                    int(value["response_cycles"])
                    if value.get("response_cycles") is not None
                    else None
                ),
                response_cycle_source=(
                    str(value["response_cycle_source"])
                    if value.get("response_cycle_source") is not None
                    else None
                ),
                source=str(value.get("source", "reported")),
            )
    counter = best_available_counter()
    return TokenUsage(
        input_tokens=counter.count(instruction),
        output_tokens=counter.count(stdout),
        calls=1,
        call_count_source="agent-run",
        source=f"estimated:{counter.name}",
    )


def _read_execution(variant: dict[str, Any], workspace: Path) -> dict[str, Any]:
    execution_file = variant.get("execution_file")
    if not execution_file:
        return {}
    execution_path = workspace / str(execution_file)
    if not execution_path.exists():
        return {}
    with execution_path.open(encoding="utf-8") as stream:
        loaded = json.load(stream)
    return loaded if isinstance(loaded, dict) else {}


def _combine_usage(first: TokenUsage, second: TokenUsage) -> TokenUsage:
    response_cycles = (
        first.response_cycles + second.response_cycles
        if first.response_cycles is not None and second.response_cycles is not None
        else None
    )
    return TokenUsage(
        input_tokens=first.input_tokens + second.input_tokens,
        cached_input_tokens=first.cached_input_tokens + second.cached_input_tokens,
        output_tokens=first.output_tokens + second.output_tokens,
        reasoning_tokens=first.reasoning_tokens + second.reasoning_tokens,
        calls=first.calls + second.calls,
        call_count_source=(
            first.call_count_source
            if first.call_count_source == second.call_count_source
            else "mixed"
        ),
        response_cycles=response_cycles,
        response_cycle_source=(
            first.response_cycle_source
            if response_cycles is not None
            and first.response_cycle_source == second.response_cycle_source
            else ("mixed" if response_cycles is not None else None)
        ),
        source=first.source if first.source == second.source else "mixed",
    )


def _sum_count_maps(*values: Any) -> dict[str, int]:
    combined: dict[str, int] = {}
    for raw in values:
        if not isinstance(raw, dict):
            continue
        for key, value in raw.items():
            if isinstance(value, int):
                normalized = str(key)
                combined[normalized] = combined.get(normalized, 0) + value
    return dict(sorted(combined.items()))


def _sum_nested_count_maps(*values: Any) -> dict[str, dict[str, int]]:
    combined: dict[str, dict[str, int]] = {}
    for raw in values:
        if not isinstance(raw, dict):
            continue
        for key, value in raw.items():
            normalized = str(key)
            merged = _sum_count_maps(combined.get(normalized), value)
            combined[normalized] = merged
    return dict(sorted(combined.items()))


def _combined_execution_metadata(
    initial: dict[str, Any],
    repair: dict[str, Any],
    *,
    usage: TokenUsage,
    elapsed_ms: int,
) -> dict[str, Any]:
    if not initial and not repair:
        return {}
    initial_prework = initial.get("prework")
    repair_prework = repair.get("prework")
    prework = [
        str(item)
        for values in (initial_prework, repair_prework)
        if isinstance(values, list)
        for item in values
    ]
    initial_runtime = str(initial.get("runtime_version", "unknown"))
    repair_runtime = str(repair.get("runtime_version", "unknown"))
    return {
        "route": initial.get("route", {}),
        "runtime_version": (initial_runtime if initial_runtime == repair_runtime else "mixed"),
        "return_code": int(repair.get("return_code", 0)),
        "elapsed_ms": elapsed_ms,
        "usage": usage.to_dict(),
        "answer_sha256": str(repair.get("answer_sha256", "")),
        "stderr_sha256": sha256_text(
            f"{initial.get('stderr_sha256', '')}:{repair.get('stderr_sha256', '')}"
        ),
        "event_count": int(initial.get("event_count", 0)) + int(repair.get("event_count", 0)),
        "event_types": _sum_count_maps(
            initial.get("event_types"),
            repair.get("event_types"),
        ),
        "item_types": _sum_count_maps(
            initial.get("item_types"),
            repair.get("item_types"),
        ),
        "item_events": _sum_nested_count_maps(
            initial.get("item_events"),
            repair.get("item_events"),
        ),
        "prework": list(dict.fromkeys(prework)),
        "instruction_sha256": str(initial.get("instruction_sha256", "")),
        "attempt_count": 2,
    }


@dataclass(frozen=True)
class _CommandResult:
    command: list[str]
    completed: subprocess.CompletedProcess[str]
    elapsed_ms: int
    error: str | None


def _execute_config(
    config: dict[str, Any],
    *,
    task: dict[str, Any],
    manifest_dir: Path,
    workspace: Path,
    instruction_file: Path,
    artifact_dir: Path,
    seed: int,
    variant_label: str,
    instruction: str,
    extra_environment: dict[str, str] | None = None,
) -> _CommandResult:
    command = _format_command(
        config["command"],
        manifest_dir=manifest_dir,
        workspace=workspace,
        instruction_file=instruction_file,
        artifact_dir=artifact_dir,
        seed=seed,
        variant=config,
    )
    environment = os.environ.copy()
    environment.update(
        {
            "AGP_WORKSPACE": str(workspace),
            "AGP_INSTRUCTION_FILE": str(instruction_file),
            "AGP_SEED": str(seed),
            "AGP_VARIANT": variant_label,
        }
    )
    environment_values = {
        "manifest_dir": str(manifest_dir),
        "workspace": str(workspace),
        "instruction_file": str(instruction_file),
        "artifact_dir": str(artifact_dir),
        "seed": str(seed),
        "model": str(config.get("model", "")),
        "effort": str(config.get("effort", "")),
    }
    environment.update(
        {
            str(key): str(value).format_map(environment_values)
            for key, value in config.get("env", {}).items()
        }
    )
    if extra_environment:
        environment.update(extra_environment)
    started = time.monotonic()
    try:
        # Benchmark manifests are trusted executable configuration; no shell is used.
        completed = subprocess.run(  # nosec B603
            command,
            cwd=workspace,
            input=instruction if config.get("stdin") == "instruction" else None,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            timeout=int(task.get("timeout", config.get("timeout", 600))),
            env=environment,
            check=False,
        )
        error = None
    except subprocess.TimeoutExpired as timeout_error:
        stdout = timeout_error.stdout or ""
        if isinstance(stdout, bytes):
            stdout = stdout.decode("utf-8", errors="replace")
        completed = subprocess.CompletedProcess(command, 124, stdout=stdout)
        error = "timeout"
    return _CommandResult(
        command=command,
        completed=completed,
        elapsed_ms=int((time.monotonic() - started) * 1_000),
        error=error,
    )


def _evaluate(
    evaluators: list[dict[str, Any]],
    *,
    workspace: Path,
    completed: subprocess.CompletedProcess[str],
) -> tuple[ObligationResult, ...]:
    results: list[ObligationResult] = []
    for raw in evaluators:
        evaluator_type = raw.get("type")
        name = str(raw.get("name", evaluator_type))
        critical = bool(raw.get("critical", False))
        weight = float(raw.get("weight", 1.0))
        passed = False
        evidence = ""
        if evaluator_type == "exit_code":
            expected = int(raw.get("expected", 0))
            passed = completed.returncode == expected
            evidence = f"exit={completed.returncode}, expected={expected}"
        elif evaluator_type == "stdout_contains":
            needle = str(raw["value"])
            passed = needle in completed.stdout
            evidence = f"stdout_sha256={sha256_text(completed.stdout)}"
        elif evaluator_type == "file_contains":
            path = workspace / raw["path"]
            text = path.read_text(encoding="utf-8", errors="replace") if path.exists() else ""
            passed = path.exists() and str(raw["value"]) in text
            evidence = f"exists={path.exists()}, sha256={sha256_text(text)}"
        elif evaluator_type == "file_equals":
            path = workspace / raw["path"]
            expected_path = workspace / raw["expected_path"]
            actual_bytes = path.read_bytes() if path.exists() else b""
            expected_bytes = expected_path.read_bytes() if expected_path.exists() else b""
            passed = path.exists() and expected_path.exists() and actual_bytes == expected_bytes
            evidence = (
                f"actual_sha256={sha256_bytes(actual_bytes)}, "
                f"expected_sha256={sha256_bytes(expected_bytes)}"
            )
        elif evaluator_type == "json_equals":
            path = workspace / raw["path"]
            if path.exists():
                with path.open(encoding="utf-8") as stream:
                    actual_value = json.load(stream)
                expected_value = raw["value"]
                passed = actual_value == expected_value
                evidence = f"json_sha256={sha256_text(canonical_json(actual_value))}"
            else:
                evidence = "file missing"
        elif evaluator_type == "answer_contract":
            path = workspace / raw["path"]
            failures: list[str] = []
            if not path.exists():
                failures.append("answer file missing")
                value: dict[str, Any] = {}
            else:
                try:
                    with path.open(encoding="utf-8") as stream:
                        loaded = json.load(stream)
                    value = loaded if isinstance(loaded, dict) else {}
                    if not isinstance(loaded, dict):
                        failures.append("answer is not an object")
                except json.JSONDecodeError as error:
                    value = {}
                    failures.append(f"invalid JSON: {error}")
            if value.get("task_id") != raw.get("task_id"):
                failures.append("task_id mismatch")
            if value.get("conclusion") != raw.get("conclusion"):
                failures.append("conclusion mismatch")
            evidence_items = value.get("evidence", [])
            if not isinstance(evidence_items, list):
                evidence_items = []
                failures.append("evidence is not an array")
            paths = {
                normalize_evidence_path(str(item.get("path")))
                for item in evidence_items
                if isinstance(item, dict) and item.get("path")
            }
            facts = "\n".join(
                str(item.get("fact", "")) for item in evidence_items if isinstance(item, dict)
            )
            for required_path in raw.get("required_paths", []):
                required_normalized = normalize_evidence_path(str(required_path))
                if not any(
                    path == required_normalized or path.endswith("/" + required_normalized)
                    for path in paths
                ):
                    failures.append(f"missing evidence path: {required_path}")
            for required_fact in raw.get("fact_contains", []):
                if str(required_fact).casefold() not in facts.casefold():
                    failures.append(f"missing evidence fact: {required_fact}")
            for forbidden_fact in raw.get("fact_forbids", []):
                if str(forbidden_fact).casefold() in facts.casefold():
                    failures.append(f"forbidden evidence fact: {forbidden_fact}")
            passed = not failures
            evidence = f"answer_sha256={sha256_text(canonical_json(value))}; " + (
                "contract passed" if passed else "; ".join(failures)
            )
        elif evaluator_type == "file_absent":
            path = workspace / raw["path"]
            passed = not path.exists()
            evidence = f"exists={path.exists()}"
        elif evaluator_type == "command":
            command = [str(item) for item in raw["command"]]
            # Benchmark manifests are trusted executable configuration; no shell is used.
            checked = subprocess.run(  # nosec B603
                command,
                cwd=workspace,
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                timeout=int(raw.get("timeout", 60)),
                check=False,
            )
            passed = checked.returncode == int(raw.get("expected_exit", 0))
            evidence = f"exit={checked.returncode}, output_sha256={sha256_text(checked.stdout)}"
        else:
            raise ManifestError(f"unknown evaluator type: {evaluator_type}")
        results.append(
            ObligationResult(
                name=name,
                passed=passed,
                weight=weight,
                critical=critical,
                evidence=evidence,
            )
        )
    return tuple(results)


def _run_one(
    *,
    manifest_dir: Path,
    task: dict[str, Any],
    variant_name: str,
    variant: dict[str, Any],
    seed: int,
    benchmark_dir: Path,
    retain_outputs: bool,
) -> RunOutcome:
    fixture = (manifest_dir / task["fixture"]).resolve()
    if not fixture.is_dir():
        raise ManifestError(f"fixture directory does not exist: {fixture}")
    run_id = str(uuid.uuid4())
    run_dir = benchmark_dir / "runs" / run_id
    run_dir.mkdir(parents=True, exist_ok=False)
    workspace = Path(tempfile.mkdtemp(prefix="workspace-", dir=run_dir))
    private_dir = Path(tempfile.mkdtemp(prefix="agent-goodput-private-"))
    try:
        shutil.copytree(fixture, workspace, dirs_exist_ok=True)
        instruction = str(task.get("instruction", ""))
        if task.get("instruction_file"):
            instruction = (manifest_dir / task["instruction_file"]).read_text(encoding="utf-8")
        instruction_file = private_dir / "instruction.txt"
        instruction_file.write_text(instruction, encoding="utf-8")
        initial = _execute_config(
            variant,
            task=task,
            manifest_dir=manifest_dir,
            workspace=workspace,
            instruction_file=instruction_file,
            artifact_dir=run_dir,
            seed=seed,
            variant_label=variant_name,
            instruction=instruction,
        )
        usage = _read_usage(
            variant,
            workspace,
            instruction=instruction,
            stdout=initial.completed.stdout,
        )
        obligations = _evaluate(
            task["evaluators"],
            workspace=workspace,
            completed=initial.completed,
        )
        initial_failure_count = sum(not item.passed for item in obligations)
        initial_execution = _read_execution(variant, workspace)
        execution_metadata = initial_execution
        elapsed_ms = initial.elapsed_ms
        error = initial.error
        route_name = str(variant["route_name"])
        output_hash = sha256_text(initial.completed.stdout)
        repair_artifact: dict[str, Any] | None = None
        completion_metadata: dict[str, Any] = {
            "configured": isinstance(variant.get("deterministic_completion"), dict),
            "eligible": False,
            "applied": False,
            "completed": False,
            "reason_code": "not-configured",
            "requested_path_count": 0,
            "requested_fact_count": 0,
            "added_path_count": 0,
            "certificate_count": 0,
            "matched_line_count": 0,
            "matched_fact_count": 0,
            "elapsed_ms": 0,
            "answer_before_sha256": "",
            "answer_after_sha256": "",
            "final_failure_count": initial_failure_count,
        }
        completion_config_raw = variant.get("deterministic_completion")
        completion_config = (
            completion_config_raw if isinstance(completion_config_raw, dict) else None
        )
        evidence_gaps = repairable_evidence_gaps(obligations)
        initial_failed_evaluators = [
            raw
            for raw, result in zip(task["evaluators"], obligations, strict=True)
            if not result.passed
        ]
        completion_eligible = bool(
            completion_config
            and evidence_gaps
            and (evidence_gaps.paths or evidence_gaps.facts)
            and initial.error is None
            and initial.completed.returncode == 0
            and initial_failed_evaluators
            and all(str(raw.get("type")) == "answer_contract" for raw in initial_failed_evaluators)
        )
        if completion_config is not None:
            if completion_eligible:
                completion_metadata["reason_code"] = "eligible"
            elif (
                evidence_gaps is not None
                and evidence_gaps.paths == ()
                and evidence_gaps.facts == ()
            ):
                completion_metadata["reason_code"] = "not-needed"
            else:
                completion_metadata["reason_code"] = "ineligible-failure-type"
            completion_metadata["eligible"] = completion_eligible
        if completion_config is not None and completion_eligible and evidence_gaps is not None:
            completion_started = time.monotonic()
            completion = complete_missing_evidence_paths(
                workspace=workspace,
                answer_file="answer.json",
                missing_paths=evidence_gaps.paths,
                missing_facts=evidence_gaps.facts,
                task_text=instruction,
                max_files=int(completion_config.get("max_files", 8)),
                max_file_bytes=int(completion_config.get("max_file_bytes", 262_144)),
            )
            completion_elapsed_ms = int((time.monotonic() - completion_started) * 1_000)
            elapsed_ms += completion_elapsed_ms
            if completion.applied:
                obligations = _evaluate(
                    task["evaluators"],
                    workspace=workspace,
                    completed=initial.completed,
                )
            completion_passed = completion.completed and all(item.passed for item in obligations)
            completion_metadata = {
                "configured": True,
                "eligible": True,
                **completion.to_dict(),
                "completed": completion_passed,
                "reason_code": (
                    completion.reason_code
                    if completion_passed or not completion.completed
                    else "revalidation-failed"
                ),
                "elapsed_ms": completion_elapsed_ms,
                "final_failure_count": sum(not item.passed for item in obligations),
            }
            if completion.applied:
                execution_metadata = {
                    **initial_execution,
                    "answer_sha256": completion.answer_after_sha256,
                    "elapsed_ms": elapsed_ms,
                }
                output_hash = sha256_text(f"{output_hash}:{completion.answer_after_sha256}")
        repair_metadata: dict[str, Any] = {
            "configured": isinstance(variant.get("repair"), dict),
            "applied": False,
            "attempt_count": 1,
            "mode": (
                str(variant.get("repair", {}).get("mode", "targeted"))
                if isinstance(variant.get("repair"), dict)
                else None
            ),
            "initial_failure_count": initial_failure_count,
            "post_completion_failure_count": sum(not item.passed for item in obligations),
            "final_failure_count": sum(not item.passed for item in obligations),
            "repaired": False,
            "repair_route_name": None,
            "repair_elapsed_ms": 0,
            "repair_usage": None,
        }

        repair_config_raw = variant.get("repair")
        repair_config = repair_config_raw if isinstance(repair_config_raw, dict) else None
        failed_evaluators = [
            (raw, result)
            for raw, result in zip(task["evaluators"], obligations, strict=True)
            if not result.passed
        ]
        allowed_types = (
            {str(item) for item in repair_config.get("on_evaluator_types", [])}
            if repair_config
            else set()
        )
        repair_eligible = bool(
            repair_config
            and failed_evaluators
            and initial.error is None
            and initial.completed.returncode == 0
            and all(str(raw.get("type")) in allowed_types for raw, _ in failed_evaluators)
        )
        if repair_config is not None and repair_eligible:
            repair_mode = str(repair_config.get("mode", "targeted"))
            packet = None
            repair_instruction = instruction
            repair_environment: dict[str, str] | None = None
            if repair_mode == "targeted":
                initial_outcome = RunOutcome(
                    run_id=run_id,
                    task_id=str(task["id"]),
                    project_id=str(task.get("project_id", "public-fixtures")),
                    task_family=str(task["family"]),
                    route_name=route_name,
                    usage=usage,
                    obligations=obligations,
                    elapsed_ms=elapsed_ms,
                    seed=seed,
                    variant=variant_name,
                    error=error,
                )
                packet = build_escalation_packet(
                    initial_outcome,
                    task_summary=instruction,
                    token_budget=int(repair_config.get("packet_token_budget", 2_000)),
                )
                if packet is None:
                    raise ManifestError("repair was eligible but no escalation packet was built")
                repair_packet_file = private_dir / "repair-packet.txt"
                repair_packet_file.write_text(packet.packet, encoding="utf-8")
                repair_instruction = packet.packet
                repair_environment = {
                    "AGP_REPAIR_PACKET_FILE": str(repair_packet_file),
                }
            repair = _execute_config(
                repair_config,
                task=task,
                manifest_dir=manifest_dir,
                workspace=workspace,
                instruction_file=instruction_file,
                artifact_dir=run_dir,
                seed=seed,
                variant_label=f"{variant_name}-repair",
                instruction=repair_instruction,
                extra_environment=repair_environment,
            )
            repair_usage = _read_usage(
                repair_config,
                workspace,
                instruction=repair_instruction,
                stdout=repair.completed.stdout,
            )
            usage = _combine_usage(usage, repair_usage)
            obligations = _evaluate(
                task["evaluators"],
                workspace=workspace,
                completed=repair.completed,
            )
            elapsed_ms += repair.elapsed_ms
            error = repair.error
            repair_execution = _read_execution(repair_config, workspace)
            execution_metadata = _combined_execution_metadata(
                initial_execution,
                repair_execution,
                usage=usage,
                elapsed_ms=elapsed_ms,
            )
            repair_output_hash = sha256_text(repair.completed.stdout)
            output_hash = sha256_text(f"{output_hash}:{repair_output_hash}")
            route_name = f"{route_name}+{repair_config['route_name']}"
            repair_metadata = {
                "configured": True,
                "applied": True,
                "attempt_count": 2,
                "mode": repair_mode,
                "initial_failure_count": initial_failure_count,
                "post_completion_failure_count": len(failed_evaluators),
                "final_failure_count": sum(not item.passed for item in obligations),
                "repaired": error is None and all(item.passed for item in obligations),
                "repair_route_name": str(repair_config["route_name"]),
                "repair_elapsed_ms": repair.elapsed_ms,
                "repair_usage": repair_usage.to_dict(),
            }
            repair_artifact = {
                "command": repair.command,
                "exit_code": repair.completed.returncode,
                "stdout_sha256": repair_output_hash,
                "usage": repair_usage.to_dict(),
                "obligations": [asdict(item) for item in obligations],
                "elapsed_ms": repair.elapsed_ms,
                "error": repair.error,
                "packet_sha256": (sha256_text(packet.packet) if packet is not None else None),
            }
            if retain_outputs:
                (run_dir / "repair-stdout.txt").write_text(
                    repair.completed.stdout,
                    encoding="utf-8",
                )

        artifact = {
            "run_id": run_id,
            "task_id": task["id"],
            "variant": variant_name,
            "seed": seed,
            "command": initial.command,
            "exit_code": initial.completed.returncode,
            "stdout_sha256": sha256_text(initial.completed.stdout),
            "usage": usage.to_dict(),
            "obligations": [asdict(item) for item in obligations],
            "elapsed_ms": elapsed_ms,
            "error": error,
            "deterministic_completion": completion_metadata,
            "selective_escalation": repair_metadata,
            "repair": repair_artifact,
        }
        write_json(run_dir / "run.json", artifact, mode=0o644)
        if retain_outputs:
            (run_dir / "stdout.txt").write_text(
                initial.completed.stdout,
                encoding="utf-8",
            )
        return RunOutcome(
            run_id=run_id,
            task_id=str(task["id"]),
            project_id=str(task.get("project_id", "public-fixtures")),
            task_family=str(task["family"]),
            route_name=route_name,
            usage=usage,
            obligations=obligations,
            elapsed_ms=elapsed_ms,
            seed=seed,
            variant=variant_name,
            error=error,
            metadata={
                "bucket": str(task.get("bucket", task["family"])),
                "stdout_sha256": output_hash,
                "execution": execution_metadata,
                "deterministic_completion": completion_metadata,
                "selective_escalation": repair_metadata,
            },
        )
    finally:
        shutil.rmtree(workspace, ignore_errors=True)
        shutil.rmtree(private_dir, ignore_errors=True)


def run_benchmark(
    manifest_path: str | Path,
    output_dir: str | Path,
    *,
    evidence_store: EvidenceStore | None = None,
    retain_outputs: bool = False,
    resume_from: str | Path | None = None,
    progress: Callable[[int, int, str], None] | None = None,
) -> BenchmarkRun:
    manifest_file = Path(manifest_path).expanduser().resolve()
    manifest, manifest_hash = load_manifest(manifest_file)
    runtime = validate_runtime_lock(manifest)
    bundle_hash = benchmark_bundle_hash(manifest_file, manifest)
    seed_value = int(manifest.get("random_seed", 1729))
    work: list[tuple[dict[str, Any], str, int]] = []
    for task in manifest["tasks"]:
        seeds = task.get("seeds", [seed_value])
        for seed in seeds:
            for variant_name in ("baseline", "candidate"):
                work.append((task, variant_name, int(seed)))
    # The seed provides reproducible ordering, not a security boundary.
    generator = random.Random(seed_value)  # nosec B311
    generator.shuffle(work)
    order = tuple(f"{task['id']}:{variant}:{seed}" for task, variant, seed in work)
    if resume_from is not None:
        benchmark_dir = Path(resume_from).expanduser().resolve()
        checkpoint_path = benchmark_dir / "checkpoint.json"
        checkpoint = read_json(checkpoint_path)
        if not isinstance(checkpoint, dict):
            raise ManifestError(f"resume checkpoint is missing: {checkpoint_path}")
        if checkpoint.get("manifest_hash") != manifest_hash:
            raise ManifestError("resume checkpoint manifest hash does not match")
        if checkpoint.get("bundle_hash") != bundle_hash:
            raise ManifestError("resume checkpoint benchmark assets changed")
        if tuple(checkpoint.get("randomized_order", [])) != order:
            raise ManifestError("resume checkpoint execution order does not match")
        benchmark_id = str(checkpoint.get("benchmark_id", benchmark_dir.name))
        started_at = str(checkpoint["started_at"])
        outcomes = [
            RunOutcome.from_dict(item)
            for item in checkpoint.get("outcomes", [])
            if isinstance(item, dict)
        ]
        if evidence_store is not None and outcomes:
            raise ManifestError(
                "cannot resume an ingested benchmark without an evidence replay ledger"
            )
    else:
        benchmark_id = f"{manifest['name']}-{uuid.uuid4().hex[:12]}"
        benchmark_dir = Path(output_dir).expanduser().resolve() / benchmark_id
        benchmark_dir.mkdir(parents=True, exist_ok=False)
        checkpoint_path = benchmark_dir / "checkpoint.json"
        started_at = utc_now()
        outcomes = []

    completed_keys = {(item.task_id, item.variant, item.seed) for item in outcomes}
    if len(completed_keys) != len(outcomes):
        raise ManifestError("resume checkpoint contains duplicate outcomes")

    def save_checkpoint(*, status: str, completed_at: str | None = None) -> None:
        write_json(
            checkpoint_path,
            {
                "schema_version": 1,
                "benchmark_id": benchmark_id,
                "manifest_name": str(manifest["name"]),
                "manifest_hash": manifest_hash,
                "bundle_hash": bundle_hash,
                "started_at": started_at,
                "completed_at": completed_at,
                "status": status,
                "randomized_order": list(order),
                "outcomes": [item.to_dict() for item in outcomes],
            },
            mode=0o600,
        )

    save_checkpoint(status="running")
    total = len(work)
    for task, variant_name, seed in work:
        work_key = (str(task["id"]), variant_name, seed)
        if work_key in completed_keys:
            continue
        variant = {
            **manifest["variants"][variant_name],
            **task.get("variant_overrides", {}).get(variant_name, {}),
        }
        if "env" in manifest["variants"][variant_name] or "env" in task.get(
            "variant_overrides", {}
        ).get(variant_name, {}):
            variant["env"] = {
                **manifest["variants"][variant_name].get("env", {}),
                **task.get("variant_overrides", {}).get(variant_name, {}).get("env", {}),
            }
        outcome = _run_one(
            manifest_dir=manifest_file.parent,
            task=task,
            variant_name=variant_name,
            variant=variant,
            seed=seed,
            benchmark_dir=benchmark_dir,
            retain_outputs=retain_outputs,
        )
        outcomes.append(outcome)
        completed_keys.add(work_key)
        if evidence_store is not None:
            evidence_store.append_outcome(outcome)
        save_checkpoint(status="running")
        if progress is not None:
            progress(
                len(outcomes),
                total,
                f"{task['id']}:{variant_name}:{seed}",
            )
    completed_at = utc_now()
    if runtime:
        runtime = validate_runtime_lock(manifest)
    result = BenchmarkRun(
        benchmark_id=benchmark_id,
        manifest_name=str(manifest["name"]),
        manifest_hash=manifest_hash,
        bundle_hash=bundle_hash,
        started_at=started_at,
        completed_at=completed_at,
        outcomes=tuple(outcomes),
        randomized_order=order,
        environment={
            "python": platform.python_version(),
            "platform": platform.platform(),
            "machine": platform.machine(),
            **runtime,
        },
    )
    write_json(benchmark_dir / "report.json", result.to_dict(), mode=0o644)
    save_checkpoint(status="complete", completed_at=completed_at)
    return result
