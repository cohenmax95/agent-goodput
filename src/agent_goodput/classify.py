from __future__ import annotations

import re
from collections.abc import Iterable

from .accounting import TokenCounter, best_available_counter
from .models import RiskLevel, TaskFeatures
from .util import sha256_text

_PATTERNS: dict[str, tuple[str, ...]] = {
    "external": (
        r"\bsend\b",
        r"\bpublish\b",
        r"\bpush\b",
        r"\bdeploy\b",
        r"\bmerge\b",
        r"\bemail\b",
        r"\btext\b",
        r"\bpost\b",
        r"\bsubmit\b",
        r"\btransfer\b",
        r"\bpay\b",
    ),
    "destructive": (
        r"\bdelete\b",
        r"\bremove\b",
        r"\bdrop\b",
        r"\boverwrite\b",
        r"\breset\b",
        r"\btruncate\b",
        r"\bforce[- ]?push\b",
    ),
    "sensitive": (
        r"\bcredential",
        r"\bsecret",
        r"\bapi[-_ ]?key",
        r"\bpassword",
        r"\b(?:access|api|auth|bearer|session)[-_ ]?token\b",
        r"\bpii\b",
        r"\bprivate\b",
        r"\bmedical\b",
        r"\blegal\b",
        r"\bfinancial\b",
    ),
    "high_risk": (
        r"\bsecurity\b",
        r"\bvulnerabilit",
        r"\bexploit",
        r"\bpath traversal\b",
        r"\binjection\b",
        r"\bauthori[sz]ation\b",
        r"\bpermissions?\b",
        r"\bhigh[- ]stakes\b",
        r"\bcash[- ]to[- ]close\b",
        r"\bclosing statement\b",
        r"\bsettlement statement\b",
        r"\b(?:commercial|real[- ]estate|property)\s+closing\b",
        r"\bclosing\s+(?:date|documents?|package|instructions?|scheduled|on\s+\w+)",
        r"\b(?:purchase|sale)\s+contract\b",
        r"\b(?:signed|executed)\s+(?:contract|agreement|addendum|psa)\b",
        r"\btitle\s+(?:commitment|policy|issue|exception)\b",
        r"\bescrow\b",
        r"\b1031(?:\s+exchange)?\b",
        r"\bwire amount\b",
        r"\bwire (?:instructions?|funds?)\b",
        r"\bloan commitment\b",
        r"\bprobate\b",
    ),
    "read_only": (
        r"\bscan\b",
        r"\bread\b",
        r"\binspect\b",
        r"\breview\b",
        r"\baudit\b",
        r"\bresearch\b",
        r"\bfind\b",
        r"\bsummar",
        r"\bexplain\b",
        r"\bdiagnos",
    ),
    "local_write": (
        r"\bedit\b",
        r"\bfix\b",
        r"\bimplement\b",
        r"\bbuild\b",
        r"\bcreate\b",
        r"\brefactor\b",
        r"\bupdate\b",
        r"\bchange\b",
    ),
    "quality": (
        r"\bbest\b",
        r"\bdeep\b",
        r"\bcareful",
        r"\bthorough",
        r"\babsolute\b",
        r"\bhigh[- ]stakes\b",
        r"\bfrontier\b",
        r"\bwithout diminishing\b",
        r"\bmaintain(?:ing)? quality\b",
    ),
    "verification": (
        r"\btest\b",
        r"\bverify\b",
        r"\bvalidate\b",
        r"\bbenchmark\b",
        r"\bproof\b",
        r"\bcitation",
        r"\bevidence\b",
        r"\bcheck\b",
    ),
}

_TASK_KINDS: tuple[tuple[str, tuple[str, ...]], ...] = (
    ("diagnosis", (r"\bbug\b", r"\berror\b", r"\bfail", r"\bdiagnos", r"\blog\b")),
    ("research", (r"\bresearch\b", r"\bscan\b", r"\bcompare\b", r"\baudit\b")),
    ("code", (r"\bcode\b", r"\bimplement\b", r"\bfix\b", r"\brefactor\b", r"\bcli\b")),
    ("writing", (r"\bdraft\b", r"\bwrite\b", r"\bcopy\b", r"\bemail\b", r"\bpost\b")),
    ("operations", (r"\bdeploy\b", r"\bpublish\b", r"\bsend\b", r"\bproduction\b")),
    ("planning", (r"\bplan\b", r"\bstrategy\b", r"\bdesign\b", r"\barchitect")),
)

_NEGATION_TAIL = re.compile(
    r"(?:"
    r"\b(?:do|does|did|must|should|can|could|will|would)\s+not"
    r"|\b(?:don't|doesn't|didn't|mustn't|shouldn't|can't|cannot|couldn't|won't|wouldn't)\b"
    r"|\bnever\b"
    r"|\bwithout\b"
    r"|\bno"
    r")\s+(?:[\w'-]+\s+){0,3}$",
    re.I,
)
_NEGATION_CUE = re.compile(
    r"\b(?:"
    r"(?:do|does|did|must|should|can|could|will|would)\s+not"
    r"|don't|doesn't|didn't|mustn't|shouldn't|can't|cannot|couldn't|won't|wouldn't"
    r"|never"
    r")\b",
    re.I,
)


