"""
Local LLM implementation for PersonaLab.

This module provides integration with local LLM models through Ollama or Hugging Face transformers.
"""

import json
import requests
from typing import Any, Dict, Optional

try:
    from transformers import AutoTokenizer, AutoModelForCausalLM, pipeline
    import torch
    HF_AVAILABLE = True
except ImportError:
    HF_AVAILABLE = False

from .base import BaseLLM, LLMResponse


class LocalLLM(BaseLLM):
    """Local LLM implementation supporting Ollama and Hugging Face models."""
    
    def __init__(
        self, 
        model_name: str,
        backend: str = "ollama",
        ollama_url: str = "http://localhost:11434",
        device: str = "auto",
        **kwargs
    ):
        """
        Initialize Local LLM.
        
        Args:
            model_name: Name of the local model
            backend: Backend to use ('ollama' or 'huggingface')
            ollama_url: URL of Ollama server (for ollama backend)
            device: Device to use for HuggingFace models ('cpu', 'cuda', 'auto')
            **kwargs: Additional configuration options
        """
        # Set backend first before calling super()
        self.backend = backend.lower()
        self.ollama_url = ollama_url.rstrip('/')
        
        super().__init__(model_name, **kwargs)
        
        # Initialize backend after basic setup
        try:
            if self.backend == "ollama":
                self._init_ollama()
            elif self.backend == "huggingface":
                if not HF_AVAILABLE:
                    raise ImportError("Hugging Face transformers not available. Install with: pip install transformers torch")
                self._init_huggingface(device)
            else:
                raise ValueError(f"Unsupported backend: {backend}. Use 'ollama' or 'huggingface'")
        except Exception as e:
            # If initialization fails, we still want the object to exist but be marked as unavailable
            print(f"Warning: LocalLLM initialization failed: {e}")
            self._init_failed = True
    
    def _init_ollama(self):
        """Initialize Ollama backend."""
        try:
            # Test connection to Ollama
            response = requests.get(f"{self.ollama_url}/api/tags", timeout=5)
            if response.status_code != 200:
                raise ConnectionError(f"Cannot connect to Ollama at {self.ollama_url}")
            
            # Check if model exists
            models = response.json().get('models', [])
            model_names = [model['name'] for model in models]
            if self.model_name not in model_names:
                print(f"Warning: Model '{self.model_name}' not found in Ollama. Available models: {model_names}")
        except Exception as e:
            print(f"Warning: Could not verify Ollama connection: {e}")
    
    def _init_huggingface(self, device: str):
        """Initialize Hugging Face backend."""
        try:
            # Set device
            if device == "auto":
                self.device = "cuda" if torch.cuda.is_available() else "cpu"
            else:
                self.device = device
            
            # Initialize tokenizer and model
            self.tokenizer = AutoTokenizer.from_pretrained(self.model_name)
            self.model = AutoModelForCausalLM.from_pretrained(
                self.model_name,
                torch_dtype=torch.float16 if self.device == "cuda" else torch.float32,
                device_map=self.device if self.device == "cuda" else None
            )
            
            # Create text generation pipeline
            self.pipeline = pipeline(
                "text-generation",
                model=self.model,
                tokenizer=self.tokenizer,
                device=0 if self.device == "cuda" else -1
            )
            
        except Exception as e:
            raise RuntimeError(f"Failed to initialize Hugging Face model: {e}")
    
    def _get_provider_name(self) -> str:
        """Return the provider name."""
        return f"Local-{self.backend.title()}"
    
    def generate(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
        **kwargs
    ) -> LLMResponse:
        """
        Generate a response using the local LLM.
        
        Args:
            prompt: The user prompt/message
            system_prompt: Optional system prompt for context
            temperature: Sampling temperature (0.0 to 1.0)
            max_tokens: Maximum tokens to generate
            **kwargs: Additional parameters
            
        Returns:
            LLMResponse object containing the generated content and metadata
        """
        if self.backend == "ollama":
            return self._generate_ollama(prompt, system_prompt, temperature, max_tokens, **kwargs)
        else:
            return self._generate_huggingface(prompt, system_prompt, temperature, max_tokens, **kwargs)
    
    def _generate_ollama(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
        **kwargs
    ) -> LLMResponse:
        """Generate response using Ollama."""
        # Prepare full prompt
        full_prompt = prompt
        if system_prompt:
            full_prompt = f"{system_prompt}\n\nUser: {prompt}\nAssistant:"
        
        # Prepare request data
        data = {
            "model": self.model_name,
            "prompt": full_prompt,
            "stream": False,
            "options": {
                "temperature": temperature,
                **kwargs
            }
        }
        
        if max_tokens:
            data["options"]["num_predict"] = max_tokens
        
        # Make request with timing
        response, response_time = self._measure_time(
            requests.post,
            f"{self.ollama_url}/api/generate",
            json=data,
            timeout=120
        )
        
        if response.status_code != 200:
            raise RuntimeError(f"Ollama request failed: {response.status_code} - {response.text}")
        
        result = response.json()
        content = result.get("response", "")
        
        # Prepare metadata
        metadata = {
            "total_duration": result.get("total_duration"),
            "load_duration": result.get("load_duration"),
            "prompt_eval_count": result.get("prompt_eval_count"),
            "prompt_eval_duration": result.get("prompt_eval_duration"),
            "eval_count": result.get("eval_count"),
            "eval_duration": result.get("eval_duration")
        }
        
        # Prepare usage information
        usage = {
            "prompt_tokens": result.get("prompt_eval_count", 0),
            "completion_tokens": result.get("eval_count", 0),
            "total_tokens": result.get("prompt_eval_count", 0) + result.get("eval_count", 0)
        }
        
        return LLMResponse(
            content=content,
            model=self.model_name,
            provider=self.provider_name,
            usage=usage,
            response_time=response_time,
            metadata=metadata
        )
    
    def _generate_huggingface(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
        **kwargs
    ) -> LLMResponse:
        """Generate response using Hugging Face transformers."""
        # Prepare full prompt
        full_prompt = prompt
        if system_prompt:
            full_prompt = f"{system_prompt}\n\nUser: {prompt}\nAssistant:"
        
        # Generate response with timing
        generation_kwargs = {
            "max_new_tokens": max_tokens or 512,
            "temperature": temperature,
            "do_sample": temperature > 0,
            "pad_token_id": self.tokenizer.eos_token_id,
            **kwargs
        }
        
        result, response_time = self._measure_time(
            self.pipeline,
            full_prompt,
            **generation_kwargs
        )
        
        # Extract generated text
        generated_text = result[0]["generated_text"]
        # Remove the input prompt from the output
        content = generated_text[len(full_prompt):].strip()
        
        # Prepare usage information (approximate)
        prompt_tokens = len(self.tokenizer.encode(full_prompt))
        completion_tokens = len(self.tokenizer.encode(content))
        
        usage = {
            "prompt_tokens": prompt_tokens,
            "completion_tokens": completion_tokens,
            "total_tokens": prompt_tokens + completion_tokens
        }
        
        # Prepare metadata
        metadata = {
            "device": self.device,
            "torch_dtype": str(self.model.dtype) if hasattr(self.model, 'dtype') else None
        }
        
        return LLMResponse(
            content=content,
            model=self.model_name,
            provider=self.provider_name,
            usage=usage,
            response_time=response_time,
            metadata=metadata
        )
    
    def generate_with_memory(
        self,
        prompt: str,
        memory_context: Dict[str, Any],
        system_prompt: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
        **kwargs
    ) -> LLMResponse:
        """
        Generate a response using memory context.
        
        Args:
            prompt: The user prompt/message
            memory_context: Memory search results to include as context
            system_prompt: Optional system prompt for context
            temperature: Sampling temperature (0.0 to 1.0)
            max_tokens: Maximum tokens to generate
            **kwargs: Additional parameters
            
        Returns:
            LLMResponse object containing the generated content and metadata
        """
        # Format memory context
        memory_text = self._format_memory_context(memory_context)
        
        # Enhance system prompt with memory context
        enhanced_system_prompt = system_prompt or ""
        if memory_text:
            enhanced_system_prompt += f"\n\nRELEVANT MEMORY CONTEXT:\n{memory_text}"
        
        return self.generate(
            prompt=prompt,
            system_prompt=enhanced_system_prompt,
            temperature=temperature,
            max_tokens=max_tokens,
            **kwargs
        )
    
    def list_available_models(self) -> list:
        """List available models."""
        if self.backend == "ollama":
            try:
                response = requests.get(f"{self.ollama_url}/api/tags", timeout=5)
                if response.status_code == 200:
                    models = response.json().get('models', [])
                    return [model['name'] for model in models]
            except Exception:
                pass
            return []
        else:
            # For HuggingFace, we can't easily list all available models
            return ["Meta-Llama-2-7b-chat-hf", "Meta-Llama-2-13b-chat-hf", "codellama/CodeLlama-7b-Instruct-hf"]
    
    def is_available(self) -> bool:
        """Check if the local LLM is available and working."""
        try:
            # Check if initialization failed
            if hasattr(self, '_init_failed') and self._init_failed:
                return False
                
            if not hasattr(self, 'backend'):
                return False
                
            if self.backend == "ollama":
                response = requests.get(f"{self.ollama_url}/api/tags", timeout=5)
                return response.status_code == 200
            else:
                # For HuggingFace, check if model is loaded
                return hasattr(self, 'model') and self.model is not None
        except Exception:
            return False 