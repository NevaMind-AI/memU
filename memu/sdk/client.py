"""
MemU SDK HTTP Client

Provides HTTP client for interacting with MemU API services.
"""

import os
import logging
from typing import Optional, Dict, Any
from urllib.parse import urljoin

import httpx
from pydantic import ValidationError

from .models import MemorizeRequest, MemorizeResponse, MemorizeTaskStatusResponse
from .exceptions import (
    MemuAPIException,
    MemuValidationException, 
    MemuAuthenticationException,
    MemuConnectionException
)

logger = logging.getLogger(__name__)


class MemuClient:
    """HTTP client for MemU API services"""
    
    def __init__(
        self,
        base_url: str = None,
        api_key: str = None,
        timeout: float = 30.0,
        max_retries: int = 3,
        **kwargs
    ):
        """
        Initialize MemU SDK client
        
        Args:
            base_url: Base URL for MemU API server
            api_key: API key for authentication
            timeout: Request timeout in seconds
            max_retries: Maximum number of retries for failed requests
            **kwargs: Additional httpx client parameters
        """
        self.base_url = base_url or os.getenv("MEMU_API_BASE_URL", "http://localhost:8000")
        self.api_key = api_key or os.getenv("MEMU_API_KEY")
        self.timeout = timeout
        self.max_retries = max_retries
        
        if not self.base_url:
            raise ValueError("base_url is required. Set MEMU_API_BASE_URL environment variable or pass base_url parameter.")
        
        if not self.api_key:
            raise ValueError("api_key is required. Set MEMU_API_KEY environment variable or pass api_key parameter.")
        
        # Ensure base_url ends with /
        if not self.base_url.endswith('/'):
            self.base_url += '/'
        
        # Configure httpx client
        client_kwargs = {
            'timeout': self.timeout,
            'headers': {
                'User-Agent': 'MemU-Python-SDK/0.1.3',
                'Content-Type': 'application/json',
                'Accept': 'application/json',
                'Authorization': f'Bearer {self.api_key}',
            },
            **kwargs
        }
        
        self._client = httpx.Client(**client_kwargs)
        
        logger.info(f"MemU SDK client initialized with base_url: {self.base_url}")
    
    def __enter__(self):
        """Context manager entry"""
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit"""
        self.close()
    
    def close(self):
        """Close the HTTP client"""
        if hasattr(self, '_client'):
            self._client.close()
    
    def _make_request(
        self,
        method: str,
        endpoint: str,
        json_data: Dict[str, Any] = None,
        params: Dict[str, Any] = None,
        **kwargs
    ) -> Dict[str, Any]:
        """
        Make HTTP request with error handling and retries
        
        Args:
            method: HTTP method (GET, POST, etc.)
            endpoint: API endpoint (relative to base_url)
            json_data: JSON request body
            params: Query parameters
            **kwargs: Additional request parameters
            
        Returns:
            Dict[str, Any]: Response JSON data
            
        Raises:
            MemuAPIException: For API errors
            MemuConnectionException: For connection errors
        """
        url = urljoin(self.base_url, endpoint)
        
        # Prepare query parameters if provided
        if params is None:
            params = {}
        
        for attempt in range(self.max_retries + 1):
            try:
                logger.debug(f"Making {method} request to {url} (attempt {attempt + 1})")
                
                response = self._client.request(
                    method=method,
                    url=url,
                    json=json_data,
                    params=params,
                    **kwargs
                )
                
                # Handle HTTP status codes
                if response.status_code == 200:
                    return response.json()
                elif response.status_code == 422:
                    error_data = response.json()
                    raise MemuValidationException(
                        f"Validation error: {error_data}",
                        status_code=response.status_code,
                        response_data=error_data
                    )
                elif response.status_code == 401:
                    raise MemuAuthenticationException(
                        "Authentication failed. Check your API key.",
                        status_code=response.status_code
                    )
                elif response.status_code == 403:
                    raise MemuAuthenticationException(
                        "Access forbidden. Check your API key permissions.",
                        status_code=response.status_code
                    )
                else:
                    error_msg = f"API request failed with status {response.status_code}"
                    try:
                        error_data = response.json()
                        error_msg += f": {error_data}"
                    except:
                        error_msg += f": {response.text}"
                    
                    raise MemuAPIException(
                        error_msg,
                        status_code=response.status_code
                    )
                    
            except httpx.RequestError as e:
                if attempt == self.max_retries:
                    raise MemuConnectionException(f"Connection error after {self.max_retries + 1} attempts: {str(e)}")
                else:
                    logger.warning(f"Request failed (attempt {attempt + 1}), retrying: {str(e)}")
                    continue
            except (MemuAPIException, MemuValidationException, MemuAuthenticationException):
                # Don't retry these errors
                raise
    
    def memorize_conversation(
        self,
        conversation_text: str,
        user_id: str,
        user_name: str,
        agent_id: str,
        agent_name: str,
        project_id: str,
        api_key_id: str = None
    ) -> MemorizeResponse:
        """
        Start a Celery task to memorize conversation text with agent processing
        
        Args:
            conversation_text: Conversation text to memorize
            user_id: User identifier  
            user_name: User display name
            agent_id: Agent identifier
            agent_name: Agent display name
            project_id: Project identifier
            api_key_id: API key identifier (optional, uses client api_key if not provided)
            
        Returns:
            MemorizeResponse: Task ID and status for tracking the memorization process
            
        Raises:
            MemuValidationException: For validation errors
            MemuAPIException: For API errors
            MemuConnectionException: For connection errors
        """
        try:
            # Use provided api_key_id or fall back to client api_key
            request_api_key_id = api_key_id or self.api_key
            
            # Create request model
            request_data = MemorizeRequest(
                conversation_text=conversation_text,
                user_id=user_id,
                user_name=user_name,
                agent_id=agent_id,
                agent_name=agent_name,
                api_key_id=request_api_key_id,
                project_id=project_id
            )
            
            logger.info(f"Starting memorization for user {user_id} and agent {agent_id}")
            
            # Make API request
            response_data = self._make_request(
                method="POST",
                endpoint="api/v1/memory/memorize",
                json_data=request_data.model_dump()
            )
            
            # Parse response
            response = MemorizeResponse(**response_data)
            logger.info(f"Memorization task started: {response.task_id}")
            
            return response
            
        except ValidationError as e:
            raise MemuValidationException(f"Request validation failed: {str(e)}")
    
    def get_task_status(self, task_id: str) -> MemorizeTaskStatusResponse:
        """
        Get the status of a memorization task
        
        Args:
            task_id: Task identifier returned from memorize_conversation
            
        Returns:
            MemorizeTaskStatusResponse: Task status, progress, and results
            
        Raises:
            MemuValidationException: For validation errors
            MemuAPIException: For API errors
            MemuConnectionException: For connection errors
        """
        try:
            logger.info(f"Getting status for task: {task_id}")
            
            # Make API request to the correct endpoint
            response_data = self._make_request(
                method="GET",
                endpoint=f"api/v1/memory/memorize/status/{task_id}"
            )
            
            # Parse response using the model
            response = MemorizeTaskStatusResponse(**response_data)
            logger.debug(f"Task {task_id} status: {response.status}")
            
            return response
            
        except ValidationError as e:
            raise MemuValidationException(f"Response validation failed: {str(e)}")