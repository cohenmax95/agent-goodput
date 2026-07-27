from __future__ import annotations

import json
import re
from dataclasses import asdict, dataclass
from pathlib import Path, PurePosixPath

from .models import ObligationResult
from .util import sha256_bytes, write_json

_MISSING_PATH_ONLY = re.compile(r"^missing evidence path:\s*(.+)$")
_MISSING_FACT_ONLY = re.compile(r"^missing evidence fact:\s*(.+)$")
_TOKEN = re.compile(r"[A-Za-z_][A-Za-z0-9_.-]{2,}|\d+(?:\.\d+)+")
_BACKTICK = re.compile(r"`([^`\n]{1,120})`")
_LINE_CITATION = re.compile(r"(?:#L\d+(?:-L?\d+)?|:L?\d+(?::\d+)?(?:-\d+)?)$")
_MAX_CERTIFICATE_CHARS = 280
_COMMON_TERMS = {
    "answer",
    "before",
    "claim",
    "complete",
    "conclusion",
    "deterministic",
    "evidence",
    "exact",
    "fact",
    "file",
    "implementation",
    "include",
    "missing",
    "path",
    "required",
    "source",
    "state",
    "task",
    "test",
    "tests",
    "verification",
}


@dataclass(frozen=True)
class CompletionResult:
    applied: bool
    completed: bool
    reason_code: str
    requested_path_count: int
    requested_fact_count: int
    added_path_count: int
    certificate_count: int
    matched_line_count: int
    matched_fact_count: int
    answer_before_sha256: str
    answer_after_sha256: str

    def to_dict(self) -> dict[str, object]:
        return asdict(self)


@dataclass(frozen=True)
class EvidenceGaps:
    paths: tuple[str, ...]
    facts: tuple[str, ...]


def repairable_evidence_gaps(
    obligations: tuple[ObligationResult, ...],
) -> EvidenceGaps | None:
    """Return missing paths and facts only when every failure is a lexical evidence gap."""
    failed = [item for item in obligations if not item.passed]
    if not failed:
        return EvidenceGaps(paths=(), facts=())
    paths: list[str] = []
    facts: list[str] = []
    for obligation in failed:
        evidence = obligation.evidence or ""
        segments = [item.strip() for item in evidence.split(";")[1:] if item.strip()]
        if not segments:
            return None
        for segment in segments:
            path_match = _MISSING_PATH_ONLY.fullmatch(segment)
            if path_match is not None:
                paths.append(path_match.group(1).strip())
                continue
            fact_match = _MISSING_FACT_ONLY.fullmatch(segment)
            if fact_match is not None:
                facts.append(fact_match.group(1).strip())
                continue
            return None
    normalized_paths = tuple(dict.fromkeys(path for path in paths if path))
    normalized_facts = tuple(dict.fromkeys(fact for fact in facts if fact))
    if not normalized_paths and not normalized_facts:
        return None
    return EvidenceGaps(paths=normalized_paths, facts=normalized_facts)


def missing_evidence_paths_only(
    obligations: tuple[ObligationResult, ...],
) -> tuple[str, ...] | None:
    """Return verifier-reported paths only when every failure is path-only."""
    gaps = repairable_evidence_gaps(obligations)
    if gaps is None:
        return None
    if gaps.facts:
        return None
    if not gaps.paths:
        return ()
    return gaps.paths


def _query_terms(*values: str) -> tuple[str, ...]:
    preferred: list[str] = []
    for value in values:
        for span in _BACKTICK.findall(value):
            preferred.extend(_TOKEN.findall(span))
    all_tokens = preferred[:]
    for value in values:
        all_tokens.extend(_TOKEN.findall(value))

    selected: list[str] = []
    seen: set[str] = set()
    preferred_casefold = {item.casefold() for item in preferred}
    for token in all_tokens:
        folded = token.casefold()
        if folded in seen or folded in _COMMON_TERMS:
            continue
        distinctive = (
            folded in preferred_casefold
            or "_" in token
            or "." in token
            or "-" in token
            or any(character.isdigit() for character in token)
            or (
                any(character.islower() for character in token)
                and any(character.isupper() for character in token)
            )
            or token.isupper()
        )
        if len(token) < 4 and not any(character.isdigit() for character in token):
            continue
        if not distinctive:
            continue
        seen.add(folded)
        selected.append(token)
        if len(selected) >= 128:
            break
    return tuple(selected)


