"""
Quantization Utilities for Engram Embeddings

Provides efficient quantization and dequantization for reducing
memory footprint of large embedding tables.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

import numpy as np

if TYPE_CHECKING:
    from memu.engram.settings import QuantizationType


class QuantizationHandler:
    """Handles quantization and dequantization of embeddings.
    
    Supported quantization types:
        - NONE: No quantization (FP32)
        - FP16: Half precision floating point
        - INT8: 8-bit symmetric quantization
        - INT4: 4-bit symmetric quantization with packing
    """
    
    @staticmethod
    def quantize(
        data: np.ndarray,
        quantization: "QuantizationType",
    ) -> tuple[np.ndarray, dict[str, Any]]:
        """Quantize embeddings to lower precision.
        
        Args:
            data: Float32 embeddings
            quantization: Target quantization type
            
        Returns:
            Tuple of (quantized data, metadata for dequantization)
        """
        from memu.engram.settings import QuantizationType
        
        if quantization == QuantizationType.NONE:
            return data.astype(np.float32), {}
        
        elif quantization == QuantizationType.FP16:
            return data.astype(np.float16), {}
        
        elif quantization == QuantizationType.INT8:
            # Symmetric quantization: map [-max, max] to [-127, 127]
            scale = np.abs(data).max() / 127.0
            if scale == 0:
                scale = 1.0
            quantized = np.round(data / scale).astype(np.int8)
            return quantized, {"scale": scale}
        
        elif quantization == QuantizationType.INT4:
            # Symmetric quantization: map [-max, max] to [-7, 7]
            # Pack two INT4 values per byte
            scale = np.abs(data).max() / 7.0
            if scale == 0:
                scale = 1.0
            quantized = np.round(data / scale).astype(np.int8)
            quantized = np.clip(quantized, -8, 7)
            
            # Pack pairs of values into bytes
            flat = quantized.flatten()
            if len(flat) % 2 != 0:
                flat = np.pad(flat, (0, 1), mode='constant')
            packed = ((flat[::2] & 0x0F) | ((flat[1::2] & 0x0F) << 4)).astype(np.uint8)
            return packed.reshape(-1), {"scale": scale, "original_shape": data.shape}
        
        else:
            raise ValueError(f"Unknown quantization type: {quantization}")
    
    @staticmethod
    def dequantize(
        data: np.ndarray,
        quantization: "QuantizationType",
        metadata: dict[str, Any],
    ) -> np.ndarray:
        """Dequantize embeddings to float32.
        
        Args:
            data: Quantized embeddings
            quantization: Quantization type
            metadata: Metadata from quantization
            
        Returns:
            Float32 embeddings
        """
        from memu.engram.settings import QuantizationType
        
        if quantization == QuantizationType.NONE:
            return data.astype(np.float32)
        
        elif quantization == QuantizationType.FP16:
            return data.astype(np.float32)
        
        elif quantization == QuantizationType.INT8:
            scale = metadata.get("scale", 1.0)
            return data.astype(np.float32) * scale
        
        elif quantization == QuantizationType.INT4:
            scale = metadata.get("scale", 1.0)
            original_shape = metadata.get("original_shape")
            
            # Unpack pairs of values from bytes
            unpacked = np.zeros(len(data) * 2, dtype=np.int8)
            unpacked[::2] = (data & 0x0F).astype(np.int8)
            unpacked[1::2] = ((data >> 4) & 0x0F).astype(np.int8)
            
            # Sign extend 4-bit to 8-bit
            unpacked = np.where(unpacked > 7, unpacked - 16, unpacked)
            
            result = unpacked.astype(np.float32) * scale
            if original_shape:
                result = result[:np.prod(original_shape)].reshape(original_shape)
            return result
        
        else:
            raise ValueError(f"Unknown quantization type: {quantization}")


__all__ = ["QuantizationHandler"]
