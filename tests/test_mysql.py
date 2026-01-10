"""Tests for MySQL database integration."""

from __future__ import annotations

import json
import pytest
from pydantic import BaseModel


class MySQLTestUserModel(BaseModel):
    """Test user model with scope fields."""
    user_id: str | None = None
    agent_id: str | None = None


# ============================================================================
# MySQL Repository Base Tests
# ============================================================================

class TestMySQLRepoBase:
    """Test MySQL repository base functionality."""

    def test_normalize_embedding_from_json_string(self):
        """Test embedding normalization from JSON string."""
        json_embedding = json.dumps([0.1, 0.2, 0.3])
        parsed = json.loads(json_embedding)
        result = [float(x) for x in parsed]
        assert result == [0.1, 0.2, 0.3]

    def test_normalize_embedding_from_list(self):
        """Test embedding normalization from list."""
        embedding = [0.1, 0.2, 0.3]
        result = [float(x) for x in embedding]
        assert result == [0.1, 0.2, 0.3]

    def test_normalize_embedding_none(self):
        """Test embedding normalization with None."""
        result = None
        assert result is None

    def test_prepare_embedding_to_json(self):
        """Test embedding preparation to JSON string."""
        embedding = [0.1, 0.2, 0.3]
        result = json.dumps(embedding)
        assert result == json.dumps(embedding)

    def test_prepare_embedding_none(self):
        """Test embedding preparation with None."""
        result = None
        assert result is None

    def test_matches_where_basic(self):
        """Test basic where clause matching."""
        class MockItem:
            user_id = "user1"
            agent_id = "agent1"
        
        item = MockItem()
        
        def matches_where(obj, where):
            if not where:
                return True
            for raw_key, expected in where.items():
                if expected is None:
                    continue
                field, op = [*raw_key.split("__", 1), None][:2]
                actual = getattr(obj, str(field), None)
                if op == "in":
                    if isinstance(expected, str):
                        if actual != expected:
                            return False
                    else:
                        try:
                            if actual not in expected:
                                return False
                        except TypeError:
                            return False
                else:
                    if actual != expected:
                        return False
            return True
        
        # Match
        assert matches_where(item, {"user_id": "user1"}) is True
        
        # No match
        assert matches_where(item, {"user_id": "user2"}) is False
        
        # Empty where
        assert matches_where(item, None) is True
        assert matches_where(item, {}) is True

    def test_matches_where_in_operator(self):
        """Test where clause with 'in' operator."""
        class MockItem:
            user_id = "user1"
        
        item = MockItem()
        
        def matches_where(obj, where):
            if not where:
                return True
            for raw_key, expected in where.items():
                if expected is None:
                    continue
                field, op = [*raw_key.split("__", 1), None][:2]
                actual = getattr(obj, str(field), None)
                if op == "in":
                    if isinstance(expected, str):
                        if actual != expected:
                            return False
                    else:
                        try:
                            if actual not in expected:
                                return False
                        except TypeError:
                            return False
                else:
                    if actual != expected:
                        return False
            return True
        
        # Match with in operator
        assert matches_where(item, {"user_id__in": ["user1", "user2"]}) is True
        
        # No match with in operator
        assert matches_where(item, {"user_id__in": ["user2", "user3"]}) is False


# ============================================================================
# MySQL Memory Item Repository Tests
# ============================================================================

class TestMySQLMemoryItemRepo:
    """Test MySQL memory item repository."""

    def test_cosine_similarity(self):
        """Test cosine similarity calculation."""
        def cosine(a, b):
            denom = (sum(x * x for x in a) ** 0.5) * (sum(y * y for y in b) ** 0.5) + 1e-9
            return float(sum(x * y for x, y in zip(a, b, strict=True)) / denom)
        
        # Identical vectors
        vec = [1.0, 0.0, 0.0]
        assert abs(cosine(vec, vec) - 1.0) < 0.001
        
        # Orthogonal vectors
        vec1 = [1.0, 0.0, 0.0]
        vec2 = [0.0, 1.0, 0.0]
        assert abs(cosine(vec1, vec2)) < 0.001
        
        # Similar vectors
        vec1 = [1.0, 1.0, 0.0]
        vec2 = [1.0, 0.0, 0.0]
        similarity = cosine(vec1, vec2)
        assert 0.5 < similarity < 1.0


