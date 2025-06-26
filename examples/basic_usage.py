#!/usr/bin/env python3
"""
Basic usage example for your package.
"""

from personalab import YourMainClass
from personalab.utils import setup_logging, validate_config


def main():
    """Demonstrate basic usage of the package."""
    
    # Set up logging
    logger = setup_logging("INFO")
    logger.info("Starting basic usage example")
    
    # Create instance with configuration
    config = {
        "setting1": "value1",
        "setting2": 42,
        "nested": {
            "option": True
        }
    }
    
    # Validate configuration
    required_keys = ["setting1", "setting2"]
    try:
        validate_config(config, required_keys)
        logger.info("Configuration is valid")
    except ValueError as e:
        logger.error(f"Configuration error: {e}")
        return
    
    # Initialize main class
    instance = YourMainClass(config)
    
    # Demonstrate basic functionality
    result = instance.do_something()
    logger.info(f"Result: {result}")
    
    # Process some data
    sample_data = [1, 2, None, "hello", None, 3.14, "world"]
    processed_data = instance.process_data(sample_data)
    logger.info(f"Processed data: {processed_data}")
    
    # Show configuration
    current_config = instance.get_config()
    logger.info(f"Current config: {current_config}")
    
    # Update configuration
    instance.update_config({"new_setting": "new_value"})
    updated_config = instance.get_config()
    logger.info(f"Updated config: {updated_config}")
    
    logger.info("Example completed successfully")


if __name__ == "__main__":
    main() 