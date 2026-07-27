from __future__ import annotations

import json
import re
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Literal

from .accounting import TokenCounter, best_available_counter
from .util import sha256_text


@dataclass(frozen=True)
class ContextItem:
    label: str
    kind: str
    text: str
    priority: int = 50
    requirement: Literal["required", "conditional", "optional"] = "conditional"
    source: str | None = None


@dataclass(frozen=True)
class ContextCost:
    label: str
    kind: str
    source: str | None
    characters: int
    bytes: int
    tokens: int
    counter: str
    exact: bool
    digest: str


@dataclass(frozen=True)
class CompiledContext:
    packet: str
    selected: tuple[ContextCost, ...]
    omitted: tuple[ContextCost, ...]
    duplicate_lines_removed: int
    token_budget: int
    used_tokens: int
    counter: str
    exact: bool

    def to_dict(self) -> dict[str, object]:
        return {
            "packet": self.packet,
            "selected": [asdict(item) for item in self.selected],
            "omitted": [asdict(item) for item in self.omitted],
            "duplicate_lines_removed": self.duplicate_lines_removed,
            "token_budget": self.token_budget,
            "used_tokens": self.used_tokens,
            "counter": self.counter,
            "exact": self.exact,
        }


def _cost(item: ContextItem, counter: TokenCounter) -> ContextCost:
    raw = item.text.encode("utf-8")
    return ContextCost(
        label=item.label,
        kind=item.kind,
        source=item.source,
        characters=len(item.text),
        bytes=len(raw),
        tokens=counter.count(item.text),
        counter=counter.name,
        exact=counter.exact,
        digest=sha256_text(item.text),
    )


def audit_paths(
    paths: list[str | Path] | tuple[str | Path, ...],
    *,
    kind: str = "file",
    counter: TokenCounter | None = None,
) -> list[ContextCost]:
    selected = counter or best_available_counter()
    costs: list[ContextCost] = []
    for raw_path in paths:
        path = Path(raw_path).expanduser().resolve()
        text = path.read_text(encoding="utf-8", errors="replace")
        costs.append(
            _cost(
                ContextItem(
                    label=path.name,
                    kind=kind,
                    text=text,
                    source=str(path),
                ),
                selected,
            )
        )
    return costs


def _deduplicate_lines(text: str, seen: set[str]) -> tuple[str, int]:
    output: list[str] = []
    removed = 0
    in_fence = False
    for line in text.splitlines():
        if line.strip().startswith("```"):
            in_fence = not in_fence
        normalized = re.sub(r"\s+", " ", line.strip()).casefold()
        if not normalized or in_fence:
            output.append(line)
            continue
        digest = sha256_text(normalized)
        if digest in seen:
            removed += 1
            continue
        seen.add(digest)
        output.append(line)
    return "\n".join(output).strip(), removed


def compile_context(
    items: list[ContextItem] | tuple[ContextItem, ...],
    *,
    token_budget: int,
    counter: TokenCounter | None = None,
) -> CompiledContext:
    if token_budget <= 0:
        raise ValueError("token_budget must be positive")
    selected_counter = counter or best_available_counter()
    ordered = sorted(
        enumerate(items),
        key=lambda pair: (
            {"required": 0, "conditional": 1, "optional": 2}[pair[1].requirement],
            pair[1].priority,
            pair[0],
        ),
    )
    selected_costs: list[ContextCost] = []
    omitted_costs: list[ContextCost] = []
    sections: list[str] = []
    seen_lines: set[str] = set()
    removed = 0
    used = 0

    for _, item in ordered:
        deduplicated, duplicate_count = _deduplicate_lines(item.text, seen_lines)
        removed += duplicate_count
        if not deduplicated:
            continue
        section = f"## {item.label}\n\n{deduplicated}"
        section_tokens = selected_counter.count(section)
        item_cost = _cost(
            ContextItem(
                label=item.label,
                kind=item.kind,
                text=deduplicated,
                priority=item.priority,
                requirement=item.requirement,
                source=item.source,
            ),
            selected_counter,
        )
        if used + section_tokens <= token_budget:
            sections.append(section)
            selected_costs.append(item_cost)
            used += section_tokens
            continue
        if item.requirement == "required":
            raise ValueError(f"required context '{item.label}' exceeds the remaining token budget")
        omitted_costs.append(item_cost)

    return CompiledContext(
        packet="\n\n".join(sections).strip(),
        selected=tuple(selected_costs),
        omitted=tuple(omitted_costs),
        duplicate_lines_removed=removed,
        token_budget=token_budget,
        used_tokens=used,
        counter=selected_counter.name,
        exact=selected_counter.exact,
    )


def costs_as_json(costs: list[ContextCost]) -> str:
    return json.dumps([asdict(item) for item in costs], indent=2, sort_keys=True)
