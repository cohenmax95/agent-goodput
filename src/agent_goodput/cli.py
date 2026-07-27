from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path
from typing import Any

from .benchmark import run_benchmark
from .classify import classify_task
from .codex_runner import CodexRunner
from .context import audit_paths, costs_as_json
from .controller import PolicyController
from .delegation import delegation_gate
from .evidence import EvidenceStore
from .installer import bundle_files, install, uninstall
from .models import RunOutcome
from .policy import decide, proposed_route
from .preflight import run_preflight
from .sanitize import sanitize_benchmark_file
from .util import read_json, state_dir


def _print(value: Any) -> None:
    print(json.dumps(value, indent=2, sort_keys=True))


def _prompt(args: argparse.Namespace) -> str:
    if getattr(args, "prompt_file", None):
        return Path(args.prompt_file).read_text(encoding="utf-8")
    if getattr(args, "prompt", None):
        return str(args.prompt)
    if not sys.stdin.isatty():
        return sys.stdin.read()
    raise ValueError("provide a prompt, --prompt-file, or stdin")


def _root(args: argparse.Namespace) -> Path:
    return state_dir(getattr(args, "state_dir", None))


def command_classify(args: argparse.Namespace) -> int:
    _print(classify_task(_prompt(args)).to_dict())
    return 0


def command_route(args: argparse.Namespace) -> int:
    features = classify_task(_prompt(args))
    controller = PolicyController(_root(args))
    snapshot = controller.load()
    candidate = proposed_route(features)
    if args.register_shadow and candidate and features.bucket not in snapshot.buckets:
        snapshot = controller.register_shadow(features.bucket, candidate.name)
    _print(
        {
            "features": features.to_dict(),
            "decision": decide(features, snapshot).to_dict(),
            "policy_digest": snapshot.digest,
        }
    )
    return 0


def command_context_audit(args: argparse.Namespace) -> int:
    costs = audit_paths(args.paths, kind=args.kind)
    print(costs_as_json(costs))
    return 0


def command_preflight(args: argparse.Namespace) -> int:
    _print([item.to_dict() for item in run_preflight(args.cwd, args.kinds)])
    return 0


def command_delegate(args: argparse.Namespace) -> int:
    features = classify_task(_prompt(args))
    estimate = delegation_gate(
        features,
        requested_agents=args.requested_agents,
        independent_work_items=args.work_items,
        duplicated_context_tokens=args.duplicated_context_tokens,
        expected_tokens_per_agent=args.tokens_per_agent,
        verification_tokens=args.verification_tokens,
        expected_serial_ms=args.serial_ms,
        expected_parallel_ms=args.parallel_ms,
        max_agents=args.max_agents,
    )
    _print({"features": features.to_dict(), "delegation": estimate.to_dict()})
    return 0


def command_ingest(args: argparse.Namespace) -> int:
    raw = read_json(Path(args.outcome))
    outcome = RunOutcome.from_dict(raw)
    store = EvidenceStore(_root(args) / "evidence.sqlite3")
    sequence, event_hash = store.append_outcome(outcome)
    _print({"sequence": sequence, "event_hash": event_hash, "run_id": outcome.run_id})
    return 0


def command_policy_show(args: argparse.Namespace) -> int:
    controller = PolicyController(_root(args))
    snapshot = controller.load()
    _print({"policy": snapshot.to_dict(), "digest": snapshot.digest})
    return 0


def command_policy_register(args: argparse.Namespace) -> int:
    controller = PolicyController(_root(args))
    snapshot = controller.register_shadow(args.bucket, args.route)
    _print({"policy": snapshot.to_dict(), "digest": snapshot.digest})
    return 0


def command_policy_evaluate(args: argparse.Namespace) -> int:
    controller = PolicyController(_root(args))
    _print(controller.evaluate(args.bucket))
    return 0


def command_policy_apply(args: argparse.Namespace) -> int:
    controller = PolicyController(_root(args))
    evaluation = controller.evaluate(args.bucket)
    if not args.apply:
        _print({"dry_run": True, **evaluation})
        return 0
    snapshot = controller.apply_evaluation(args.bucket)
    _print({"dry_run": False, "policy": snapshot.to_dict(), "digest": snapshot.digest})
    return 0


def command_policy_rollback(args: argparse.Namespace) -> int:
    controller = PolicyController(_root(args))
    if not args.apply:
        _print(
            {
                "dry_run": True,
                "bucket": args.bucket,
                "reason_code": args.reason_code,
                "action": "roll back to baseline",
            }
        )
        return 0
    snapshot = controller.emergency_rollback(args.bucket, args.reason_code)
    _print({"dry_run": False, "policy": snapshot.to_dict(), "digest": snapshot.digest})
    return 0


def command_policy_cycle(args: argparse.Namespace) -> int:
    controller = PolicyController(_root(args))
    if not args.apply:
        evaluations = [controller.evaluate(bucket) for bucket in sorted(controller.load().buckets)]
        _print({"dry_run": True, "evaluations": evaluations})
        return 0
    _print({"dry_run": False, **controller.run_cycle()})
    return 0


