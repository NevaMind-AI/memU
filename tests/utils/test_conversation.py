import json

import pytest

from memu.utils.conversation import format_conversation_for_preprocess  # type: ignore[import-untyped]


class TestFormatConversationForPreprocess:
    """
    Test suite for format_conversation_for_preprocess function in src/memu/utils/conversation.py.

    Covers:
    - Happy Path: Valid JSON input (list or dict wrapper).
    - Edge Cases: Empty input, empty JSON structures.
    - Error Handling: Invalid JSON (current implementation handles gracefully by returning raw text).
    - Type Safety: Unexpected JSON types.
    """

    @pytest.mark.parametrize(
        "input_json,expected_output",
        [
            # Happy Path: Standard usage with list of messages
            (
                json.dumps([
                    {"role": "user", "content": "Hello world", "created_at": "2023-10-27T10:00:00"},
                    {"role": "assistant", "content": "Hello! How can I help?", "created_at": "2023-10-27T10:00:05"},
                ]),
                "[0] 2023-10-27T10:00:00 [user]: Hello world\n[1] 2023-10-27T10:00:05 [assistant]: Hello! How can I help?",
            ),
            # Happy Path: Dict wrapper with 'content' key
            (json.dumps({"content": [{"role": "user", "content": "Wrapper test"}]}), "[0] [user]: Wrapper test"),
            # Happy Path: Missing optional fields (role defaults to user, created_at omitted)
            (json.dumps([{"content": "Just text"}]), "[0] [user]: Just text"),
            # Happy Path: Multiline content should be collapsed
            (
                json.dumps([{"role": "system", "content": "Line 1\nLine 2\nLine 3"}]),
                "[0] [system]: Line 1 Line 2 Line 3",
            ),
            # Happy Path: Content is None/Null
            (json.dumps([{"role": "user", "content": None}]), "[0] [user]: "),
            # Happy Path: Content is a dict with 'text'
            (json.dumps([{"role": "user", "content": {"text": "Rich content"}}]), "[0] [user]: Rich content"),
        ],
    )
    def test_happy_path_valid_formats(self, input_json: str, expected_output: str) -> None:
        """
        Test that valid JSON inputs are correctly formatted into the expected line-based string.
        """
        result = format_conversation_for_preprocess(input_json)
        assert result == expected_output

    @pytest.mark.parametrize(
        "edge_input,expected",
        [
            ("", ""),  # Empty string
            ("   ", ""),  # Whitespace only
            ("[]", ""),  # Empty JSON list -> produces empty string
        ],
    )
    def test_edge_cases_empty(self, edge_input: str, expected: str) -> None:
        """
        Test edge cases handling for empty or whitespace-only inputs, and empty JSON lists.
        """
        assert format_conversation_for_preprocess(edge_input) == expected

    def test_malformed_json_handling(self) -> None:
        """
        Test handling of malformed JSON strings.

        Note: The implementation swallows JSONDecodeError and returns raw text.
        This test verifies that graceful fallback behavior.
        """
        malformed_json = '{"role": "user", "content": "Missing brace"'
        result = format_conversation_for_preprocess(malformed_json)
        # Expecting raw text back as fallback
        assert result == malformed_json

    def test_unexpected_json_structures(self) -> None:
        """
        Test handling of valid JSON that does not match expected conversation schema.
        Expectation: Returns raw text if schema extraction fails.
        """
        # Empty dict -> _extract_messages returns None
        assert format_conversation_for_preprocess("{}") == "{}"

        # Random non-message JSON
        random_json = json.dumps({"key": "value"})
        assert format_conversation_for_preprocess(random_json) == random_json

        # Valid JSON primitives
        assert format_conversation_for_preprocess("123") == "123"
