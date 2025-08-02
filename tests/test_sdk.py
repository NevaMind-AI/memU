"""
Test cases for MemU SDK

Tests the HTTP client functionality and API interactions.
"""

import pytest
import httpx
from unittest.mock import Mock, patch, MagicMock

from memu.sdk import MemuClient, MemorizeRequest, MemorizeResponse
from memu.sdk.exceptions import (
    MemuAPIException,
    MemuValidationException,
    MemuAuthenticationException,
    MemuConnectionException
)


class TestMemuClient:
    """Test cases for MemuClient"""
    
    def test_client_initialization(self):
        """Test client initialization with various parameters"""
        
        # Test with all parameters
        client = MemuClient(
            base_url="https://api.memu.ai",
            api_key="test-key",
            timeout=60.0,
            max_retries=5
        )
        
        assert client.base_url == "https://api.memu.ai/"
        assert client.api_key == "test-key"
        assert client.timeout == 60.0
        assert client.max_retries == 5
        
        client.close()
    
    def test_client_initialization_missing_values(self):
        """Test client initialization with missing required values"""
        
        # Test missing base_url (should use default)
        with patch.dict('os.environ', {'MEMU_API_KEY': 'test-key'}):
            client = MemuClient()
            assert client.base_url == "http://localhost:8000/"
            client.close()
        
        # Test missing api_key
        with pytest.raises(ValueError, match="api_key is required"):
            MemuClient(base_url="https://api.memu.ai")
    
    def test_base_url_normalization(self):
        """Test that base_url is properly normalized"""
        
        # URL without trailing slash
        client = MemuClient(
            base_url="https://api.memu.ai",
            api_key="test-key"
        )
        assert client.base_url == "https://api.memu.ai/"
        client.close()
        
        # URL with trailing slash
        client = MemuClient(
            base_url="https://api.memu.ai/",
            api_key="test-key"
        )
        assert client.base_url == "https://api.memu.ai/"
        client.close()
    
    def test_context_manager(self):
        """Test context manager functionality"""
        
        with MemuClient(base_url="https://api.memu.ai", api_key="test-key") as client:
            assert client.base_url == "https://api.memu.ai/"
            assert client.api_key == "test-key"
        
        # Client should be closed after context exit
        # Note: We can't easily test if httpx client is closed without accessing private members
    
    @patch('memu.sdk.client.httpx.Client')
    def test_memorize_conversation_success(self, mock_httpx):
        """Test successful memorize_conversation call"""
        
        # Mock response
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "task_id": "test-task-123",
            "status": "pending",
            "message": "Task created successfully"
        }
        
        mock_client = Mock()
        mock_client.request.return_value = mock_response
        mock_httpx.return_value = mock_client
        
        client = MemuClient(base_url="https://api.memu.ai", api_key="test-key")
        
        response = client.memorize_conversation(
            conversation_text="Hello world",
            user_id="user123",
            user_name="Alice",
            agent_id="agent456",
            agent_name="Bot",
            project_id="proj789"
        )
        
        assert isinstance(response, MemorizeResponse)
        assert response.task_id == "test-task-123"
        assert response.status == "pending"
        assert response.message == "Task created successfully"
        
        # Verify the request was made correctly
        mock_client.request.assert_called_once()
        call_args = mock_client.request.call_args
        
        assert call_args[1]['method'] == 'POST'
        assert 'api/v1/memory/memorize' in call_args[1]['url']
        assert call_args[1]['params']['api_key_id'] == 'test-key'
        
        json_data = call_args[1]['json']
        assert json_data['conversation_text'] == "Hello world"
        assert json_data['user_id'] == "user123"
        assert json_data['user_name'] == "Alice"
        
        client.close()
    
    @patch('memu.sdk.client.httpx.Client')
    def test_memorize_conversation_validation_error(self, mock_httpx):
        """Test memorize_conversation with validation error"""
        
        # Mock 422 response
        mock_response = Mock()
        mock_response.status_code = 422
        mock_response.json.return_value = {
            "detail": [
                {
                    "loc": ["conversation_text"],
                    "msg": "field required",
                    "type": "value_error.missing"
                }
            ]
        }
        
        mock_client = Mock()
        mock_client.request.return_value = mock_response
        mock_httpx.return_value = mock_client
        
        client = MemuClient(base_url="https://api.memu.ai", api_key="test-key")
        
        with pytest.raises(MemuValidationException) as exc_info:
            client.memorize_conversation(
                conversation_text="",  # Empty text should cause validation error
                user_id="user123",
                user_name="Alice",
                agent_id="agent456", 
                agent_name="Bot",
                project_id="proj789"
            )
        
        assert exc_info.value.status_code == 422
        assert "detail" in exc_info.value.response_data
        
        client.close()
    
    @patch('memu.sdk.client.httpx.Client')
    def test_memorize_conversation_auth_error(self, mock_httpx):
        """Test memorize_conversation with authentication error"""
        
        # Mock 401 response
        mock_response = Mock()
        mock_response.status_code = 401
        mock_response.json.return_value = {"detail": "Invalid API key"}
        
        mock_client = Mock()
        mock_client.request.return_value = mock_response
        mock_httpx.return_value = mock_client
        
        client = MemuClient(base_url="https://api.memu.ai", api_key="invalid-key")
        
        with pytest.raises(MemuAuthenticationException) as exc_info:
            client.memorize_conversation(
                conversation_text="Hello",
                user_id="user123",
                user_name="Alice",
                agent_id="agent456",
                agent_name="Bot", 
                project_id="proj789"
            )
        
        assert exc_info.value.status_code == 401
        assert "Authentication failed" in str(exc_info.value)
        
        client.close()
    
    @patch('memu.sdk.client.httpx.Client')
    def test_memorize_conversation_connection_error(self, mock_httpx):
        """Test memorize_conversation with connection error"""
        
        # Mock connection error
        mock_client = Mock()
        mock_client.request.side_effect = httpx.RequestError("Connection failed")
        mock_httpx.return_value = mock_client
        
        client = MemuClient(base_url="https://api.memu.ai", api_key="test-key")
        
        with pytest.raises(MemuConnectionException) as exc_info:
            client.memorize_conversation(
                conversation_text="Hello",
                user_id="user123", 
                user_name="Alice",
                agent_id="agent456",
                agent_name="Bot",
                project_id="proj789"
            )
        
        assert "Connection error after" in str(exc_info.value)
        
        client.close()
    
    @patch('memu.sdk.client.httpx.Client')
    def test_get_task_status_success(self, mock_httpx):
        """Test successful get_task_status call"""
        
        # Mock response
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "task_id": "test-task-123",
            "status": "completed",
            "progress": 100,
            "result": {"success": True}
        }
        
        mock_client = Mock()
        mock_client.request.return_value = mock_response
        mock_httpx.return_value = mock_client
        
        client = MemuClient(base_url="https://api.memu.ai", api_key="test-key")
        
        status = client.get_task_status("test-task-123")
        
        assert status["task_id"] == "test-task-123"
        assert status["status"] == "completed"
        assert status["progress"] == 100
        
        # Verify the request was made correctly
        mock_client.request.assert_called_once()
        call_args = mock_client.request.call_args
        
        assert call_args[1]['method'] == 'GET'
        assert 'api/v1/tasks/test-task-123/status' in call_args[1]['url']
        
        client.close()
    
    @patch('memu.sdk.client.httpx.Client')
    def test_retry_logic(self, mock_httpx):
        """Test retry logic for failed requests"""
        
        # Mock client that fails twice then succeeds
        mock_response_success = Mock()
        mock_response_success.status_code = 200
        mock_response_success.json.return_value = {
            "task_id": "test-task-123",
            "status": "pending",
            "message": "Success after retries"
        }
        
        mock_client = Mock()
        mock_client.request.side_effect = [
            httpx.RequestError("Connection failed"),  # First attempt fails
            httpx.RequestError("Connection failed"),  # Second attempt fails
            mock_response_success                     # Third attempt succeeds
        ]
        mock_httpx.return_value = mock_client
        
        client = MemuClient(
            base_url="https://api.memu.ai",
            api_key="test-key",
            max_retries=3
        )
        
        response = client.memorize_conversation(
            conversation_text="Hello",
            user_id="user123",
            user_name="Alice",
            agent_id="agent456",
            agent_name="Bot",
            project_id="proj789"
        )
        
        assert response.task_id == "test-task-123"
        assert response.message == "Success after retries"
        
        # Should have made 3 attempts (2 failures + 1 success)
        assert mock_client.request.call_count == 3
        
        client.close()


