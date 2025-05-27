import os
import pytest
import asyncio
from src.llm.gemini_client import generate
from src.config import Config
from src.logger import get_logger
logger = get_logger(__name__)

@pytest.fixture(autouse=True)
def setup_test_env(mock_env_vars):
    """Ensure test environment is set up for all tests."""
    # Debug: Print environment variables
    logger.info("Environment: %s", os.getenv('ENVIRONMENT'))
    logger.info("API Key exists: %s", bool(os.getenv('GEMINI_API_KEY')))

@pytest.mark.asyncio
async def test_gemini_hello():
    """Test that we can make a basic API call to Gemini with a hello message."""
    
    # Simple hello message
    test_message = "Hello, this is a test message"
    
    # Make the API call
    response = await generate(
        contents=test_message,
        model="gemini-2.0-flash-lite"
    )
    
    # Basic assertions
    assert response is not None
    assert hasattr(response, 'text')
    assert isinstance(response.text, str)
    assert len(response.text) > 0 