def _positive_match(text: str, pattern: str) -> bool:
    for match in re.finditer(pattern, text, re.I):
        prefix = text[max(0, match.start() - 80) : match.start()]
        if _NEGATION_TAIL.search(prefix):
            continue
        clause_start = max(
            text.rfind(".", 0, match.start()),
            text.rfind(";", 0, match.start()),
            text.rfind("\n", 0, match.start()),
        )
        clause_prefix = text[clause_start + 1 : match.start()]
        cue_matches = list(_NEGATION_CUE.finditer(clause_prefix))
        if cue_matches:
            after_cue = clause_prefix[cue_matches[-1].end() :]
            coordinated = "," in after_cue or bool(re.search(r"\b(?:and|or)\s+$", after_cue, re.I))
            boundary = re.search(
                r"\b(?:but|except|however|then)\b",
                after_cue,
                re.I,
            )
            if coordinated and not boundary:
                continue
        return True
    return False


def _matches(
    text: str,
    category: str,
    *,
    honor_negation: bool = True,
) -> list[str]:
    if not honor_negation:
        return [pattern for pattern in _PATTERNS[category] if re.search(pattern, text, re.I)]
    return [pattern for pattern in _PATTERNS[category] if _positive_match(text, pattern)]


def _task_kind(text: str) -> str:
    scored = [
        (sum(_positive_match(text, pattern) for pattern in patterns), name)
        for name, patterns in _TASK_KINDS
    ]
    score, name = max(scored)
    return name if score else "general"


def _clamp(value: float) -> float:
    return max(0.0, min(1.0, value))


def classify_task(
    prompt: str,
    *,
    counter: TokenCounter | None = None,
    extra_risk_signals: Iterable[str] = (),
) -> TaskFeatures:
    selected_counter = counter or best_available_counter()
    normalized = " ".join(prompt.split())
    external = _matches(normalized, "external")
    destructive = _matches(normalized, "destructive")
    sensitive = _matches(normalized, "sensitive", honor_negation=False)
    high_risk = _matches(normalized, "high_risk", honor_negation=False)
    local_write = _matches(normalized, "local_write")
    quality = _matches(normalized, "quality")
    verification = _matches(normalized, "verification")

    risk = RiskLevel.LOW
    reasons: list[str] = []
    if local_write:
        risk = RiskLevel.MEDIUM
        reasons.append("local mutation requested")
    if external or sensitive or high_risk:
        risk = max(risk, RiskLevel.HIGH)
        if external or sensitive:
            reasons.append("external or sensitive action detected")
        if high_risk:
            reasons.append("high-stakes or security-sensitive work detected")
    if destructive and (external or re.search(r"\b(prod|production)\b", normalized, re.I)):
        risk = RiskLevel.CRITICAL
        reasons.append("destructive production-capable action detected")
    elif destructive:
        risk = max(risk, RiskLevel.HIGH)
        reasons.append("destructive language detected")
    if extra_risk_signals:
        risk = max(risk, RiskLevel.HIGH)
        reasons.extend(f"risk signal: {item}" for item in extra_risk_signals)

    write_scope: str = "none"
    if local_write:
        write_scope = "local"
    if external:
        write_scope = "external"

    words = re.findall(r"\b[\w'-]+\b", normalized)
    clauses = len(re.findall(r"[,;:]|\b(?:and|then|also|plus)\b", normalized, re.I))
    requested_steps = len(re.findall(r"(?:^|\n)\s*(?:[-*]|\d+[.)])\s+", prompt))
    complexity = _clamp(
        0.12
        + min(len(words), 500) / 850
        + min(clauses, 20) / 50
        + min(requested_steps, 10) / 20
        + (0.18 if quality else 0.0)
    )
    vague_references = len(
        re.findall(r"\b(this|that|it|things?|stuff|whatever)\b", normalized, re.I)
    )
    ambiguity = _clamp(vague_references / max(5, len(words) / 8))
    verification_strength = _clamp(len(verification) / 4)
    parallelizable = bool(
        re.search(
            r"\b(parallel|independent|multiple repos?|across projects?|compare)\b", normalized, re.I
        )
    )

    prework: list[str] = []
    task_kind = _task_kind(normalized)
    if task_kind in {"code", "diagnosis", "research"}:
        prework.append("inventory")
    if re.search(r"\b(diff|change|pr|branch)\b", normalized, re.I):
        prework.append("diff-summary")
    if re.search(r"\b(test|ci|fail|error|log)\b", normalized, re.I):
        prework.append("result-filter")
    if re.search(r"\b(schema|json|yaml|toml|config)\b", normalized, re.I):
        prework.append("schema-check")

    return TaskFeatures(
        fingerprint=sha256_text(normalized)[:20],
        task_kind=task_kind,
        risk=risk,
        write_scope=write_scope,  # type: ignore[arg-type]
        complexity=complexity,
        ambiguity=ambiguity,
        verification_strength=verification_strength,
        estimated_prompt_tokens=selected_counter.count(prompt),
        deterministic_prework=tuple(dict.fromkeys(prework)),
        parallelizable=parallelizable,
        explicit_quality_request=bool(quality),
        sensitive=bool(sensitive),
        reasons=tuple(reasons),
    )
