"""
Tests for the main module.
"""

import pytest
from personalab.main import YourMainClass


class TestYourMainClass:
    """Test cases for YourMainClass."""
    
    def test_init_default(self):
        """Test initialization with default parameters."""
        instance = YourMainClass()
        assert instance.config == {}
        assert instance._initialized is True
    
    def test_init_with_config(self):
        """Test initialization with custom config."""
        config = {"key1": "value1", "key2": 42}
        instance = YourMainClass(config)
        assert instance.config == config
        assert instance._initialized is True
    
    def test_do_something(self):
        """Test do_something method."""
        instance = YourMainClass()
        result = instance.do_something()
        assert result == "Hello from your package!"
        assert isinstance(result, str)
    
    def test_process_data_empty_list(self):
        """Test process_data with empty list."""
        instance = YourMainClass()
        result = instance.process_data([])
        assert result == []
    
    def test_process_data_with_none_values(self):
        """Test process_data filters None values."""
        instance = YourMainClass()
        data = [1, None, "hello", None, 3.14, None]
        result = instance.process_data(data)
        expected = [1, "hello", 3.14]
        assert result == expected
    
    def test_process_data_no_none_values(self):
        """Test process_data with no None values."""
        instance = YourMainClass()
        data = [1, 2, 3, "hello", "world"]
        result = instance.process_data(data)
        assert result == data
    
    def test_get_config(self):
        """Test get_config returns copy of config."""
        config = {"key1": "value1", "nested": {"key2": "value2"}}
        instance = YourMainClass(config)
        retrieved_config = instance.get_config()
        
        # Should be equal but not the same object
        assert retrieved_config == config
        assert retrieved_config is not config
        
        # Modifying retrieved config shouldn't affect original
        retrieved_config["new_key"] = "new_value"
        assert "new_key" not in instance.config
    
    def test_update_config(self):
        """Test update_config method."""
        instance = YourMainClass({"key1": "value1"})
        new_config = {"key2": "value2", "key1": "updated_value1"}
        
        instance.update_config(new_config)
        
        expected = {"key1": "updated_value1", "key2": "value2"}
        assert instance.config == expected
    
    def test_update_config_empty(self):
        """Test update_config with empty dictionary."""
        original_config = {"key1": "value1"}
        instance = YourMainClass(original_config.copy())
        
        instance.update_config({})
        
        assert instance.config == original_config 