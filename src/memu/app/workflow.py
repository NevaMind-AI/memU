"""Workflow mixin providing common utilities for memory operations.

This module extracts common functionality used across memorize, retrieve, and crud mixins
to reduce code duplication and improve maintainability.
"""

from __future__ import annotations

import logging
import re
from collections.abc import Awaitable, Callable, Mapping
from typing import TYPE_CHECKING, Any, cast

from pydantic import BaseModel

from memu.workflow.step import WorkflowState

logger = logging.getLogger(__name__)

if TYPE_CHECKING:
    from memu.app.service import Context
    from memu.database.interfaces import Database


class WorkflowMixin:
    """Mixin providing common workflow utilities for memory operations.

    This mixin contains helper methods that are shared across MemorizeMixin,
    RetrieveMixin, and CRUDMixin to reduce code duplication.
    """

    # Type hints for methods/attributes provided by the implementing class
    if TYPE_CHECKING:
        _run_workflow: Callable[..., Awaitable[WorkflowState]]
        _get_context: Callable[[], Context]
        _get_database: Callable[[], Database]
        _get_step_llm_client: Callable[[Mapping[str, Any] | None], Any]
        _get_llm_client: Callable[..., Any]
        user_model: type[BaseModel]

    @staticmethod
    def _extract_json_blob(raw: str) -> str:
        """Extract JSON object from LLM response text.

        Finds the first '{' and last '}' to extract the JSON object,
        handling cases where the LLM might add surrounding text.

        Args:
            raw: Raw response text from LLM

        Returns:
            Extracted JSON string

        Raises:
            ValueError: If no valid JSON object is found
        """
        start = raw.find("{")
        end = raw.rfind("}")
        if start == -1 or end == -1 or end <= start:
            msg = "No JSON object found"
            raise ValueError(msg)
        return raw[start : end + 1]

    @staticmethod
    def _escape_prompt_value(value: str) -> str:
        """Escape special characters for LLM prompt formatting.

        Escapes curly braces which are used as format string delimiters
        in Jinja2-style prompts.

        Args:
            value: Value to escape

        Returns:
            Escaped value safe for use in prompts
        """
        return value.replace("{", "{{").replace("}", "}}")

    @staticmethod
    def _extract_tag_content(raw: str, tag: str) -> str | None:
        """Extract content between XML-style tags.

        Args:
            raw: Raw response text
            tag: Tag name to extract (without angle brackets)

        Returns:
            Content inside the tag, or None if not found
        """
        pattern = rf"<{tag}>\s*(.*?)\s*</{tag}>"
        match = re.search(pattern, raw, re.IGNORECASE | re.DOTALL)
        if match:
            return match.group(1).strip() or None
        return None

    def _model_dump_without_embeddings(self, obj: BaseModel) -> dict[str, Any]:
        """Serialize a Pydantic model, excluding embedding fields.

        Args:
            obj: Pydantic model instance to serialize

        Returns:
            Dictionary representation without embedding data
        """
        data = obj.model_dump(exclude={"embedding"})
        return data

    def _normalize_where(self, where: Mapping[str, Any] | None) -> dict[str, Any]:
        """Validate and clean the `where` scope filters against the configured user model.

        Ensures that only valid filter fields specified in the user model are allowed,
        preventing invalid filter parameters from reaching the database layer.

        Args:
            where: Raw filter parameters from the caller

        Returns:
            Cleaned and validated filter dictionary

        Raises:
            ValueError: If an unknown filter field is provided
        """
        if not where:
            return {}

        valid_fields = set(getattr(self.user_model, "model_fields", {}).keys())
        cleaned: dict[str, Any] = {}

        for raw_key, value in where.items():
            if value is None:
                continue
            field = raw_key.split("__", 1)[0]
            if field not in valid_fields:
                msg = f"Unknown filter field '{field}' for current user scope"
                raise ValueError(msg)
            cleaned[raw_key] = value

        return cleaned

    def _extract_query_text(self, query: dict[str, Any]) -> str:
        """Extract query text from a query dictionary.

        Supports queries with 'text' field or direct string values.

        Args:
            query: Query dictionary or string

        Returns:
            Extracted query text
        """
        if isinstance(query, str):
            return query
        if isinstance(query, dict):
            return query.get("text", "") or ""
        return str(query)

    def _category_embedding_text(self, category: dict[str, str]) -> str:
        """Generate text for embedding a category.

        Creates a combined string of category name and description
        suitable for semantic similarity matching.

        Args:
            category: Category dictionary with 'name' and optionally 'description'

        Returns:
            Combined text for embedding
        """
        name = (category.get("name") or "").strip() or "Untitled"
        desc = (category.get("description") or "").strip()
        if desc:
            return f"{name}: {desc}"
        return name

    def _workflow_response(
        self,
        result: WorkflowState,
        workflow_name: str,
    ) -> dict[str, Any]:
        """Extract and validate workflow response.

        Standard error handling pattern for all workflow operations.

        Args:
            result: Workflow execution result
            workflow_name: Name of the workflow for error messages

        Returns:
            Response dictionary from the workflow

        Raises:
            RuntimeError: If workflow failed to produce a response
        """
        response = cast(dict[str, Any] | None, result.get("response"))
        if response is None:
            msg = f"{workflow_name} workflow failed to produce a response"
            raise RuntimeError(msg)
        return response
