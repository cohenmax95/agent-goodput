from __future__ import annotations

import json
import shutil
import subprocess  # nosec B404
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from .accounting import TokenCounter, best_available_counter


@dataclass(frozen=True)
class PreflightResult:
    kind: str
    ok: bool
    output: str
    output_tokens: int
    token_counter: str
    exact_tokens: bool
    command: tuple[str, ...] | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def _run(
    command: list[str],
    *,
    cwd: Path,
    counter: TokenCounter,
    timeout: int = 20,
) -> PreflightResult:
    # The caller supplies an internal command array and no shell is used.
    completed = subprocess.run(  # nosec B603
        command,
        cwd=cwd,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        timeout=timeout,
        check=False,
    )
    output = completed.stdout.strip()
    return PreflightResult(
        kind=command[0],
        ok=completed.returncode == 0,
        output=output,
        output_tokens=counter.count(output),
        token_counter=counter.name,
        exact_tokens=counter.exact,
        command=tuple(command),
    )


def file_inventory(
    cwd: str | Path,
    *,
    max_files: int = 400,
    counter: TokenCounter | None = None,
) -> PreflightResult:
    root = Path(cwd).expanduser().resolve()
    selected = counter or best_available_counter()
    if shutil.which("rg"):
        result = _run(["rg", "--files", "--hidden", "-g", "!.git"], cwd=root, counter=selected)
        lines = result.output.splitlines()
    else:
        lines = sorted(
            str(path.relative_to(root))
            for path in root.rglob("*")
            if path.is_file() and ".git" not in path.parts
        )
    omitted = max(0, len(lines) - max_files)
    visible = lines[:max_files]
    if omitted:
        visible.append(f"[{omitted} additional files omitted]")
    output = "\n".join(visible)
    return PreflightResult(
        kind="inventory",
        ok=True,
        output=output,
        output_tokens=selected.count(output),
        token_counter=selected.name,
        exact_tokens=selected.exact,
        command=("rg", "--files") if shutil.which("rg") else None,
    )


def diff_summary(
    cwd: str | Path,
    *,
    counter: TokenCounter | None = None,
) -> PreflightResult:
    root = Path(cwd).expanduser().resolve()
    selected = counter or best_available_counter()
    status = _run(
        ["git", "status", "--short", "--untracked-files=all"],
        cwd=root,
        counter=selected,
    )
    stats = _run(["git", "diff", "--stat"], cwd=root, counter=selected)
    staged = _run(["git", "diff", "--cached", "--stat"], cwd=root, counter=selected)
    output = "\n".join(
        part
        for part in (
            "[status]\n" + status.output if status.output else "",
            "[working tree]\n" + stats.output if stats.output else "",
            "[staged]\n" + staged.output if staged.output else "",
        )
        if part
    )
    if not output:
        output = "clean tracked worktree"
    return PreflightResult(
        kind="diff-summary",
        ok=status.ok and stats.ok and staged.ok,
        output=output,
        output_tokens=selected.count(output),
        token_counter=selected.name,
        exact_tokens=selected.exact,
        command=("git", "status/diff"),
    )


def filter_result_output(
    text: str,
    *,
    context_lines: int = 2,
    max_matches: int = 40,
) -> str:
    lines = text.splitlines()
    needles = (
        "error",
        "failed",
        "failure",
        "exception",
        "traceback",
        "warning",
        "assert",
        "panic",
    )
    selected: set[int] = set()
    for index, line in enumerate(lines):
        if any(needle in line.casefold() for needle in needles):
            selected.update(
                range(max(0, index - context_lines), min(len(lines), index + context_lines + 1))
            )
            if len(selected) >= max_matches * (context_lines * 2 + 1):
                break
    if not selected:
        tail = lines[-min(20, len(lines)) :]
        return "\n".join(tail)
    output: list[str] = []
    prior = -2
    for index in sorted(selected):
        if index > prior + 1:
            output.append("…")
        output.append(lines[index])
        prior = index
    return "\n".join(output)


def validate_json_files(
    paths: list[str | Path],
    *,
    counter: TokenCounter | None = None,
) -> PreflightResult:
    selected = counter or best_available_counter()
    results: list[str] = []
    ok = True
    for raw_path in paths:
        path = Path(raw_path).expanduser().resolve()
        try:
            with path.open(encoding="utf-8") as stream:
                json.load(stream)
            results.append(f"PASS {path.name}")
        except (OSError, json.JSONDecodeError) as error:
            ok = False
            results.append(f"FAIL {path.name}: {error}")
    output = "\n".join(results)
    return PreflightResult(
        kind="schema-check",
        ok=ok,
        output=output,
        output_tokens=selected.count(output),
        token_counter=selected.name,
        exact_tokens=selected.exact,
    )


def run_preflight(
    cwd: str | Path,
    kinds: list[str] | tuple[str, ...],
) -> list[PreflightResult]:
    results: list[PreflightResult] = []
    for kind in dict.fromkeys(kinds):
        if kind == "inventory":
            results.append(file_inventory(cwd))
        elif kind == "diff-summary":
            results.append(diff_summary(cwd))
        elif kind == "result-filter":
            counter = best_available_counter()
            log_paths = sorted(Path(cwd).rglob("*.log"))[:5]
            sections: list[str] = []
            for path in log_paths:
                filtered = filter_result_output(path.read_text(encoding="utf-8", errors="replace"))
                sections.append(f"[{path.relative_to(Path(cwd))}]\n{filtered}")
            output = "\n\n".join(sections) if sections else "no .log files found"
            results.append(
                PreflightResult(
                    kind="result-filter",
                    ok=True,
                    output=output,
                    output_tokens=counter.count(output),
                    token_counter=counter.name,
                    exact_tokens=counter.exact,
                )
            )
        elif kind == "schema-check":
            json_paths = sorted(Path(cwd).glob("*.json"))
            results.append(validate_json_files(list(json_paths)))
        else:
            raise ValueError(f"unknown preflight kind: {kind}")
    return results
