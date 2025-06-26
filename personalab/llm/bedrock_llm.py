"""
AWS Bedrock LLM implementation for PersonaLab.

This module provides support for AWS Bedrock models including Claude, Llama, and others.
"""

import os
import time
import json
from typing import Dict, List, Optional, Any, AsyncGenerator

try:
    import boto3
    from botocore.exceptions import ClientError
    BEDROCK_AVAILABLE = True
except ImportError:
    BEDROCK_AVAILABLE = False
    boto3 = None
    ClientError = Exception

from .base import BaseLLM, LLMResponse


class BedrockLLM(BaseLLM):
    """
    AWS Bedrock LLM implementation.
    
    Supports Bedrock models like:
    - anthropic.claude-3-sonnet-20240229-v1:0
    - anthropic.claude-3-haiku-20240307-v1:0
    - anthropic.claude-instant-v1
    - meta.llama2-70b-chat-v1
    - amazon.titan-text-express-v1
    """
    
    def __init__(self, 
                 model: str = "anthropic.claude-3-sonnet-20240229-v1:0",
                 region_name: str = "us-east-1",
                 aws_access_key_id: Optional[str] = None,
                 aws_secret_access_key: Optional[str] = None,
                 aws_session_token: Optional[str] = None,
                 temperature: float = 0.7,
                 max_tokens: Optional[int] = None,
                 top_p: float = 1.0,
                 **kwargs):
        """
        Initialize AWS Bedrock LLM.
        
        Args:
            model: Model ID (e.g., 'anthropic.claude-3-sonnet-20240229-v1:0')
            region_name: AWS region name
            aws_access_key_id: AWS access key ID
            aws_secret_access_key: AWS secret access key
            aws_session_token: AWS session token (for temporary credentials)
            temperature: Sampling temperature (0.0 to 1.0)
            max_tokens: Maximum tokens to generate
            top_p: Nucleus sampling parameter
            **kwargs: Additional model parameters
        """
        if not BEDROCK_AVAILABLE:
            raise ImportError(
                "AWS SDK not available. Install with: "
                "pip install boto3"
            )
        
        super().__init__(model=model, temperature=temperature, max_tokens=max_tokens, **kwargs)
        
        # Set up AWS credentials
        self.region_name = region_name
        self.aws_access_key_id = aws_access_key_id or os.getenv("AWS_ACCESS_KEY_ID")
        self.aws_secret_access_key = aws_secret_access_key or os.getenv("AWS_SECRET_ACCESS_KEY")
        self.aws_session_token = aws_session_token or os.getenv("AWS_SESSION_TOKEN")
        
        # Model parameters
        self.temperature = temperature
        self.max_tokens = max_tokens or 4096
        self.top_p = top_p
        self.kwargs = kwargs
        
        # Initialize Bedrock client
        session_params = {
            "region_name": self.region_name
        }
        
        if self.aws_access_key_id and self.aws_secret_access_key:
            session_params.update({
                "aws_access_key_id": self.aws_access_key_id,
                "aws_secret_access_key": self.aws_secret_access_key
            })
            if self.aws_session_token:
                session_params["aws_session_token"] = self.aws_session_token
        
        session = boto3.Session(**session_params)
        self._client = session.client("bedrock-runtime")
    
    def _prepare_request_body(self, prompt: str, **kwargs) -> str:
        """Prepare request body based on model provider."""
        model_provider = self.model.split(".")[0]
        
        if model_provider == "anthropic":
            # Claude models
            return json.dumps({
                "anthropic_version": "bedrock-2023-05-31",
                "max_tokens": kwargs.get("max_tokens", self.max_tokens),
                "messages": [{"role": "user", "content": prompt}],
                "temperature": kwargs.get("temperature", self.temperature),
                "top_p": kwargs.get("top_p", self.top_p)
            })
        
        elif model_provider == "meta":
            # Llama models
            return json.dumps({
                "prompt": prompt,
                "max_gen_len": kwargs.get("max_tokens", self.max_tokens),
                "temperature": kwargs.get("temperature", self.temperature),
                "top_p": kwargs.get("top_p", self.top_p)
            })
        
        elif model_provider == "amazon":
            # Titan models
            return json.dumps({
                "inputText": prompt,
                "textGenerationConfig": {
                    "maxTokenCount": kwargs.get("max_tokens", self.max_tokens),
                    "temperature": kwargs.get("temperature", self.temperature),
                    "topP": kwargs.get("top_p", self.top_p)
                }
            })
        
        else:
            # Generic format
            return json.dumps({
                "prompt": prompt,
                "max_tokens": kwargs.get("max_tokens", self.max_tokens),
                "temperature": kwargs.get("temperature", self.temperature),
                "top_p": kwargs.get("top_p", self.top_p)
            })
    
    def _extract_response_text(self, response_body: Dict[str, Any]) -> str:
        """Extract response text based on model provider."""
        model_provider = self.model.split(".")[0]
        
        if model_provider == "anthropic":
            # Claude models
            return response_body.get("content", [{}])[0].get("text", "")
        
        elif model_provider == "meta":
            # Llama models
            return response_body.get("generation", "")
        
        elif model_provider == "amazon":
            # Titan models
            results = response_body.get("results", [{}])
            return results[0].get("outputText", "") if results else ""
        
        else:
            # Generic extraction
            return response_body.get("completion", response_body.get("text", str(response_body)))
    
    async def generate_async(self, 
                           prompt: str, 
                           system_prompt: Optional[str] = None,
                           memory_context: Optional[str] = None,
                           **kwargs) -> LLMResponse:
        """
        Generate response asynchronously using AWS Bedrock.
        
        Args:
            prompt: User prompt
            system_prompt: System prompt (will be prepended)
            memory_context: Memory context from PersonaLab
            **kwargs: Additional generation parameters
            
        Returns:
            LLMResponse object
        """
        start_time = time.time()
        
        try:
            # Construct full prompt
            full_prompt = self._construct_prompt(prompt, system_prompt, memory_context)
            
            # Prepare request body
            request_body = self._prepare_request_body(full_prompt, **kwargs)
            
            # Make API call
            response = self._client.invoke_model(
                modelId=self.model,
                body=request_body,
                contentType="application/json"
            )
            
            # Parse response
            response_body = json.loads(response["body"].read())
            content = self._extract_response_text(response_body)
            
            # Calculate tokens (approximate)
            prompt_tokens = self._estimate_tokens(full_prompt)
            completion_tokens = self._estimate_tokens(content)
            
            end_time = time.time()
            
            return LLMResponse(
                content=content,
                model=self.model,
                provider="bedrock",
                prompt_tokens=prompt_tokens,
                completion_tokens=completion_tokens,
                total_tokens=prompt_tokens + completion_tokens,
                response_time=end_time - start_time,
                finish_reason="stop"
            )
            
        except ClientError as e:
            end_time = time.time()
            error_code = e.response.get("Error", {}).get("Code", "Unknown")
            error_message = e.response.get("Error", {}).get("Message", str(e))
            
            return LLMResponse(
                content=f"AWS Error [{error_code}]: {error_message}",
                model=self.model,
                provider="bedrock",
                prompt_tokens=0,
                completion_tokens=0,
                total_tokens=0,
                response_time=end_time - start_time,
                finish_reason="error"
            )
        
        except Exception as e:
            end_time = time.time()
            return LLMResponse(
                content=f"Error: {str(e)}",
                model=self.model,
                provider="bedrock",
                prompt_tokens=0,
                completion_tokens=0,
                total_tokens=0,
                response_time=end_time - start_time,
                finish_reason="error"
            )
    
    def generate(self, 
                prompt: str, 
                system_prompt: Optional[str] = None,
                memory_context: Optional[str] = None,
                **kwargs) -> LLMResponse:
        """
        Generate response synchronously using AWS Bedrock.
        
        Args:
            prompt: User prompt
            system_prompt: System prompt (will be prepended)
            memory_context: Memory context from PersonaLab
            **kwargs: Additional generation parameters
            
        Returns:
            LLMResponse object
        """
        start_time = time.time()
        
        try:
            # Construct full prompt
            full_prompt = self._construct_prompt(prompt, system_prompt, memory_context)
            
            # Prepare request body
            request_body = self._prepare_request_body(full_prompt, **kwargs)
            
            # Make API call
            response = self._client.invoke_model(
                modelId=self.model,
                body=request_body,
                contentType="application/json"
            )
            
            # Parse response
            response_body = json.loads(response["body"].read())
            content = self._extract_response_text(response_body)
            
            # Calculate tokens (approximate)
            prompt_tokens = self._estimate_tokens(full_prompt)
            completion_tokens = self._estimate_tokens(content)
            
            end_time = time.time()
            
            return LLMResponse(
                content=content,
                model=self.model,
                provider="bedrock",
                prompt_tokens=prompt_tokens,
                completion_tokens=completion_tokens,
                total_tokens=prompt_tokens + completion_tokens,
                response_time=end_time - start_time,
                finish_reason="stop"
            )
            
        except ClientError as e:
            end_time = time.time()
            error_code = e.response.get("Error", {}).get("Code", "Unknown")
            error_message = e.response.get("Error", {}).get("Message", str(e))
            
            return LLMResponse(
                content=f"AWS Error [{error_code}]: {error_message}",
                model=self.model,
                provider="bedrock",
                prompt_tokens=0,
                completion_tokens=0,
                total_tokens=0,
                response_time=end_time - start_time,
                finish_reason="error"
            )
        
        except Exception as e:
            end_time = time.time()
            return LLMResponse(
                content=f"Error: {str(e)}",
                model=self.model,
                provider="bedrock",
                prompt_tokens=0,
                completion_tokens=0,
                total_tokens=0,
                response_time=end_time - start_time,
                finish_reason="error"
            )
    
    async def stream_async(self, 
                          prompt: str, 
                          system_prompt: Optional[str] = None,
                          memory_context: Optional[str] = None,
                          **kwargs) -> AsyncGenerator[str, None]:
        """
        Stream response asynchronously using AWS Bedrock.
        
        Note: Bedrock streaming support varies by model. This simulates streaming
        for models that don't support it natively.
        
        Args:
            prompt: User prompt
            system_prompt: System prompt (will be prepended)
            memory_context: Memory context from PersonaLab
            **kwargs: Additional generation parameters
            
        Yields:
            Streaming text chunks
        """
        try:
            # Generate complete response (streaming implementation would require invoke_model_with_response_stream)
            response = await self.generate_async(prompt, system_prompt, memory_context, **kwargs)
            
            # Simulate streaming by yielding chunks
            content = response.content
            chunk_size = 50  # Characters per chunk
            
            for i in range(0, len(content), chunk_size):
                chunk = content[i:i + chunk_size]
                yield chunk
                
        except Exception as e:
            yield f"Error: {str(e)}"
    
    def is_available(self) -> bool:
        """Check if AWS Bedrock is available."""
        try:
            # Test connectivity
            self._client.list_foundation_models(maxResults=1)
            return True
        except:
            return False
    
    def get_model_info(self) -> Dict[str, Any]:
        """Get information about the model."""
        return {
            "provider": "bedrock",
            "model": self.model,
            "region_name": self.region_name,
            "temperature": self.temperature,
            "max_tokens": self.max_tokens,
            "top_p": self.top_p,
            "available": self.is_available(),
            "supports_streaming": True,  # Via invoke_model_with_response_stream
            "supports_async": True
        } 