def command_evidence_verify(args: argparse.Namespace) -> int:
    store = EvidenceStore(_root(args) / "evidence.sqlite3")
    ok, message = store.verify_chain()
    _print({"ok": ok, "message": message, "head_hash": store.head_hash})
    return 0 if ok else 1


def command_benchmark_run(args: argparse.Namespace) -> int:
    root = _root(args)
    store = EvidenceStore(root / "evidence.sqlite3") if args.ingest else None

    def progress(completed: int, total: int, key: str) -> None:
        print(
            f"benchmark progress {completed}/{total}: {key}",
            file=sys.stderr,
            flush=True,
        )

    result = run_benchmark(
        args.manifest,
        args.output,
        evidence_store=store,
        retain_outputs=args.retain_outputs,
        resume_from=args.resume,
        progress=progress,
    )
    _print(result.to_dict())
    return 0


def command_benchmark_sanitize(args: argparse.Namespace) -> int:
    result = sanitize_benchmark_file(
        args.report,
        args.output,
        redact_obligation_evidence=args.redact_obligation_evidence,
    )
    _print(
        {
            "output": str(Path(args.output).expanduser().resolve()),
            "benchmark_id": result["benchmark_id"],
            "pair_count": result["summary"]["pair_count"],
            "provenance": result["provenance"],
        }
    )
    return 0


def command_install(args: argparse.Namespace) -> int:
    source = Path(__file__).resolve().parents[2]
    plan = install(source, args.agents_home, apply=args.apply)
    _print({"dry_run": not args.apply, **plan.to_dict()})
    return 0 if plan.apply_allowed else 2


def command_uninstall(args: argparse.Namespace) -> int:
    plan = uninstall(args.agents_home, apply=args.apply)
    _print({"dry_run": not args.apply, **plan.to_dict()})
    return 0 if plan.apply_allowed else 2


def command_doctor(args: argparse.Namespace) -> int:
    root = _root(args)
    controller = PolicyController(root)
    chain_ok, chain_message = controller.evidence.verify_chain()
    source = Path(__file__).resolve().parents[2]
    bundled = bundle_files(source)
    checks = {
        "python_supported": sys.version_info >= (3, 11),
        "policy_signature": True,
        "evidence_chain": chain_ok,
        "plugin_manifest_json": False,
        "hooks_json": False,
        "raw_telemetry_default": False,
        "live_install_detected": bool(os.environ.get("PLUGIN_ROOT")),
    }
    for key, relative in (
        ("plugin_manifest_json", ".codex-plugin/plugin.json"),
        ("hooks_json", "hooks/hooks.json"),
    ):
        try:
            path = bundled[relative]
            with path.open(encoding="utf-8") as stream:
                json.load(stream)
            checks[key] = True
        except (KeyError, OSError, json.JSONDecodeError):
            checks[key] = False
    _print(
        {
            "ok": all(
                checks[key]
                for key in (
                    "python_supported",
                    "policy_signature",
                    "evidence_chain",
                    "plugin_manifest_json",
                    "hooks_json",
                )
            ),
            "checks": checks,
            "evidence": chain_message,
            "state_dir": str(root),
            "policy_digest": controller.load().digest,
        }
    )
    return 0