def _safe_source_file(
    workspace: Path,
    raw_path: str,
    *,
    max_file_bytes: int,
) -> tuple[Path, str] | None:
    normalized = raw_path.strip().replace("\\", "/").removeprefix("./")
    relative = PurePosixPath(normalized)
    if relative.is_absolute() or not relative.parts or ".." in relative.parts:
        return None
    candidate = workspace.joinpath(*relative.parts)
    current = workspace
    for part in relative.parts:
        current /= part
        if current.is_symlink():
            return None
    resolved = candidate.resolve()
    try:
        resolved.relative_to(workspace)
    except ValueError:
        return None
    if not resolved.is_file() or resolved.stat().st_size > max_file_bytes:
        return None
    return resolved, relative.as_posix()


def _ranked_matching_lines(
    text: str,
    terms: tuple[str, ...],
) -> list[tuple[int, str, int]]:
    ranked: list[tuple[int, int, str, int]] = []
    folded_terms = tuple((term, term.casefold()) for term in terms)
    for line_number, raw_line in enumerate(text.splitlines(), start=1):
        line = " ".join(raw_line.strip().split())
        if not line:
            continue
        folded_line = line.casefold()
        matched = [term for term, folded in folded_terms if folded in folded_line]
        if not matched:
            continue
        score = len(set(item.casefold() for item in matched))
        ranked.append((score, -line_number, line, line_number))
    return [
        (line_number, line, score) for score, _, line, line_number in sorted(ranked, reverse=True)
    ]


