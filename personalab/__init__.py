"""
PersonaLab

A Python framework for creating and managing AI personas and laboratory environments.
"""

__version__ = "0.1.0"
__author__ = "Your Name"
__email__ = "your.email@example.com"

# from .main import YourMainClass  # Commented out until main module is created
from .memory import BaseMemory, ProfileMemory, EventMemory, Memory

__all__ = ["BaseMemory", "ProfileMemory", "EventMemory", "Memory"] 