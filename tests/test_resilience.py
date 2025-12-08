
import pytest
import httpx
from unittest.mock import MagicMock, patch
from src.core.llm import LLMClient
from tenacity import RetryError

# Mock response object
def mock_response(status_code=200, json_data=None):
    resp = MagicMock()
    resp.status_code = status_code
    resp.json.return_value = json_data or {}
    return resp

def test_openai_retry_success():
    """Test that OpenAI chat retries on connection error and eventually succeeds."""
    client = LLMClient()
    client.provider = "openai"
    client.api_key = "fake-key"
    client.base_url = "https://api.openai.com/v1"
    
    # Mock httpx.post to fail twice then succeed
    with patch("httpx.post") as mock_post:
        mock_post.side_effect = [
            httpx.ConnectError("Connection failed"),
            httpx.ReadTimeout("Timeout"),
            mock_response(200, {"choices": [{"message": {"content": "Success"}}]})
        ]
        
        result = client._openai_chat([{"role": "user", "content": "hi"}])
        
        assert result == "Success"
        assert mock_post.call_count == 3

def test_openai_retry_fail():
    """Test that OpenAI chat gives up after max retries."""
    client = LLMClient()
    client.provider = "openai"
    client.api_key = "fake-key"
    
    # Mock httpx.post to fail always
    with patch("httpx.post") as mock_post:
        mock_post.side_effect = httpx.ConnectError("Fail forever")
        
        with pytest.raises(RetryError):
            client._openai_chat([{"role": "user", "content": "hi"}])
            
        # Should match max retries in code (5)
        assert mock_post.call_count == 5

if __name__ == "__main__":
    # DIY runner if pytest not available/convenient
    try:
        test_openai_retry_success()
        print("✅ test_openai_retry_success passed")
    except Exception as e:
        print(f"❌ test_openai_retry_success failed: {e}")
        
    try:
        test_openai_retry_fail()
        print("✅ test_openai_retry_fail passed")
    except Exception as e:
        print(f"❌ test_openai_retry_fail failed: {e}")