class TestDataModels:
    """Test cases for data models"""
    
    def test_memorize_request_model(self):
        """Test MemorizeRequest model validation"""
        
        # Valid request
        request = MemorizeRequest(
            conversation_text="Hello world",
            user_id="user123",
            user_name="Alice",
            agent_id="agent456", 
            agent_name="Bot",
            api_key_id="key789",
            project_id="proj101"
        )
        
        assert request.conversation_text == "Hello world"
        assert request.user_id == "user123"
        assert request.user_name == "Alice"
        assert request.agent_id == "agent456"
        assert request.agent_name == "Bot"
        assert request.api_key_id == "key789"
        assert request.project_id == "proj101"
        
        # Test model_dump
        data = request.model_dump()
        assert isinstance(data, dict)
        assert data["conversation_text"] == "Hello world"
    
    def test_memorize_response_model(self):
        """Test MemorizeResponse model validation"""
        
        # Valid response
        response = MemorizeResponse(
            task_id="task-123",
            status="pending",
            message="Task created"
        )
        
        assert response.task_id == "task-123"
        assert response.status == "pending"
        assert response.message == "Task created"
    
    def test_model_validation_errors(self):
        """Test model validation with invalid data"""
        
        # Missing required fields
        with pytest.raises(Exception):  # Pydantic ValidationError
            MemorizeRequest(
                conversation_text="Hello",
                # Missing other required fields
            )
        
        # Empty strings (if validation rules are added later)
        request = MemorizeRequest(
            conversation_text="",  # Empty but allowed for now
            user_id="user123",
            user_name="Alice",
            agent_id="agent456",
            agent_name="Bot", 
            api_key_id="key789",
            project_id="proj101"
        )
        assert request.conversation_text == ""


if __name__ == "__main__":
    pytest.main([__file__])