def command_codex_run(args: argparse.Namespace) -> int:
    prompt = _prompt(args)
    features = classify_task(prompt)
    controller = PolicyController(_root(args))
    decision = decide(features, controller.load())
    runner = CodexRunner(codex=args.codex)
    result = runner.run(
        prompt,
        cwd=args.cwd,
        route=decision.applied_route,
        sandbox=args.sandbox,
        timeout_seconds=args.timeout,
        output_schema=args.output_schema,
        isolated=not args.include_user_context,
    )
    _print(
        {
            "features": features.to_dict(),
            "decision": decision.to_dict(),
            "execution": result.to_dict(include_answer=args.include_answer),
        }
    )
    return 0 if result.return_code == 0 else result.return_code


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="agp",
        description="Quality-gated agent efficiency.",
    )
    parser.add_argument("--state-dir", help="Local state directory")
    subparsers = parser.add_subparsers(dest="command", required=True)

    classify = subparsers.add_parser("classify")
    classify.add_argument("prompt", nargs="?")
    classify.add_argument("--prompt-file")
    classify.set_defaults(handler=command_classify)

    route = subparsers.add_parser("route")
    route.add_argument("prompt", nargs="?")
    route.add_argument("--prompt-file")
    route.add_argument("--register-shadow", action="store_true")
    route.set_defaults(handler=command_route)

    context = subparsers.add_parser("context")
    context_subparsers = context.add_subparsers(dest="context_command", required=True)
    audit = context_subparsers.add_parser("audit")
    audit.add_argument("paths", nargs="+")
    audit.add_argument("--kind", default="file")
    audit.set_defaults(handler=command_context_audit)

    preflight = subparsers.add_parser("preflight")
    preflight.add_argument("--cwd", default=".")
    preflight.add_argument(
        "kinds",
        nargs="+",
        choices=("inventory", "diff-summary", "result-filter", "schema-check"),
    )
    preflight.set_defaults(handler=command_preflight)

    delegate = subparsers.add_parser("delegate")
    delegate.add_argument("prompt", nargs="?")
    delegate.add_argument("--prompt-file")
    delegate.add_argument("--requested-agents", type=int, default=2)
    delegate.add_argument("--work-items", type=int, required=True)
    delegate.add_argument("--duplicated-context-tokens", type=int, required=True)
    delegate.add_argument("--tokens-per-agent", type=int, required=True)
    delegate.add_argument("--verification-tokens", type=int, default=0)
    delegate.add_argument("--serial-ms", type=int, required=True)
    delegate.add_argument("--parallel-ms", type=int, required=True)
    delegate.add_argument("--max-agents", type=int, default=2)
    delegate.set_defaults(handler=command_delegate)

    ingest = subparsers.add_parser("ingest")
    ingest.add_argument("outcome")
    ingest.set_defaults(handler=command_ingest)

    policy = subparsers.add_parser("policy")
    policy_subparsers = policy.add_subparsers(dest="policy_command", required=True)
    policy_show = policy_subparsers.add_parser("show")
    policy_show.set_defaults(handler=command_policy_show)
    policy_register = policy_subparsers.add_parser("register")
    policy_register.add_argument("bucket")
    policy_register.add_argument("route")
    policy_register.set_defaults(handler=command_policy_register)
    policy_evaluate = policy_subparsers.add_parser("evaluate")
    policy_evaluate.add_argument("bucket")
    policy_evaluate.set_defaults(handler=command_policy_evaluate)
    policy_apply = policy_subparsers.add_parser("apply")
    policy_apply.add_argument("bucket")
    policy_apply.add_argument("--apply", action="store_true")
    policy_apply.set_defaults(handler=command_policy_apply)
    policy_rollback = policy_subparsers.add_parser("rollback")
    policy_rollback.add_argument("bucket")
    policy_rollback.add_argument("reason_code")
    policy_rollback.add_argument("--apply", action="store_true")
    policy_rollback.set_defaults(handler=command_policy_rollback)
    policy_cycle = policy_subparsers.add_parser("cycle")
    policy_cycle.add_argument("--apply", action="store_true")
    policy_cycle.set_defaults(handler=command_policy_cycle)

    evidence = subparsers.add_parser("evidence")
    evidence_subparsers = evidence.add_subparsers(dest="evidence_command", required=True)
    evidence_verify = evidence_subparsers.add_parser("verify")
    evidence_verify.set_defaults(handler=command_evidence_verify)

    benchmark = subparsers.add_parser("benchmark")
    benchmark_subparsers = benchmark.add_subparsers(dest="benchmark_command", required=True)
    benchmark_run = benchmark_subparsers.add_parser("run")
    benchmark_run.add_argument("manifest")
    benchmark_run.add_argument("--output", default="benchmark-results")
    benchmark_run.add_argument("--ingest", action="store_true")
    benchmark_run.add_argument("--retain-outputs", action="store_true")
    benchmark_run.add_argument("--resume")
    benchmark_run.set_defaults(handler=command_benchmark_run)
    benchmark_sanitize = benchmark_subparsers.add_parser("sanitize")
    benchmark_sanitize.add_argument("report")
    benchmark_sanitize.add_argument("--output", required=True)
    benchmark_sanitize.add_argument("--redact-obligation-evidence", action="store_true")
    benchmark_sanitize.set_defaults(handler=command_benchmark_sanitize)

    install_parser = subparsers.add_parser("install")
    install_parser.add_argument("--agents-home", default=str(Path.home() / ".agents"))
    install_parser.add_argument("--apply", action="store_true")
    install_parser.set_defaults(handler=command_install)

    uninstall_parser = subparsers.add_parser("uninstall")
    uninstall_parser.add_argument("--agents-home", default=str(Path.home() / ".agents"))
    uninstall_parser.add_argument("--apply", action="store_true")
    uninstall_parser.set_defaults(handler=command_uninstall)

    doctor = subparsers.add_parser("doctor")
    doctor.set_defaults(handler=command_doctor)

    codex_run = subparsers.add_parser("run")
    codex_run.add_argument("prompt", nargs="?")
    codex_run.add_argument("--prompt-file")
    codex_run.add_argument("--cwd", default=".")
    codex_run.add_argument("--codex")
    codex_run.add_argument(
        "--sandbox",
        choices=("read-only", "workspace-write", "danger-full-access"),
        default="read-only",
    )
    codex_run.add_argument("--timeout", type=int, default=900)
    codex_run.add_argument("--output-schema")
    codex_run.add_argument("--include-user-context", action="store_true")
    codex_run.add_argument("--include-answer", action="store_true")
    codex_run.set_defaults(handler=command_codex_run)
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        return int(args.handler(args))
    except (OSError, ValueError, RuntimeError, KeyError) as error:
        print(f"error: {error}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
