"""
Engram Storage Backends

This package provides storage backends for Engram embedding tables,
enabling efficient storage-compute separation strategies.

Available Backends:
    - InMemoryStorage: Fast in-memory storage
    - MMapStorage: Memory-mapped file storage
    - HybridStorage: Hot cache + cold storage with LRU
    
Utilities:
    - QuantizationHandler: FP16/INT8/INT4 quantization
"""

from memu.engram.storage.base import EmbeddingStorage
from memu.engram.storage.hybrid import HybridStorage
from memu.engram.storage.memory import InMemoryStorage
from memu.engram.storage.mmap import MMapStorage
from memu.engram.storage.quantization import QuantizationHandler

__all__ = [
    "EmbeddingStorage",
    "InMemoryStorage",
    "MMapStorage",
    "HybridStorage",
    "QuantizationHandler",
]
