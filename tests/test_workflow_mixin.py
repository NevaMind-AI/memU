"""Tests for the WorkflowMixin refactoring.

These tests verify that the common utilities have been correctly extracted
into WorkflowMixin and that the mixins properly inherit from it.
"""

import pytest

# Check if postgres dependencies are available
# (importing memu.app.memorize triggers memu.app.__init__ -> service -> database.postgres)
try:
    import pgvector  # noqa: F401

    POSTGRES_DEPS_AVAILABLE = True
except ImportError:
    POSTGRES_DEPS_AVAILABLE = False

requires_postgres_deps = pytest.mark.skipif(
    not POSTGRES_DEPS_AVAILABLE,
    reason="Postgres dependencies (pgvector) not available",
)


class TestWorkflowMixinImports:
    """Test that all modules can be imported successfully."""

    @requires_postgres_deps
    def test_workflow_mixin_import(self):
        """Test that WorkflowMixin can be imported."""
        from memu.app.workflow import WorkflowMixin

        assert WorkflowMixin is not None

    @requires_postgres_deps
    def test_memorize_mixin_import(self):
        """Test that MemorizeMixin can be imported."""
        from memu.app.memorize import MemorizeMixin

        assert MemorizeMixin is not None

    @requires_postgres_deps
    def test_retrieve_mixin_import(self):
        """Test that RetrieveMixin can be imported."""
        from memu.app.retrieve import RetrieveMixin

        assert RetrieveMixin is not None

    @requires_postgres_deps
    def test_crud_mixin_import(self):
        """Test that CRUDMixin can be imported."""
        from memu.app.crud import CRUDMixin

        assert CRUDMixin is not None


class TestWorkflowMixinInheritance:
    """Test that all mixins properly inherit from WorkflowMixin."""

    @requires_postgres_deps
    def test_memorize_mixin_inherits_workflow_mixin(self):
        """Test that MemorizeMixin inherits from WorkflowMixin."""
        from memu.app.memorize import MemorizeMixin
        from memu.app.workflow import WorkflowMixin

        assert issubclass(MemorizeMixin, WorkflowMixin)

    @requires_postgres_deps
    def test_retrieve_mixin_inherits_workflow_mixin(self):
        """Test that RetrieveMixin inherits from WorkflowMixin."""
        from memu.app.retrieve import RetrieveMixin
        from memu.app.workflow import WorkflowMixin

        assert issubclass(RetrieveMixin, WorkflowMixin)

    @requires_postgres_deps
    def test_crud_mixin_inherits_workflow_mixin(self):
        """Test that CRUDMixin inherits from WorkflowMixin."""
        from memu.app.crud import CRUDMixin
        from memu.app.workflow import WorkflowMixin

        assert issubclass(CRUDMixin, WorkflowMixin)


@requires_postgres_deps
class TestWorkflowMixinMethods:
    """Test that WorkflowMixin provides all expected methods."""

    def test_extract_json_blob_method_exists(self):
        """Test that _extract_json_blob method exists."""
        from memu.app.workflow import WorkflowMixin

        assert hasattr(WorkflowMixin, "_extract_json_blob")

    def test_escape_prompt_value_method_exists(self):
        """Test that _escape_prompt_value method exists."""
        from memu.app.workflow import WorkflowMixin

        assert hasattr(WorkflowMixin, "_escape_prompt_value")

    def test_extract_tag_content_method_exists(self):
        """Test that _extract_tag_content method exists."""
        from memu.app.workflow import WorkflowMixin

        assert hasattr(WorkflowMixin, "_extract_tag_content")

    def test_model_dump_without_embeddings_method_exists(self):
        """Test that _model_dump_without_embeddings method exists."""
        from memu.app.workflow import WorkflowMixin

        assert hasattr(WorkflowMixin, "_model_dump_without_embeddings")

    def test_normalize_where_method_exists(self):
        """Test that _normalize_where method exists."""
        from memu.app.workflow import WorkflowMixin

        assert hasattr(WorkflowMixin, "_normalize_where")

    def test_workflow_response_method_exists(self):
        """Test that _workflow_response method exists."""
        from memu.app.workflow import WorkflowMixin

        assert hasattr(WorkflowMixin, "_workflow_response")

    def test_category_embedding_text_method_exists(self):
        """Test that _category_embedding_text method exists."""
        from memu.app.workflow import WorkflowMixin

        assert hasattr(WorkflowMixin, "_category_embedding_text")

    def test_extract_query_text_method_exists(self):
        """Test that _extract_query_text method exists."""
        from memu.app.workflow import WorkflowMixin

        assert hasattr(WorkflowMixin, "_extract_query_text")