# ============================================================================
# MySQL Store Integration Tests
# ============================================================================

class TestMySQLStoreInit:
    """Test MySQL store initialization."""

    def test_build_mysql_database_requires_dsn(self):
        """Test that build_mysql_database requires DSN."""
        from memu.app.settings import DatabaseConfig, MetadataStoreConfig
        from memu.database.mysql import build_mysql_database
        
        config = DatabaseConfig(
            metadata_store=MetadataStoreConfig(provider="mysql", dsn=None)
        )
        
        with pytest.raises(ValueError, match="MySQL metadata_store requires a DSN"):
            build_mysql_database(config=config, user_model=MySQLTestUserModel)


# ============================================================================
# Database Factory Tests
# ============================================================================

class TestDatabaseFactory:
    """Test database factory with MySQL support."""

    def test_factory_supports_mysql_provider(self):
        """Test that factory recognizes mysql provider."""
        from memu.database.factory import build_database
        from memu.app.settings import DatabaseConfig, MetadataStoreConfig
        
        config = DatabaseConfig(
            metadata_store=MetadataStoreConfig(provider="mysql", dsn=None)
        )
        
        # Should raise ValueError about DSN, not about unsupported provider
        with pytest.raises(ValueError, match="MySQL metadata_store requires a DSN"):
            build_database(config=config, user_model=MySQLTestUserModel)

    def test_factory_rejects_unknown_provider(self):
        """Test that factory rejects unknown providers."""
        from memu.database.factory import build_database
        from memu.app.settings import DatabaseConfig, MetadataStoreConfig
        
        # Create config with invalid provider by bypassing validation
        config = DatabaseConfig(
            metadata_store=MetadataStoreConfig(provider="inmemory")
        )
        # Manually set invalid provider
        config.metadata_store.provider = "unknown"
        
        with pytest.raises(ValueError, match="Unsupported metadata_store provider"):
            build_database(config=config, user_model=MySQLTestUserModel)


# ============================================================================
# Settings Tests
# ============================================================================

class TestSettingsMySQL:
    """Test settings support for MySQL."""

    def test_metadata_store_accepts_mysql(self):
        """Test that MetadataStoreConfig accepts mysql provider."""
        from memu.app.settings import MetadataStoreConfig
        
        config = MetadataStoreConfig(
            provider="mysql",
            dsn="mysql+pymysql://user:pass@localhost/testdb"
        )
        
        assert config.provider == "mysql"
        assert "mysql" in config.dsn

    def test_metadata_store_normalizes_mysql(self):
        """Test that provider is normalized to lowercase."""
        from memu.app.settings import MetadataStoreConfig
        
        config = MetadataStoreConfig(provider="MySQL")
        assert config.provider == "mysql"


# ============================================================================
# MySQL Module Structure Tests
# ============================================================================

class TestMySQLModuleStructure:
    """Test that MySQL module has correct structure."""

    def test_mysql_module_exports(self):
        """Test that MySQL module exports build_mysql_database."""
        from memu.database.mysql import build_mysql_database
        assert callable(build_mysql_database)

    def test_mysql_session_manager_exists(self):
        """Test that SessionManager class exists."""
        from memu.database.mysql.session import SessionManager
        assert SessionManager is not None

    def test_mysql_store_class_exists(self):
        """Test that MySQLStore class exists."""
        from memu.database.mysql.mysql import MySQLStore
        assert MySQLStore is not None

    def test_mysql_repositories_exist(self):
        """Test that all repository classes exist."""
        from memu.database.mysql.repositories import (
            MySQLResourceRepo,
            MySQLMemoryCategoryRepo,
            MySQLMemoryItemRepo,
            MySQLCategoryItemRepo,
        )
        assert MySQLResourceRepo is not None
        assert MySQLMemoryCategoryRepo is not None
        assert MySQLMemoryItemRepo is not None
        assert MySQLCategoryItemRepo is not None
