"""Invalid epoch metadata must not abort generic host preparation."""

import json

from memu.hosts.generic.sessions import GenericTranscriptSource


def test_invalid_epoch_metadata_is_ignored() -> None:
    source = GenericTranscriptSource("unused")
    invalid = (True, False, float("nan"), float("inf"), float("-inf"), 10**100, -(10**100))
    for value in invalid:
        assert source.timestamp(json.dumps({"timestamp": value})) is None


def test_valid_epoch_and_iso_timestamps_are_unchanged() -> None:
    source = GenericTranscriptSource("unused")
    assert source.timestamp('{"timestamp":0}') == "1970-01-01T00:00:00+00:00"
    assert source.timestamp('{"timestamp":1752537600000}') == "2025-07-15T00:00:00+00:00"
    assert source.timestamp('{"timestamp":"2026-07-16T00:00:00Z"}') == "2026-07-16T00:00:00Z"
