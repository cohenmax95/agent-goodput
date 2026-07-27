from __future__ import annotations

import json
import os
import shutil
import subprocess  # nosec B404
import tempfile
import time
from collections import Counter
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .models import Route, TokenUsage
from .util import sha256_text

_DEFAULT_DISABLED_FEATURES = (
    "apps",
    "browser_use",
    "chronicle",
    "hooks",
    "image_generation",
    "in_app_browser",
    "multi_agent",
    "plugins",
    "skill_search",
)


@dataclass(frozen=True)
class CodexExecution:
    route: Route
    runtime_version: str
    return_code: int
    elapsed_ms: int
    usage: TokenUsage
    answer: str
    answer_sha256: str
    stderr_sha256: str
    event_count: int
    event_types: dict[str, int]
    item_types: dict[str, int]
    item_events: dict[str, dict[str, int]]
    timed_out: bool = False

    def to_dict(self, *, include_answer: bool = False) -> dict[str, Any]:
        value = {
            "route": self.route.to_dict(),
            "runtime_version": self.runtime_version,
            "return_code": self.return_code,
            "elapsed_ms": self.elapsed_ms,
            "usage": self.usage.to_dict(),
            "answer_sha256": self.answer_sha256,
            "answer_bytes": len(self.answer.encode("utf-8")),
            "stderr_sha256": self.stderr_sha256,
            "event_count": self.event_count,
            "event_types": self.event_types,
            "item_types": self.item_types,
            "item_events": self.item_events,
            "timed_out": self.timed_out,
        }
        if include_answer:
            value["answer"] = self.answer
        return value


def find_codex(explicit: str | Path | None = None) -> Path:
    candidates: list[Path] = []
    if explicit:
        candidates.append(Path(explicit).expanduser())
    if os.environ.get("CODEX_BINARY"):
        candidates.append(Path(os.environ["CODEX_BINARY"]).expanduser())
    found = shutil.which("codex")
    if found:
        candidates.append(Path(found))
    candidates.extend(
        (
            Path("/Applications/Codex.app/Contents/Resources/codex"),
            Path("/Applications/ChatGPT.app/Contents/Resources/codex"),
        )
    )
    for candidate in candidates:
        resolved = candidate.resolve()
        if resolved.is_file() and os.access(resolved, os.X_OK):
            return resolved
    raise FileNotFoundError("Codex CLI was not found; pass --codex or set CODEX_BINARY")


def _decode_stream(value: str | bytes | None) -> str:
    if isinstance(value, bytes):
        return value.decode("utf-8", errors="replace")
    return value or ""


def parse_codex_events(
    stdout: str,
) -> tuple[
    TokenUsage,
    int,
    dict[str, int],
    dict[str, int],
    dict[str, dict[str, int]],
]:
    usage: dict[str, int] = {}
    event_types: Counter[str] = Counter()
    item_types: Counter[str] = Counter()
    item_events: dict[str, Counter[str]] = {}
    event_count = 0
    for line in stdout.splitlines():
        try:
            event = json.loads(line)
        except json.JSONDecodeError:
            continue
        if not isinstance(event, dict):
            continue
        event_count += 1
        event_type = event.get("type")
        if isinstance(event_type, str):
            event_types[event_type] += 1
        item = event.get("item")
        if isinstance(item, dict) and isinstance(item.get("type"), str):
            item_type = str(item["type"])
            item_types[item_type] += 1
            if isinstance(event_type, str):
                item_events.setdefault(event_type, Counter())[item_type] += 1
        raw_usage = event.get("usage")
        if isinstance(raw_usage, dict):
            found = {
                key: int(value)
                for key in (
                    "input_tokens",
                    "cached_input_tokens",
                    "output_tokens",
                    "reasoning_tokens",
                    "model_calls",
                )
                if isinstance((value := raw_usage.get(key)), int)
            }
            if found:
                usage = found
    model_calls_reported = "model_calls" in usage
    return (
        TokenUsage(
            input_tokens=usage.get("input_tokens", 0),
            cached_input_tokens=usage.get("cached_input_tokens", 0),
            output_tokens=usage.get("output_tokens", 0),
            reasoning_tokens=usage.get("reasoning_tokens", 0),
            calls=usage.get("model_calls", 1),
            call_count_source=("codex:model_calls" if model_calls_reported else "agent-run"),
            source="codex" if usage else "missing",
        ),
        event_count,
        dict(sorted(event_types.items())),
        dict(sorted(item_types.items())),
        {event: dict(sorted(counts.items())) for event, counts in sorted(item_events.items())},
    )