def complete_missing_evidence_paths(
    *,
    workspace: str | Path,
    answer_file: str | Path,
    missing_paths: tuple[str, ...],
    missing_facts: tuple[str, ...] = (),
    task_text: str,
    max_files: int = 8,
    max_facts: int = 8,
    max_fact_chars: int = 80,
    max_fact_total_chars: int = 160,
    max_file_bytes: int = 262_144,
    max_answer_bytes: int = 262_144,
) -> CompletionResult:
    """Append bounded certificates for verifier-reported lexical evidence gaps."""
    root = Path(workspace).expanduser().resolve()
    answer_path = Path(answer_file)
    if not answer_path.is_absolute():
        answer_path = root / answer_path
    if answer_path.is_symlink():
        return CompletionResult(
            applied=False,
            completed=False,
            reason_code="unsafe-answer-path",
            requested_path_count=len(missing_paths),
            requested_fact_count=len(missing_facts),
            added_path_count=0,
            certificate_count=0,
            matched_line_count=0,
            matched_fact_count=0,
            answer_before_sha256=sha256_bytes(b""),
            answer_after_sha256=sha256_bytes(b""),
        )
    answer_path = answer_path.resolve()
    try:
        answer_path.relative_to(root)
    except ValueError:
        return CompletionResult(
            applied=False,
            completed=False,
            reason_code="unsafe-answer-path",
            requested_path_count=len(missing_paths),
            requested_fact_count=len(missing_facts),
            added_path_count=0,
            certificate_count=0,
            matched_line_count=0,
            matched_fact_count=0,
            answer_before_sha256=sha256_bytes(b""),
            answer_after_sha256=sha256_bytes(b""),
        )
    before_bytes = answer_path.read_bytes() if answer_path.is_file() else b""
    before_hash = sha256_bytes(before_bytes)

    def result(
        reason: str,
        *,
        applied: bool = False,
        completed: bool = False,
        added_paths: int = 0,
        certificates: int = 0,
        matches: int = 0,
        matched_facts: int = 0,
        after_hash: str | None = None,
    ) -> CompletionResult:
        return CompletionResult(
            applied=applied,
            completed=completed,
            reason_code=reason,
            requested_path_count=len(missing_paths),
            requested_fact_count=len(missing_facts),
            added_path_count=added_paths,
            certificate_count=certificates,
            matched_line_count=matches,
            matched_fact_count=matched_facts,
            answer_before_sha256=before_hash,
            answer_after_sha256=after_hash or before_hash,
        )

    if not missing_paths and not missing_facts:
        return result("no-evidence-gaps")
    if (
        max_files <= 0
        or len(missing_paths) > max_files
        or max_facts < 0
        or len(missing_facts) > max_facts
        or max_fact_chars <= 0
        or any(len(fact) > max_fact_chars for fact in missing_facts)
        or max_fact_total_chars < 0
        or sum(len(fact) for fact in missing_facts) > max_fact_total_chars
        or max_file_bytes <= 0
        or max_answer_bytes <= 0
        or len(before_bytes) > max_answer_bytes
    ):
        return result("limit-exceeded")
    try:
        loaded = json.loads(before_bytes)
    except (json.JSONDecodeError, UnicodeDecodeError):
        return result("invalid-answer")
    if not isinstance(loaded, dict):
        return result("invalid-answer")
    evidence = loaded.get("evidence")
    if not isinstance(evidence, list) or not all(isinstance(item, dict) for item in evidence):
        return result("invalid-answer")
    query_values = [
        task_text,
        str(loaded.get("conclusion", "")),
        *(str(item.get("fact", "")) for item in evidence),
    ]
    trusted_text = "\n".join(query_values).casefold()
    if any(fact.casefold() not in trusted_text for fact in missing_facts):
        return result("untrusted-missing-fact")
    terms = _query_terms(*query_values)
    if not terms and not missing_facts:
        return result("no-query-terms")

    def normalize_path(raw_path: str) -> str:
        normalized = raw_path.strip().replace("\\", "/").removeprefix("./")
        return _LINE_CITATION.sub("", normalized)

    existing_path_list = tuple(
        dict.fromkeys(
            normalize_path(str(item.get("path", "")))
            for item in evidence
            if str(item.get("path", "")).strip()
        )
    )
    required_paths = tuple(dict.fromkeys(normalize_path(path) for path in missing_paths))
    source_candidates = tuple(dict.fromkeys((*required_paths, *existing_path_list)))
    if not source_candidates:
        return result("no-source-paths")
    if len(source_candidates) > max_files:
        return result("limit-exceeded")

    additions: list[dict[str, str]] = []
    added_required_paths: set[str] = set()
    matched_line_count = 0
    matched_facts: set[str] = set()
    existing_paths = set(existing_path_list)
    required_path_set = set(required_paths)
    for raw_path in source_candidates:
        required_new_path = raw_path in required_path_set and raw_path not in existing_paths
        source = _safe_source_file(root, raw_path, max_file_bytes=max_file_bytes)
        if source is None:
            if required_new_path:
                return result("unsafe-or-missing-path", applied=True)
            continue
        source_path, relative_path = source
        text = source_path.read_text(encoding="utf-8", errors="replace")
        ranked_lines = _ranked_matching_lines(text, terms)
        selected: list[tuple[int, str, int]] = []
        for fact in missing_facts:
            if fact.casefold() in matched_facts:
                continue
            all_lines = (
                (line_number, " ".join(raw_line.strip().split()), 0)
                for line_number, raw_line in enumerate(text.splitlines(), start=1)
            )
            fact_line = next(
                (item for item in all_lines if item[1] and fact.casefold() in item[1].casefold()),
                None,
            )
            if fact_line is not None and fact_line not in selected:
                selected.append(fact_line)
                matched_facts.add(fact.casefold())
        if required_new_path and not selected and ranked_lines:
            selected.append(ranked_lines[0])
        if not selected:
            if required_new_path:
                return result("no-source-match", applied=True)
            continue
        digest = sha256_bytes(source_path.read_bytes())[:12]
        line_note = ",".join(f"L{line_number}" for line_number, _, _ in selected)
        facts_in_source = [
            fact
            for fact in missing_facts
            if any(fact.casefold() in line.casefold() for _, line, _ in selected)
        ]
        matched_terms = tuple(
            dict.fromkeys(
                term
                for _, line, _ in selected
                for term in terms
                if term.casefold() in line.casefold()
            )
        )
        safe_terms = ",".join(term[:64] for term in matched_terms[:8])
        literal_note = f" verified_literals={','.join(facts_in_source)};" if facts_in_source else ""
        certificate = (
            f"Deterministic source certificate sha256={digest};"
            f"{literal_note} lines={line_note}; matched_terms={safe_terms}"
        )
        if len(certificate) > _MAX_CERTIFICATE_CHARS:
            return result("certificate-too-large", applied=True)
        additions.append({"path": relative_path, "fact": certificate})
        if required_new_path:
            added_required_paths.add(relative_path)
        matched_line_count += len(selected)

    unresolved_paths = required_path_set - existing_paths - added_required_paths
    if unresolved_paths:
        return result("missing-path-not-in-source", applied=True)
    if len(matched_facts) != len({fact.casefold() for fact in missing_facts}):
        return result("missing-fact-not-in-source", applied=True)

    if not additions:
        return result("already-present", applied=True, completed=True)
    if len(evidence) + len(additions) > 8:
        return result("evidence-capacity", applied=True)
    updated = dict(loaded)
    updated["evidence"] = [*evidence, *additions]
    write_json(answer_path, updated, mode=0o644)
    after_hash = sha256_bytes(answer_path.read_bytes())
    return result(
        "completed",
        applied=True,
        completed=True,
        added_paths=len(added_required_paths),
        certificates=len(additions),
        matches=matched_line_count,
        matched_facts=len(matched_facts),
        after_hash=after_hash,
    )
