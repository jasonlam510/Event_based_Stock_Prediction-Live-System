import pytest
import os
from pathlib import Path

@pytest.fixture
def mock_env_vars(monkeypatch):
    """Fixture to set up mock environment variables for testing"""
    # Get the actual API key from .env.test file
    env_file = Path(__file__).parent.parent / '.env.test'
    if env_file.exists():
        with open(env_file) as f:
            for line in f:
                if line.strip() and not line.startswith('#'):
                    key, value = line.strip().split('=', 1)
                    monkeypatch.setenv(key, value)
    else:
        # Fallback to test values if .env.test doesn't exist
        monkeypatch.setenv("GEMINI_API_KEY", "test_api_key")
    
    monkeypatch.setenv("ENVIRONMENT", "test") 