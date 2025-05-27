import pytest
import os
from pathlib import Path
from src.llm.prompt import analyze_news, NewsAnalysis
from src.utils.logger import get_logger

logger = get_logger(__name__)

@pytest.fixture(autouse=True)
def setup_test_env(mock_env_vars):
    """Ensure test environment is set up for all tests."""
    # Debug: Print environment variables
    logger.info("Environment: %s", os.getenv('ENVIRONMENT'))
    logger.info("API Key exists: %s", bool(os.getenv('GEMINI_API_KEY')))

@pytest.fixture
def sample_news_cases():
    """Sample news cases for testing."""
    return [
        {
            "content": "Apple Inc. reports record-breaking Q4 earnings, exceeding market expectations",
            "expected_type": "earnings",
            "description": "Positive earnings news"
        },
        {
            "content": "Tesla announces major recall of 2 million vehicles due to safety concerns",
            "expected_type": "regulatory",
            "description": "Negative regulatory news"
        },
        {
            "content": "Microsoft acquires AI startup for $10 billion to boost cloud capabilities",
            "expected_type": "merger",
            "description": "Merger news"
        },
        {
            "content": "Federal Reserve raises interest rates by 0.25% to combat inflation",
            "expected_type": "monetary",
            "description": "Monetary policy news"
        }
    ]

@pytest.mark.asyncio
async def test_gemini_api_connection(sample_news_cases):
    """Test that we can successfully connect to and get responses from the Gemini API."""
    for case in sample_news_cases:
        logger.info("Testing case: %s", case["description"])
        
        # Call the real API
        result = await analyze_news(
            content=case["content"],
            content_name="headline",
            market_reference="tech sector"
        )
        
        # Verify the result is a NewsAnalysis object
        assert isinstance(result, NewsAnalysis)
        
        # Log the results
        logger.info(
            "Analysis results for '%s':\n"
            "  Sentiment: %.2f\n"
            "  Relevance: %.2f\n"
            "  Importance: %.2f\n"
            "  Event Type: %s",
            case["content"][:50] + "...",
            result.sentiment_score,
            result.relevance_score,
            result.event_importance,
            result.event_type
        )
        
        # Verify expected event type matches
        assert result.event_type == case["expected_type"], \
            f"Expected event type {case['expected_type']}, got {result.event_type}"

def test_news_analysis_model_validation():
    """Test Pydantic model validation."""
    # Test valid data
    valid_data = {
        "sentiment_score": 0.5,
        "relevance_score": 0.8,
        "event_importance": 0.7,
        "event_type": "earnings"
    }
    analysis = NewsAnalysis(**valid_data)
    assert analysis.sentiment_score == 0.5
    
    # Test invalid data types
    with pytest.raises(ValueError):
        NewsAnalysis(
            sentiment_score="not a float",  # Should be float
            relevance_score=0.8,
            event_importance=0.7,
            event_type="earnings"
        )
    
    # Test out of range values
    with pytest.raises(ValueError):
        NewsAnalysis(
            sentiment_score=2.0,  # Outside valid range
            relevance_score=0.8,
            event_importance=0.7,
            event_type="earnings"
        )
    
    # Test invalid event type
    with pytest.raises(ValueError):
        NewsAnalysis(
            sentiment_score=0.5,
            relevance_score=0.8,
            event_importance=0.7,
            event_type="invalid_type"  # Not in allowed values
        )

if __name__ == "__main__":
    # This allows running the tests directly
    pytest.main([__file__, "-v"]) 