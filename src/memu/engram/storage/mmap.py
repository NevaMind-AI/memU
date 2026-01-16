"""
Memory-Mapped File Storage Backend for Engram

Enables efficient storage-compute separation by storing embeddings
on disk with memory-mapped access.
"""

from __future__ import annotations

import logging
import mmap
import struct
from pathlib import Path

import numpy as np

from memu.engram.storage.base import EmbeddingStorage
from memu.engram.storage.memory import InMemoryStorage

logger = logging.getLogger(__name__)


class MMapStorage(EmbeddingStorage):
    """Memory-mapped file storage for large embedding tables.
    
    This backend enables efficient storage-compute separation by:
    - Storing embeddings on disk with memory-mapped access
    - Loading only required embeddings on demand (O(1) access)
    - Supporting concurrent access from multiple processes
    - Reducing RAM requirements for large embedding tables
    
    File Format:
        Header (32 bytes):
            - Magic number: "ENGR" (4 bytes)
            - Version: uint32 (4 bytes)
            - Num embeddings: uint64 (8 bytes)
            - Embedding dim: uint64 (8 bytes)
            - Padding: 8 bytes
        Data: embeddings array
    """
    
    HEADER_SIZE = 32  # bytes for metadata
    MAGIC_NUMBER = b"ENGR"  # File signature
    VERSION = 1
    
    def __init__(
        self,
        path: Path | str,
        num_embeddings: int | None = None,
        embedding_dim: int | None = None,
        dtype: np.dtype = np.float32,
        mode: str = "r+",
        init_method: str = "normal",
        init_scale: float = 0.02,
    ) -> None:
        """Initialize memory-mapped storage.
        
        Args:
            path: Path to the storage file
            num_embeddings: Number of embeddings (required for new file)
            embedding_dim: Embedding dimension (required for new file)
            dtype: Data type for storage
            mode: File mode ('r+' for existing, 'w+' for new)
            init_method: Initialization method for new file
            init_scale: Scale factor for initialization
        """
        self._path = Path(path)
        self._dtype = dtype
        self._file = None
        self._mmap = None
        self._array = None
        
        if mode == "w+" or not self._path.exists():
            if num_embeddings is None or embedding_dim is None:
                raise ValueError(
                    "num_embeddings and embedding_dim required for new file"
                )
            self._create_new(num_embeddings, embedding_dim, init_method, init_scale)
        else:
            self._open_existing()
    
    def _create_new(
        self,
        num_embeddings: int,
        embedding_dim: int,
        init_method: str,
        init_scale: float,
    ) -> None:
        """Create a new storage file."""
        self._num_embeddings = num_embeddings
        self._embedding_dim = embedding_dim
        
        # Calculate file size
        element_size = np.dtype(self._dtype).itemsize
        data_size = num_embeddings * embedding_dim * element_size
        total_size = self.HEADER_SIZE + data_size
        
        # Create file with proper size
        self._path.parent.mkdir(parents=True, exist_ok=True)
        
        with open(self._path, "wb") as f:
            # Write header
            f.write(self.MAGIC_NUMBER)
            f.write(struct.pack("<I", self.VERSION))
            f.write(struct.pack("<Q", num_embeddings))
            f.write(struct.pack("<Q", embedding_dim))
            # Pad to HEADER_SIZE
            f.write(b"\x00" * (self.HEADER_SIZE - 24))
            # Write initial data
            f.write(b"\x00" * data_size)
        
        # Open for read/write
        self._file = open(self._path, "r+b")
        self._mmap = mmap.mmap(self._file.fileno(), 0)
        self._array = np.ndarray(
            shape=(num_embeddings, embedding_dim),
            dtype=self._dtype,
            buffer=self._mmap,
            offset=self.HEADER_SIZE,
        )
        
        # Initialize values
        temp = InMemoryStorage(
            num_embeddings, embedding_dim, self._dtype, init_method, init_scale
        )
        self._array[:] = temp.load_all()
        temp.close()
        
        self._mmap.flush()
        
        logger.info(
            f"Created MMapStorage: {self._path}, "
            f"{num_embeddings} x {embedding_dim}, "
            f"size={total_size / 1e9:.2f} GB"
        )
    
    def _open_existing(self) -> None:
        """Open an existing storage file."""
        self._file = open(self._path, "r+b")
        
        # Read header
        magic = self._file.read(4)
        if magic != self.MAGIC_NUMBER:
            raise ValueError(f"Invalid file format: {self._path}")
        
        version = struct.unpack("<I", self._file.read(4))[0]
        if version > self.VERSION:
            raise ValueError(f"Unsupported version: {version}")
        
        self._num_embeddings = struct.unpack("<Q", self._file.read(8))[0]
        self._embedding_dim = struct.unpack("<Q", self._file.read(8))[0]
        
        # Memory map
        self._mmap = mmap.mmap(self._file.fileno(), 0)
        self._array = np.ndarray(
            shape=(self._num_embeddings, self._embedding_dim),
            dtype=self._dtype,
            buffer=self._mmap,
            offset=self.HEADER_SIZE,
        )
        
        logger.info(
            f"Opened MMapStorage: {self._path}, "
            f"{self._num_embeddings} x {self._embedding_dim}"
        )
    
    def store(self, embeddings: np.ndarray) -> None:
        """Store embeddings (replace entire table).
        
        Args:
            embeddings: Full embedding table to store
        """
        if embeddings.shape != self._array.shape:
            raise ValueError(
                f"Shape mismatch: expected {self._array.shape}, "
                f"got {embeddings.shape}"
            )
        self._array[:] = embeddings.astype(self._dtype)
        self._mmap.flush()
    
    def load(self, indices: np.ndarray) -> np.ndarray:
        """Load embeddings by indices.
        
        Args:
            indices: Indices to load
            
        Returns:
            Embeddings at specified indices
        """
        return self._array[indices].copy()
    
    def load_all(self) -> np.ndarray:
        """Load all embeddings.
        
        Returns:
            Full embedding table
        """
        return self._array[:].copy()
    
    def update(self, indices: np.ndarray, embeddings: np.ndarray) -> None:
        """Update specific embeddings.
        
        Args:
            indices: Indices to update
            embeddings: New embedding values
        """
        self._array[indices] = embeddings.astype(self._dtype)
        self._mmap.flush()
    
    def close(self) -> None:
        """Close the storage and release resources."""
        if self._mmap:
            self._mmap.flush()
            self._mmap.close()
        if self._file:
            self._file.close()
    
    @property
    def shape(self) -> tuple[int, int]:
        """Get shape of the embedding table.
        
        Returns:
            Tuple of (num_embeddings, embedding_dim)
        """
        return (self._num_embeddings, self._embedding_dim)


__all__ = ["MMapStorage"]
