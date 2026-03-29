"""Tests for the Memory Admission Gate."""

from __future__ import annotations

import pytest

from memu.app.admission import AdmissionGate, AdmissionResult
from memu.app.settings import MemorizeAdmissionConfig


def _gate(*, enabled: bool = True, min_length: int = 30, threshold: float = 0.3, noise_patterns: list[str] | None = None) -> AdmissionGate:
    return AdmissionGate(
        MemorizeAdmissionConfig(
            enabled=enabled,
            min_length=min_length,
            threshold=threshold,
            noise_patterns=noise_patterns or [],
        )
    )


# ------------------------------------------------------------------
# Gate disabled → everything passes
# ------------------------------------------------------------------

class TestGateDisabled:
    def test_short_string_passes_when_disabled(self):
        r = _gate(enabled=False).check("hi")
        assert r.allowed is True
        assert r.score == 1.0
        assert r.reason == "gate_disabled"

    def test_noise_passes_when_disabled(self):
        r = _gate(enabled=False).check("<local-command-caveat> stuff")
        assert r.allowed is True


# ------------------------------------------------------------------
# Min-length filter
# ------------------------------------------------------------------

class TestMinLength:
    def test_too_short_rejected(self):
        r = _gate(min_length=30).check("short")
        assert r.allowed is False
        assert "too_short" in r.reason
        assert r.score == 0.0

    def test_exactly_at_min_length(self):
        text = "A" * 30
        r = _gate(min_length=30).check(text)
        # Not rejected by length (may still be rejected by score)
        assert "too_short" not in r.reason

    def test_whitespace_only_rejected(self):
        r = _gate(min_length=5).check("     ")
        assert r.allowed is False
        assert "too_short" in r.reason


# ------------------------------------------------------------------
# Built-in noise patterns
# ------------------------------------------------------------------

class TestNoisePatterns:
    def test_local_command_caveat(self):
        r = _gate().check("This is a message with <local-command-caveat> in it and some more text here.")
        assert r.allowed is False
        assert "noise_pattern" in r.reason

    def test_exit_code(self):
        r = _gate().check("EXIT: 0\nSome other output that makes it long enough to pass length check.")
        assert r.allowed is False
        assert "noise_pattern" in r.reason

    def test_shell_prompt(self):
        r = _gate().check("$ git status\nOn branch main nothing to commit working tree clean enough text")
        assert r.allowed is False
        assert "noise_pattern" in r.reason

    def test_pure_json(self):
        r = _gate().check('{"key": "value", "another": 123, "nested": {"a": true}}')
        assert r.allowed is False
        assert "noise_pattern" in r.reason

    def test_json_with_natural_language_not_rejected_by_json_pattern(self):
        # Text that starts with [ but has natural language around it shouldn't match the pure-JSON pattern
        text = "Here is some context about the user. They prefer dark mode and use vim."
        r = _gate().check(text)
        # Should not be rejected by noise patterns
        assert "noise_pattern" not in r.reason


# ------------------------------------------------------------------
# Custom noise patterns
# ------------------------------------------------------------------

class TestCustomPatterns:
    def test_custom_pattern_rejects(self):
        r = _gate(noise_patterns=[r"IGNORE_THIS"]).check(
            "Some text that contains IGNORE_THIS marker and is long enough."
        )
        assert r.allowed is False
        assert "custom_noise_pattern" in r.reason


# ------------------------------------------------------------------
# Quality score / threshold
# ------------------------------------------------------------------

class TestScoreThreshold:
    def test_natural_language_passes(self):
        text = "The user prefers dark mode and uses Vim as their primary editor. They are experienced with Python."
        r = _gate(threshold=0.3).check(text)
        assert r.allowed is True
        assert r.score >= 0.3

    def test_low_quality_rejected(self):
        # All caps, no spaces, short-ish → low score
        text = "AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA"  # 31 chars, no spaces, no mixed case
        r = _gate(threshold=0.5).check(text)
        assert r.allowed is False
        assert "low_score" in r.reason


# ------------------------------------------------------------------
# AdmissionResult dataclass
# ------------------------------------------------------------------

class TestAdmissionResult:
    def test_is_frozen(self):
        r = AdmissionResult(allowed=True, reason="pass", score=0.8)
        with pytest.raises(AttributeError):
            r.allowed = False  # type: ignore[misc]
