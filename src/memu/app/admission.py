"""Memory Admission Gate — filter low-quality content before memorization.

Inspired by A-MAC (arXiv:2603.04549): score content at write-time,
reject below threshold.  Pure heuristics, no LLM calls.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from memu.app.settings import MemorizeAdmissionConfig


class AdmissionRejectedError(Exception):
    """Raised when content fails the admission gate."""

    def __init__(self, result: AdmissionResult) -> None:
        self.result = result
        super().__init__(result.reason)

# Built-in noise patterns (always applied when gate is enabled)
_BUILTIN_NOISE_PATTERNS: list[re.Pattern[str]] = [
    re.compile(r"<local-command-caveat>"),
    re.compile(r"^\s*EXIT:\s*\d+", re.MULTILINE),
    # Bare shell prompt lines, e.g. "$ ls -la" or "> git status"
    re.compile(r"^\s*[$>]\s+\S+", re.MULTILINE),
    # Pure JSON blob with no natural language around it
    re.compile(r"^\s*[\[{][\s\S]*[\]}]\s*$"),
]


@dataclass(frozen=True, slots=True)
class AdmissionResult:
    allowed: bool
    reason: str
    score: float


class AdmissionGate:
    """Stateless, cheap content gate."""

    def __init__(self, config: MemorizeAdmissionConfig) -> None:
        self._enabled = config.enabled
        self._min_length = config.min_length
        self._threshold = config.threshold
        # Compile user-supplied patterns once
        self._extra_patterns = [re.compile(p) for p in (config.noise_patterns or [])]

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def check(self, content: str) -> AdmissionResult:
        """Return admission decision for *content*.

        When the gate is disabled every input is allowed (score=1.0).
        """
        if not self._enabled:
            return AdmissionResult(allowed=True, reason="gate_disabled", score=1.0)

        stripped = content.strip()

        # --- length filter ---
        if len(stripped) < self._min_length:
            return AdmissionResult(
                allowed=False,
                reason=f"too_short (len={len(stripped)}<{self._min_length})",
                score=0.0,
            )

        # --- noise pattern filter ---
        for pat in _BUILTIN_NOISE_PATTERNS:
            if pat.search(stripped):
                return AdmissionResult(
                    allowed=False,
                    reason=f"noise_pattern ({pat.pattern!r})",
                    score=0.1,
                )

        for pat in self._extra_patterns:
            if pat.search(stripped):
                return AdmissionResult(
                    allowed=False,
                    reason=f"custom_noise_pattern ({pat.pattern!r})",
                    score=0.1,
                )

        # --- basic quality score (simple heuristic) ---
        score = self._score(stripped)
        if score < self._threshold:
            return AdmissionResult(
                allowed=False,
                reason=f"low_score ({score:.2f}<{self._threshold})",
                score=score,
            )

        return AdmissionResult(allowed=True, reason="pass", score=score)

    # ------------------------------------------------------------------
    # Internals
    # ------------------------------------------------------------------

    @staticmethod
    def _score(text: str) -> float:
        """Cheap 0-1 quality heuristic.

        Rewards: longer text, presence of spaces (sentence-like), mixed case.
        """
        length = len(text)
        # length component: ramp 0→1 over 30-300 chars
        len_score = min(length / 300.0, 1.0)

        # space ratio — natural language has ~15-20% spaces
        space_ratio = text.count(" ") / max(length, 1)
        space_score = min(space_ratio / 0.15, 1.0)

        # mixed case (not ALL CAPS or all lower)
        has_upper = any(c.isupper() for c in text)
        has_lower = any(c.islower() for c in text)
        case_score = 1.0 if (has_upper and has_lower) else 0.5

        return round(0.4 * len_score + 0.35 * space_score + 0.25 * case_score, 4)