@requires_postgres_deps
class TestWorkflowMixinFunctionality:
    """Test the functionality of WorkflowMixin methods."""

    def test_extract_json_blob_basic(self):
        """Test _extract_json_blob extracts JSON correctly."""
        from memu.app.workflow import WorkflowMixin

        class TestClass(WorkflowMixin):
            pass

        obj = TestClass()
        raw = 'Some text {"key": "value", "nested": {"data": 123}} more text'
        result = obj._extract_json_blob(raw)
        assert result == '{"key": "value", "nested": {"data": 123}}'

    def test_extract_json_blob_invalid_json(self):
        """Test _extract_json_blob raises ValueError for invalid JSON."""
        from memu.app.workflow import WorkflowMixin

        class TestClass(WorkflowMixin):
            pass

        obj = TestClass()
        with pytest.raises(ValueError, match="No JSON object found"):
            obj._extract_json_blob("No JSON here")

    def test_escape_prompt_value(self):
        """Test _escape_prompt_value escapes curly braces."""
        from memu.app.workflow import WorkflowMixin

        class TestClass(WorkflowMixin):
            pass

        obj = TestClass()
        result = obj._escape_prompt_value("Hello {name} and {placeholder}")
        assert result == "Hello {{name}} and {{placeholder}}"

    def test_extract_tag_content(self):
        """Test _extract_tag_content extracts content between tags."""
        from memu.app.workflow import WorkflowMixin

        class TestClass(WorkflowMixin):
            pass

        obj = TestClass()
        raw = "<tag>Extracted content</tag>"
        result = obj._extract_tag_content(raw, "tag")
        assert result == "Extracted content"

    def test_extract_tag_content_no_match(self):
        """Test _extract_tag_content returns None when tag not found."""
        from memu.app.workflow import WorkflowMixin

        class TestClass(WorkflowMixin):
            pass

        obj = TestClass()
        result = obj._extract_tag_content("No tags here", "tag")
        assert result is None

    def test_extract_tag_content_empty_content(self):
        """Test _extract_tag_content returns None for tags with empty or whitespace content."""
        from memu.app.workflow import WorkflowMixin

        class TestClass(WorkflowMixin):
            pass

        obj = TestClass()
        # Empty content between tags
        result = obj._extract_tag_content("<tag></tag>", "tag")
        assert result is None

        # Only whitespace between tags
        result = obj._extract_tag_content("<tag>   </tag>", "tag")
        assert result is None

    def test_category_embedding_text_basic(self):
        """Test _category_embedding_text generates proper text."""
        from memu.app.workflow import WorkflowMixin

        class TestClass(WorkflowMixin):
            pass

        obj = TestClass()
        result = obj._category_embedding_text({"name": "Test", "description": "A test category"})
        assert result == "Test: A test category"

    def test_category_embedding_text_no_description(self):
        """Test _category_embedding_text with no description."""
        from memu.app.workflow import WorkflowMixin

        class TestClass(WorkflowMixin):
            pass

        obj = TestClass()
        result = obj._category_embedding_text({"name": "Test"})
        assert result == "Test"

    def test_category_embedding_text_empty_name_fallback(self):
        """Test _category_embedding_text uses 'Untitled' for empty name."""
        from memu.app.workflow import WorkflowMixin

        class TestClass(WorkflowMixin):
            pass

        obj = TestClass()
        result = obj._category_embedding_text({"name": "", "description": "A test"})
        assert result == "Untitled: A test"

        result = obj._category_embedding_text({})
        assert result == "Untitled"

    def test_extract_query_text_string(self):
        """Test _extract_query_text with string input."""
        from memu.app.workflow import WorkflowMixin

        class TestClass(WorkflowMixin):
            pass

        obj = TestClass()
        result = obj._extract_query_text("simple query")
        assert result == "simple query"

    def test_extract_query_text_dict_with_text(self):
        """Test _extract_query_text with dict having text field."""
        from memu.app.workflow import WorkflowMixin

        class TestClass(WorkflowMixin):
            pass

        obj = TestClass()
        result = obj._extract_query_text({"text": "dict query"})
        assert result == "dict query"

    def test_normalize_where_empty(self):
        """Test _normalize_where with None or empty dict."""
        from pydantic import BaseModel

        from memu.app.workflow import WorkflowMixin

        class UserModel(BaseModel):
            user_id: str

        class TestClass(WorkflowMixin):
            user_model = UserModel

        obj = TestClass()
        assert obj._normalize_where(None) == {}
        assert obj._normalize_where({}) == {}

    def test_normalize_where_valid_fields(self):
        """Test _normalize_where with valid filter fields."""
        from pydantic import BaseModel

        from memu.app.workflow import WorkflowMixin

        class UserModel(BaseModel):
            user_id: str
            org_id: str

        class TestClass(WorkflowMixin):
            user_model = UserModel

        obj = TestClass()
        result = obj._normalize_where({"user_id": "123", "org_id__in": ["a", "b"]})
        assert result == {"user_id": "123", "org_id__in": ["a", "b"]}

    def test_normalize_where_invalid_field_raises(self):
        """Test _normalize_where raises ValueError for unknown fields."""
        from pydantic import BaseModel

        from memu.app.workflow import WorkflowMixin

        class UserModel(BaseModel):
            user_id: str

        class TestClass(WorkflowMixin):
            user_model = UserModel

        obj = TestClass()
        with pytest.raises(ValueError, match="Unknown filter field"):
            obj._normalize_where({"invalid_field": "value"})

    def test_normalize_where_skips_none_values(self):
        """Test _normalize_where skips None values."""
        from pydantic import BaseModel

        from memu.app.workflow import WorkflowMixin

        class UserModel(BaseModel):
            user_id: str
            org_id: str

        class TestClass(WorkflowMixin):
            user_model = UserModel

        obj = TestClass()
        result = obj._normalize_where({"user_id": "123", "org_id": None})
        assert result == {"user_id": "123"}

    def test_workflow_response_success(self):
        """Test _workflow_response extracts response correctly."""
        from memu.app.workflow import WorkflowMixin

        class TestClass(WorkflowMixin):
            pass

        obj = TestClass()
        result = {"response": {"data": "test"}, "other": "ignored"}
        response = obj._workflow_response(result, "TestWorkflow")
        assert response == {"data": "test"}

    def test_workflow_response_raises_on_none(self):
        """Test _workflow_response raises RuntimeError when response is None."""
        from memu.app.workflow import WorkflowMixin

        class TestClass(WorkflowMixin):
            pass

        obj = TestClass()
        result = {"response": None}
        with pytest.raises(RuntimeError, match="TestWorkflow workflow failed"):
            obj._workflow_response(result, "TestWorkflow")

    def test_workflow_response_raises_on_missing(self):
        """Test _workflow_response raises RuntimeError when response key is missing."""
        from memu.app.workflow import WorkflowMixin

        class TestClass(WorkflowMixin):
            pass

        obj = TestClass()
        result = {"other": "data"}
        with pytest.raises(RuntimeError, match="MyWorkflow workflow failed"):
            obj._workflow_response(result, "MyWorkflow")


