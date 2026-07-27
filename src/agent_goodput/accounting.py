from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from .models import RunOutcome, TokenUsage


@dataclass(frozen=True)
class TokenWeights:
    """Explicit conversion weights for a cost-equivalent view.

    Raw token totals remain the primary consumption measure. These weights are
    never used to claim literal token savings.
    """

    uncached_input: float = 1.0
    cached_input: float = 0.1
    output: float = 8.0

    def __post_init__(self) -> None:
        if min(self.uncached_input, self.cached_input, self.output) < 0:
            raise ValueError("token weights cannot be negative")


def effective_tokens(usage: TokenUsage, weights: TokenWeights | None = None) -> float:
    selected = weights or TokenWeights()
    return (
        usage.uncached_input_tokens * selected.uncached_input
        + usage.cached_input_tokens * selected.cached_input
        + usage.output_tokens * selected.output
    )


def verified_goodput(
    outcomes: list[RunOutcome] | tuple[RunOutcome, ...],
    *,
    weights: TokenWeights | None = None,
    scale: float = 1_000_000,
) -> float:
    """Return verified work units per effective million tokens.

    Failed or safety-gated runs contribute zero useful work while their tokens
    remain in the denominator.
    """

    total_tokens = sum(effective_tokens(item.usage, weights) for item in outcomes)
    if total_tokens <= 0:
        return 0.0
    useful_work = sum(item.verified_work_units for item in outcomes)
    return useful_work / total_tokens * scale


class TokenCounter(Protocol):
    name: str
    exact: bool

    def count(self, text: str) -> int: ...


class ApproximateTokenCounter:
    name = "utf8-bytes-over-four"
    exact = False

    def count(self, text: str) -> int:
        if not text:
            return 0
        return max(1, (len(text.encode("utf-8")) + 3) // 4)


class TikTokenCounter:
    exact = True

    def __init__(self, model: str = "gpt-5.6") -> None:
        try:
            import tiktoken  # type: ignore[import-not-found]
        except ImportError as error:  # pragma: no cover - optional dependency
            raise RuntimeError("Install agent-goodput[tokens] for tokenizer support") from error
        try:
            self._encoding = tiktoken.encoding_for_model(model)
        except KeyError:
            self._encoding = tiktoken.get_encoding("o200k_base")
        self.name = f"tiktoken:{self._encoding.name}"

    def count(self, text: str) -> int:
        return len(self._encoding.encode(text))


def best_available_counter(model: str = "gpt-5.6") -> TokenCounter:
    try:
        return TikTokenCounter(model)
    except RuntimeError:
        return ApproximateTokenCounter()
