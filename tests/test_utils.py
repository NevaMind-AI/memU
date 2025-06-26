"""
Tests for the utils module.
"""

import json
import logging
import pytest
import tempfile
import os
from unittest.mock import patch, MagicMock

from your_package.utils import (
    setup_logging,
    validate_config,
    load_json_file,
    save_json_file,
    flatten_dict
)


class TestSetupLogging:
    """Test cases for setup_logging function."""
    
    def test_setup_logging_default_level(self):
        """Test setup_logging with default INFO level."""
        logger = setup_logging()
        assert logger.level == logging.INFO
        assert isinstance(logger, logging.Logger)
    
    def test_setup_logging_custom_level(self):
        """Test setup_logging with custom level."""
        logger = setup_logging("DEBUG")
        assert logger.level == logging.DEBUG
    
    def test_setup_logging_invalid_level(self):
        """Test setup_logging with invalid level."""
        with pytest.raises(AttributeError):
            setup_logging("INVALID_LEVEL")


class TestValidateConfig:
    """Test cases for validate_config function."""
    
    def test_validate_config_all_keys_present(self):
        """Test validate_config when all required keys are present."""
        config = {"key1": "value1", "key2": "value2", "key3": "value3"}
        required_keys = ["key1", "key2"]
        
        result = validate_config(config, required_keys)
        assert result is True
    
    def test_validate_config_missing_keys(self):
        """Test validate_config when required keys are missing."""
        config = {"key1": "value1"}
        required_keys = ["key1", "key2", "key3"]
        
        with pytest.raises(ValueError) as exc_info:
            validate_config(config, required_keys)
        
        assert "Missing required configuration keys: ['key2', 'key3']" in str(exc_info.value)
    
    def test_validate_config_empty_required(self):
        """Test validate_config with empty required keys list."""
        config = {"key1": "value1"}
        required_keys = []
        
        result = validate_config(config, required_keys)
        assert result is True


class TestJsonFileFunctions:
    """Test cases for JSON file functions."""
    
    def test_load_json_file_success(self):
        """Test successful JSON file loading."""
        test_data = {"key1": "value1", "key2": 42, "nested": {"key3": "value3"}}
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            json.dump(test_data, f)
            temp_file = f.name
        
        try:
            loaded_data = load_json_file(temp_file)
            assert loaded_data == test_data
        finally:
            os.unlink(temp_file)
    
    def test_load_json_file_not_found(self):
        """Test load_json_file with non-existent file."""
        with pytest.raises(FileNotFoundError) as exc_info:
            load_json_file("non_existent_file.json")
        
        assert "Configuration file not found" in str(exc_info.value)
    
    def test_load_json_file_invalid_json(self):
        """Test load_json_file with invalid JSON."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            f.write("invalid json content {")
            temp_file = f.name
        
        try:
            with pytest.raises(json.JSONDecodeError):
                load_json_file(temp_file)
        finally:
            os.unlink(temp_file)
    
    def test_save_json_file(self):
        """Test save_json_file function."""
        test_data = {"key1": "value1", "key2": 42, "nested": {"key3": "value3"}}
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            temp_file = f.name
        
        try:
            save_json_file(test_data, temp_file)
            
            # Verify the file was saved correctly
            with open(temp_file, 'r', encoding='utf-8') as f:
                loaded_data = json.load(f)
            
            assert loaded_data == test_data
        finally:
            os.unlink(temp_file)


class TestFlattenDict:
    """Test cases for flatten_dict function."""
    
    def test_flatten_dict_simple(self):
        """Test flatten_dict with simple nested dictionary."""
        nested_dict = {
            "a": 1,
            "b": {
                "c": 2,
                "d": 3
            }
        }
        
        expected = {
            "a": 1,
            "b.c": 2,
            "b.d": 3
        }
        
        result = flatten_dict(nested_dict)
        assert result == expected
    
    def test_flatten_dict_deep_nesting(self):
        """Test flatten_dict with deeply nested dictionary."""
        nested_dict = {
            "level1": {
                "level2": {
                    "level3": {
                        "value": "deep"
                    }
                }
            }
        }
        
        expected = {
            "level1.level2.level3.value": "deep"
        }
        
        result = flatten_dict(nested_dict)
        assert result == expected
    
    def test_flatten_dict_custom_separator(self):
        """Test flatten_dict with custom separator."""
        nested_dict = {
            "a": {
                "b": {
                    "c": "value"
                }
            }
        }
        
        expected = {
            "a/b/c": "value"
        }
        
        result = flatten_dict(nested_dict, sep="/")
        assert result == expected
    
    def test_flatten_dict_no_nesting(self):
        """Test flatten_dict with flat dictionary."""
        flat_dict = {"a": 1, "b": 2, "c": 3}
        
        result = flatten_dict(flat_dict)
        assert result == flat_dict
    
    def test_flatten_dict_empty(self):
        """Test flatten_dict with empty dictionary."""
        result = flatten_dict({})
        assert result == {} 