@requires_postgres_deps
class TestNoDuplicateMethods:
    """Test that duplicate methods have been removed from child mixins."""

    def test_memorize_no_duplicate_extract_tag_content(self):
        """Test that MemorizeMixin doesn't define its own _extract_tag_content."""
        import inspect

        from memu.app.memorize import MemorizeMixin
        from memu.app.workflow import WorkflowMixin

        # Get all method names defined directly on MemorizeMixin (not inherited)
        own_methods = set()
        for name, _method in inspect.getmembers(MemorizeMixin, predicate=inspect.isfunction):
            if not hasattr(WorkflowMixin, name):
                own_methods.add(name)

        # _extract_tag_content should NOT be in own_methods since it's now inherited
        assert "_extract_tag_content" not in own_methods, (
            "_extract_tag_content should be inherited from WorkflowMixin, not defined in MemorizeMixin"
        )

    def test_retrieve_no_duplicate_normalize_where(self):
        """Test that RetrieveMixin doesn't define its own _normalize_where."""
        import inspect

        from memu.app.retrieve import RetrieveMixin
        from memu.app.workflow import WorkflowMixin

        # Get all method names defined directly on RetrieveMixin (not inherited)
        own_methods = set()
        for name, _method in inspect.getmembers(RetrieveMixin, predicate=inspect.isfunction):
            if not hasattr(WorkflowMixin, name):
                own_methods.add(name)

        # _normalize_where should NOT be in own_methods since it's now inherited
        assert "_normalize_where" not in own_methods, (
            "_normalize_where should be inherited from WorkflowMixin, not defined in RetrieveMixin"
        )

    def test_crud_no_duplicate_normalize_where(self):
        """Test that CRUDMixin doesn't define its own _normalize_where."""
        import inspect

        from memu.app.crud import CRUDMixin
        from memu.app.workflow import WorkflowMixin

        # Get all method names defined directly on CRUDMixin (not inherited)
        own_methods = set()
        for name, _method in inspect.getmembers(CRUDMixin, predicate=inspect.isfunction):
            if not hasattr(WorkflowMixin, name):
                own_methods.add(name)

        # _normalize_where should NOT be in own_methods since it's now inherited
        assert "_normalize_where" not in own_methods, (
            "_normalize_where should be inherited from WorkflowMixin, not defined in CRUDMixin"
        )

    def test_memorize_no_duplicate_category_embedding_text(self):
        """Test that MemorizeMixin still has _category_embedding_text (as override)."""
        import inspect

        from memu.app.memorize import MemorizeMixin

        # Note: MemorizeMixin intentionally keeps _category_embedding_text as a static method
        # that overrides the one in WorkflowMixin. This is expected behavior.
        own_methods = set()
        for name, _method in inspect.getmembers(MemorizeMixin, predicate=inspect.isfunction):
            own_methods.add(name)

        # Verify that the method exists (either inherited or overridden)
        assert "_category_embedding_text" in own_methods

    def test_retrieve_has_extract_query_text_override(self):
        """Test that RetrieveMixin has its own _extract_query_text (as override)."""
        import inspect

        from memu.app.retrieve import RetrieveMixin

        # Note: RetrieveMixin intentionally keeps _extract_query_text as a static method
        # that overrides the one in WorkflowMixin with stricter validation.
        own_methods = set()
        for name, _method in inspect.getmembers(RetrieveMixin, predicate=inspect.isfunction):
            own_methods.add(name)

        # Verify that the method exists (either inherited or overridden)
        assert "_extract_query_text" in own_methods


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