class CodexRunner:
    def __init__(
        self,
        *,
        codex: str | Path | None = None,
        auth_home: str | Path | None = None,
    ) -> None:
        self.codex = find_codex(codex)
        self.runtime_version = self._version()
        self.auth_home = (
            Path(auth_home).expanduser().resolve() if auth_home else Path.home() / ".codex"
        )

    def _version(self) -> str:
        # The Codex binary is resolved locally and receives fixed arguments.
        completed = subprocess.run(  # nosec B603
            [str(self.codex), "--version"],
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            timeout=5,
            check=False,
        )
        value = completed.stdout.strip()
        return value if completed.returncode == 0 and value else "unknown"

    def _isolated_home(self, parent: Path) -> Path:
        home = parent / "codex-home"
        home.mkdir(parents=True, exist_ok=True)
        auth_source = self.auth_home / "auth.json"
        auth_target = home / "auth.json"
        if auth_source.exists() and not auth_target.exists():
            auth_target.symlink_to(auth_source)
        return home

    def run(
        self,
        prompt: str,
        *,
        cwd: str | Path,
        route: Route,
        sandbox: str = "read-only",
        timeout_seconds: int = 900,
        output_schema: str | Path | None = None,
        isolated: bool = True,
        disabled_features: tuple[str, ...] = _DEFAULT_DISABLED_FEATURES,
    ) -> CodexExecution:
        workspace = Path(cwd).expanduser().resolve()
        with tempfile.TemporaryDirectory(prefix="agent-goodput-codex-") as temporary:
            scratch = Path(temporary)
            answer_path = scratch / "answer.txt"
            command = [
                str(self.codex),
                "exec",
                "--json",
                "--ephemeral",
                "--strict-config",
                "--skip-git-repo-check",
                "--sandbox",
                sandbox,
                "--cd",
                str(workspace),
                "--model",
                route.model,
                "--config",
                f'model_reasoning_effort="{route.reasoning_effort}"',
                "--config",
                'model_verbosity="low"',
                "--config",
                "notify=[]",
                "--config",
                'approval_policy="never"',
            ]
            for feature in disabled_features:
                command.extend(["--disable", feature])
            if isolated:
                command.extend(
                    [
                        "--ignore-user-config",
                        "--ignore-rules",
                        "--config",
                        "project_doc_max_bytes=0",
                    ]
                )
            if output_schema is not None:
                command.extend(["--output-schema", str(Path(output_schema).resolve())])
            command.extend(["--output-last-message", str(answer_path), "-"])
            environment = os.environ.copy()
            if isolated:
                environment["CODEX_HOME"] = str(self._isolated_home(scratch))
            started = time.monotonic()
            timed_out = False
            try:
                # The fixed Codex command uses an argument array and no shell.
                completed = subprocess.run(  # nosec B603
                    command,
                    input=prompt,
                    text=True,
                    capture_output=True,
                    timeout=timeout_seconds,
                    env=environment,
                    check=False,
                )
                stdout = completed.stdout
                stderr = completed.stderr
                return_code = completed.returncode
            except subprocess.TimeoutExpired as error:
                timed_out = True
                stdout = _decode_stream(error.stdout)
                stderr = _decode_stream(error.stderr)
                return_code = 124
            elapsed_ms = int((time.monotonic() - started) * 1_000)
            answer = answer_path.read_text(encoding="utf-8") if answer_path.exists() else ""
            (
                usage,
                event_count,
                event_types,
                item_types,
                item_events,
            ) = parse_codex_events(stdout)
            return CodexExecution(
                route=route,
                runtime_version=self.runtime_version,
                return_code=return_code,
                elapsed_ms=elapsed_ms,
                usage=usage,
                answer=answer,
                answer_sha256=sha256_text(answer),
                stderr_sha256=sha256_text(stderr),
                event_count=event_count,
                event_types=event_types,
                item_types=item_types,
                item_events=item_events,
                timed_out=timed_out,
            )
