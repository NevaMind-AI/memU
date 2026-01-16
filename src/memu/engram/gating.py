"""
Gating and Fusion Module for Engram

This module provides the gating mechanism that controls how Engram
memories are fused with query representations.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any, Callable

import numpy as np

if TYPE_CHECKING:
    from memu.engram.settings import GatingConfig


# ============================================================================
# Activation Functions
# ============================================================================

class Activations:
    """Collection of activation functions for gating."""
    
    @staticmethod
    def sigmoid(x: np.ndarray) -> np.ndarray:
        """Numerically stable sigmoid."""
        # Clip to avoid overflow
        x = np.clip(x, -500, 500)
        return 1.0 / (1.0 + np.exp(-x))
    
    @staticmethod
    def softmax(x: np.ndarray, axis: int = -1) -> np.ndarray:
        """Numerically stable softmax."""
        x_max = np.max(x, axis=axis, keepdims=True)
        exp_x = np.exp(x - x_max)
        return exp_x / np.sum(exp_x, axis=axis, keepdims=True)
    
    @staticmethod
    def gelu(x: np.ndarray) -> np.ndarray:
        """Gaussian Error Linear Unit."""
        return 0.5 * x * (1.0 + np.tanh(np.sqrt(2.0 / np.pi) * (x + 0.044715 * x**3)))
    
    @staticmethod
    def silu(x: np.ndarray) -> np.ndarray:
        """Sigmoid Linear Unit (SiLU / Swish)."""
        return x * Activations.sigmoid(x)
    
    @staticmethod
    def relu(x: np.ndarray) -> np.ndarray:
        """Rectified Linear Unit."""
        return np.maximum(0, x)
    
    @staticmethod
    def tanh(x: np.ndarray) -> np.ndarray:
        """Hyperbolic tangent."""
        return np.tanh(x)


def get_activation(name: str) -> Callable[[np.ndarray], np.ndarray]:
    """Get activation function by name."""
    activations = {
        "sigmoid": Activations.sigmoid,
        "softmax": Activations.softmax,
        "gelu": Activations.gelu,
        "silu": Activations.silu,
        "relu": Activations.relu,
        "tanh": Activations.tanh,
    }
    if name not in activations:
        raise ValueError(f"Unknown activation: {name}")
    return activations[name]


# ============================================================================
# Normalization
# ============================================================================

class LayerNorm:
    """Layer normalization for numpy arrays.
    
    Normalizes across the last dimension with learnable parameters.
    """
    
    def __init__(
        self,
        hidden_dim: int,
        eps: float = 1e-6,
    ) -> None:
        """Initialize layer normalization.
        
        Args:
            hidden_dim: Dimension to normalize
            eps: Small constant for numerical stability
        """
        self.hidden_dim = hidden_dim
        self.eps = eps
        
        # Learnable parameters
        self.weight = np.ones(hidden_dim, dtype=np.float32)
        self.bias = np.zeros(hidden_dim, dtype=np.float32)
    
    def __call__(self, x: np.ndarray) -> np.ndarray:
        """Apply layer normalization.
        
        Args:
            x: Input array [..., hidden_dim]
            
        Returns:
            Normalized array
        """
        mean = np.mean(x, axis=-1, keepdims=True)
        var = np.var(x, axis=-1, keepdims=True)
        x_norm = (x - mean) / np.sqrt(var + self.eps)
        return x_norm * self.weight + self.bias
    
    def set_parameters(self, weight: np.ndarray, bias: np.ndarray) -> None:
        """Set learnable parameters."""
        self.weight = weight.astype(np.float32)
        self.bias = bias.astype(np.float32)


class RMSNorm:
    """Root Mean Square Layer Normalization.
    
    More efficient than standard LayerNorm, used in modern architectures.
    """
    
    def __init__(
        self,
        hidden_dim: int,
        eps: float = 1e-6,
    ) -> None:
        """Initialize RMS normalization.
        
        Args:
            hidden_dim: Dimension to normalize
            eps: Small constant for numerical stability
        """
        self.hidden_dim = hidden_dim
        self.eps = eps
        self.weight = np.ones(hidden_dim, dtype=np.float32)
    
    def __call__(self, x: np.ndarray) -> np.ndarray:
        """Apply RMS normalization.
        
        Args:
            x: Input array [..., hidden_dim]
            
        Returns:
            Normalized array
        """
        rms = np.sqrt(np.mean(x**2, axis=-1, keepdims=True) + self.eps)
        return x / rms * self.weight
    
    def set_weight(self, weight: np.ndarray) -> None:
        """Set scale weight."""
        self.weight = weight.astype(np.float32)


# ============================================================================
# Linear Projections
# ============================================================================

class Linear:
    """Linear projection layer."""
    
    def __init__(
        self,
        in_features: int,
        out_features: int,
        bias: bool = True,
        init_method: str = "xavier",
    ) -> None:
        """Initialize linear layer.
        
        Args:
            in_features: Input dimension
            out_features: Output dimension
            bias: Whether to include bias
            init_method: Weight initialization method
        """
        self.in_features = in_features
        self.out_features = out_features
        self.use_bias = bias
        
        # Initialize weights
        self.weight = self._init_weight(init_method)
        self.bias = np.zeros(out_features, dtype=np.float32) if bias else None
    
    def _init_weight(self, method: str) -> np.ndarray:
        """Initialize weight matrix."""
        if method == "xavier":
            bound = np.sqrt(6.0 / (self.in_features + self.out_features))
            return np.random.uniform(
                -bound, bound,
                (self.out_features, self.in_features)
            ).astype(np.float32)
        elif method == "kaiming":
            std = np.sqrt(2.0 / self.in_features)
            return np.random.randn(
                self.out_features, self.in_features
            ).astype(np.float32) * std
        elif method == "normal":
            return np.random.randn(
                self.out_features, self.in_features
            ).astype(np.float32) * 0.02
        else:
            raise ValueError(f"Unknown init method: {method}")
    
    def __call__(self, x: np.ndarray) -> np.ndarray:
        """Apply linear projection.
        
        Args:
            x: Input array [..., in_features]
            
        Returns:
            Projected array [..., out_features]
        """
        result = np.matmul(x, self.weight.T)
        if self.use_bias:
            result = result + self.bias
        return result
    
    def set_parameters(
        self,
        weight: np.ndarray,
        bias: np.ndarray | None = None,
    ) -> None:
        """Set layer parameters."""
        self.weight = weight.astype(np.float32)
        if bias is not None and self.use_bias:
            self.bias = bias.astype(np.float32)


# ============================================================================
# Gating Mechanisms
# ============================================================================

@dataclass
class GatingResult:
    """Result of gating computation.
    
    Attributes:
        gates: Gate values [batch, seq_len, num_channels]
        gated_memory: Memory weighted by gates
        raw_scores: Raw similarity scores before activation
        metadata: Optional metadata
    """
    gates: np.ndarray
    gated_memory: np.ndarray
    raw_scores: np.ndarray
    metadata: dict[str, Any] = field(default_factory=dict)


class EngramGating:
    """Gating mechanism for Engram memory fusion.
    
    This class implements the core gating mechanism that determines
    how much of the retrieved Engram memory to incorporate into
    the output representation.
    
    The gating formula:
        score = (K · Q) / sqrt(d)           # Dot product attention
        gate = sigmoid(sign(score) * sqrt(|score|))  # Engram gate
        output = gate * V
    
    Features:
        - Query-Key matching for relevance scoring
        - Non-linear gate transformation
        - Multi-channel gating support
        - Learnable projections
    """
    
    def __init__(
        self,
        input_dim: int,
        memory_dim: int,
        output_dim: int,
        num_channels: int = 1,
        config: "GatingConfig | None" = None,
    ) -> None:
        """Initialize gating mechanism.
        
        Args:
            input_dim: Dimension of input (query) features
            memory_dim: Dimension of memory (Engram) features
            output_dim: Dimension of output
            num_channels: Number of gating channels
            config: Gating configuration
        """
        if config is None:
            from memu.engram.settings import GatingConfig
            config = GatingConfig()
        
        self.config = config
        self.input_dim = input_dim
        self.memory_dim = memory_dim
        self.output_dim = output_dim
        self.num_channels = num_channels
        
        # Initialize projections
        self._init_projections()
        
        # Get activation function
        self.activation = get_activation(config.activation)
    
    def _init_projections(self) -> None:
        """Initialize projection layers."""
        # Key projection (memory -> hidden)
        self.key_projs: list[Linear] = []
        for _ in range(self.num_channels):
            self.key_projs.append(Linear(
                self.memory_dim,
                self.config.hidden_dim,
            ))
        
        # Value projection (memory -> output)
        self.value_proj = Linear(self.memory_dim, self.output_dim)
        
        # Normalization layers
        if self.config.use_layer_norm:
            self.key_norms: list[RMSNorm] = []
            self.query_norms: list[RMSNorm] = []
            for _ in range(self.num_channels):
                self.key_norms.append(RMSNorm(
                    self.config.hidden_dim,
                    eps=self.config.norm_eps,
                ))
                self.query_norms.append(RMSNorm(
                    self.config.hidden_dim,
                    eps=self.config.norm_eps,
                ))
    
    def _compute_gate(
        self,
        query: np.ndarray,
        key: np.ndarray,
        channel_idx: int,
    ) -> tuple[np.ndarray, np.ndarray]:
        """Compute gate values for a single channel.
        
        Args:
            query: Query features [..., hidden_dim]
            key: Key features [..., hidden_dim]
            channel_idx: Channel index
            
        Returns:
            Tuple of (gate values, raw scores)
        """
        # Normalize
        if self.config.use_layer_norm:
            key = self.key_norms[channel_idx](key)
            query = self.query_norms[channel_idx](query)
        
        # Compute similarity (dot product)
        score = np.sum(key * query, axis=-1)
        score = score / math.sqrt(self.config.hidden_dim)
        
        # Apply temperature
        score = score / self.config.temperature
        
        # Engram-style gate transformation
        if self.config.sqrt_scaling:
            # gate = sigmoid(sign(score) * sqrt(|score|))
            abs_score = np.abs(score)
            abs_score = np.clip(abs_score, self.config.gate_min, None)
            sqrt_score = np.sqrt(abs_score)
            sign_score = np.sign(score)
            transformed = sign_score * sqrt_score
        else:
            transformed = score
        
        # Apply activation
        if self.config.activation == "softmax":
            gate = self.activation(transformed)
        else:
            gate = self.activation(transformed)
        
        return gate, score
    
    def forward(
        self,
        query: np.ndarray,
        memory: np.ndarray,
    ) -> GatingResult:
        """Compute gated memory output.
        
        Args:
            query: Query features [batch, seq_len, input_dim] or
                   [batch, seq_len, num_channels, channel_dim]
            memory: Memory features [batch, seq_len, memory_dim]
            
        Returns:
            GatingResult with gated output
        """
        # Handle multi-channel query
        if query.ndim == 4:
            batch, seq_len, num_ch, ch_dim = query.shape
            assert num_ch == self.num_channels
            multi_channel_query = True
        else:
            batch, seq_len, _ = query.shape
            multi_channel_query = False
        
        # Compute value projection (shared across channels)
        value = self.value_proj(memory)  # [batch, seq_len, output_dim]
        
        # Compute gates for each channel
        all_gates = []
        all_scores = []
        
        for ch_idx in range(self.num_channels):
            # Get query for this channel
            if multi_channel_query:
                ch_query = query[:, :, ch_idx, :]
            else:
                ch_query = query
            
            # Project memory to key space
            key = self.key_projs[ch_idx](memory)
            
            # Ensure query has correct dimension for matching
            if ch_query.shape[-1] != self.config.hidden_dim:
                # Need to project query as well
                if not hasattr(self, "query_projs"):
                    self.query_projs = [
                        Linear(ch_query.shape[-1], self.config.hidden_dim)
                        for _ in range(self.num_channels)
                    ]
                ch_query = self.query_projs[ch_idx](ch_query)
            
            # Compute gate
            gate, score = self._compute_gate(ch_query, key, ch_idx)
            all_gates.append(gate)
            all_scores.append(score)
        
        # Stack gates [batch, seq_len, num_channels]
        gates = np.stack(all_gates, axis=-1)
        raw_scores = np.stack(all_scores, axis=-1)
        
        # Apply gates to value
        # Expand gates for broadcasting: [batch, seq_len, num_channels, 1]
        gates_expanded = gates[..., np.newaxis]
        
        # Expand value for channels: [batch, seq_len, 1, output_dim]
        value_expanded = value[:, :, np.newaxis, :]
        
        # Gated output: [batch, seq_len, num_channels, output_dim]
        gated_memory = gates_expanded * value_expanded
        
        return GatingResult(
            gates=gates,
            gated_memory=gated_memory,
            raw_scores=raw_scores,
            metadata={
                "batch_size": batch,
                "seq_len": seq_len,
                "num_channels": self.num_channels,
            },
        )
    
    def __call__(
        self,
        query: np.ndarray,
        memory: np.ndarray,
    ) -> GatingResult:
        """Callable interface for forward pass."""
        return self.forward(query, memory)
    
    def get_parameters(self) -> dict[str, np.ndarray]:
        """Get all learnable parameters.
        
        Returns:
            Dictionary of parameter name to values
        """
        params = {}
        
        for ch_idx, proj in enumerate(self.key_projs):
            params[f"key_proj_{ch_idx}_weight"] = proj.weight
            if proj.bias is not None:
                params[f"key_proj_{ch_idx}_bias"] = proj.bias
        
        params["value_proj_weight"] = self.value_proj.weight
        if self.value_proj.bias is not None:
            params["value_proj_bias"] = self.value_proj.bias
        
        if self.config.use_layer_norm:
            for ch_idx, norm in enumerate(self.key_norms):
                params[f"key_norm_{ch_idx}_weight"] = norm.weight
            for ch_idx, norm in enumerate(self.query_norms):
                params[f"query_norm_{ch_idx}_weight"] = norm.weight
        
        if hasattr(self, "query_projs"):
            for ch_idx, proj in enumerate(self.query_projs):
                params[f"query_proj_{ch_idx}_weight"] = proj.weight
                if proj.bias is not None:
                    params[f"query_proj_{ch_idx}_bias"] = proj.bias
        
        return params
    
    def set_parameters(self, params: dict[str, np.ndarray]) -> None:
        """Set learnable parameters.
        
        Args:
            params: Dictionary of parameter name to values
        """
        for ch_idx, proj in enumerate(self.key_projs):
            key_w = params.get(f"key_proj_{ch_idx}_weight")
            key_b = params.get(f"key_proj_{ch_idx}_bias")
            if key_w is not None:
                proj.set_parameters(key_w, key_b)
        
        val_w = params.get("value_proj_weight")
        val_b = params.get("value_proj_bias")
        if val_w is not None:
            self.value_proj.set_parameters(val_w, val_b)
        
        if self.config.use_layer_norm:
            for ch_idx, norm in enumerate(self.key_norms):
                w = params.get(f"key_norm_{ch_idx}_weight")
                if w is not None:
                    norm.set_weight(w)
            for ch_idx, norm in enumerate(self.query_norms):
                w = params.get(f"query_norm_{ch_idx}_weight")
                if w is not None:
                    norm.set_weight(w)


class SimpleGating:
    """Simplified gating for non-query-based memory retrieval.
    
    Uses only the memory features to compute gate values,
    suitable for standalone Engram retrieval without a query.
    """
    
    def __init__(
        self,
        memory_dim: int,
        output_dim: int,
        config: "GatingConfig | None" = None,
    ) -> None:
        """Initialize simple gating.
        
        Args:
            memory_dim: Dimension of memory features
            output_dim: Dimension of output
            config: Gating configuration
        """
        if config is None:
            from memu.engram.settings import GatingConfig
            config = GatingConfig()
        
        self.config = config
        self.memory_dim = memory_dim
        self.output_dim = output_dim
        
        # Gate projection
        self.gate_proj = Linear(memory_dim, 1)
        
        # Value projection
        self.value_proj = Linear(memory_dim, output_dim)
        
        # Activation
        self.activation = get_activation(config.activation)
    
    def forward(self, memory: np.ndarray) -> GatingResult:
        """Compute gated memory output.
        
        Args:
            memory: Memory features [batch, seq_len, memory_dim]
            
        Returns:
            GatingResult with gated output
        """
        # Compute gate scores
        raw_scores = self.gate_proj(memory).squeeze(-1)  # [batch, seq_len]
        
        # Apply temperature
        scores = raw_scores / self.config.temperature
        
        # Apply activation
        gates = self.activation(scores)  # [batch, seq_len]
        
        # Compute value
        value = self.value_proj(memory)  # [batch, seq_len, output_dim]
        
        # Apply gates
        gates_expanded = gates[..., np.newaxis]  # [batch, seq_len, 1]
        gated_memory = gates_expanded * value  # [batch, seq_len, output_dim]
        
        return GatingResult(
            gates=gates,
            gated_memory=gated_memory,
            raw_scores=raw_scores,
            metadata={},
        )
    
    def __call__(self, memory: np.ndarray) -> GatingResult:
        """Callable interface."""
        return self.forward(memory)


# ============================================================================
# Short Convolution for Local Enhancement
# ============================================================================

class ShortConv1D:
    """1D convolution for local context enhancement.
    
    Applies dilated causal convolution to enhance local patterns
    in the gated memory output.
    """
    
    def __init__(
        self,
        channels: int,
        kernel_size: int = 4,
        dilation: int = 1,
        groups: int | None = None,
    ) -> None:
        """Initialize 1D convolution.
        
        Args:
            channels: Number of input/output channels
            kernel_size: Convolution kernel size
            dilation: Dilation factor
            groups: Number of groups for grouped convolution
        """
        self.channels = channels
        self.kernel_size = kernel_size
        self.dilation = dilation
        self.groups = groups or channels  # Default to depthwise
        
        # Initialize kernel [groups, kernel_size]
        # For depthwise: one filter per channel
        self.kernel = np.random.randn(
            self.groups, kernel_size
        ).astype(np.float32) * 0.02
    
    def forward(self, x: np.ndarray) -> np.ndarray:
        """Apply 1D convolution.
        
        Args:
            x: Input [batch, seq_len, channels]
            
        Returns:
            Convolved output [batch, seq_len, channels]
        """
        batch, seq_len, channels = x.shape
        
        # Compute effective kernel size with dilation
        effective_k = (self.kernel_size - 1) * self.dilation + 1
        
        # Causal padding (left only)
        padding = effective_k - 1
        x_padded = np.pad(x, ((0, 0), (padding, 0), (0, 0)), mode='constant')
        
        # Apply depthwise convolution
        output = np.zeros_like(x)
        
        channels_per_group = channels // self.groups
        for g in range(self.groups):
            ch_start = g * channels_per_group
            ch_end = (g + 1) * channels_per_group
            
            for k in range(self.kernel_size):
                offset = k * self.dilation
                output[:, :, ch_start:ch_end] += (
                    x_padded[:, offset:offset + seq_len, ch_start:ch_end] *
                    self.kernel[g, k]
                )
        
        return output
    
    def __call__(self, x: np.ndarray) -> np.ndarray:
        """Callable interface."""
        return self.forward(x)


__all__ = [
    "EngramGating",
    "SimpleGating",
    "GatingResult",
    "ShortConv1D",
    "Linear",
    "LayerNorm",
    "RMSNorm",
    "Activations",
    "get_activation",
]
