import pytest
import asyncio
import os
from src.extractors.yf_news_extractors import YahooFinanceExtractor
from src.utils.logger import get_logger

logger = get_logger(__name__)

@pytest.mark.asyncio
async def test_yahoo_finance_extractor_network(mock_env_vars):
    """Test if YahooFinanceExtractor can connect to network and get response.
    
    Args:
        mock_env_vars: Fixture that sets up mock environment variables for testing
    """
    # Test URL
    test_url = "https://finance.yahoo.com/news/money-meaningless-point-says-31-180147865.html"
    
    logger.info(f"Starting test with URL: {test_url}")
    logger.info(f"Environment: {os.getenv('ENVIRONMENT')}")
    
    # Initialize extractor
    extractor = YahooFinanceExtractor()
    
    try:
        # Attempt to extract content
        logger.info("Attempting to extract content...")
        description = await extractor.extract_content(test_url)
        
        # Assert that we got a response
        assert description is not None, "Failed to get description from Yahoo Finance"
        logger.info("Successfully received description from Yahoo Finance")
        
        # Log the description for verification
        logger.info("Extracted Description:")
        logger.info(description)
        
        # Basic validation of the description
        assert isinstance(description, str), "Description should be a string"
        assert len(description) > 0, "Description should not be empty"
        assert "hedge fund" in description.lower(), "Description should contain relevant keywords"
        logger.info("Description validation passed")
        
    except Exception as e:
        logger.error(f"Test failed with error: {str(e)}")
        pytest.fail(f"Test failed with error: {str(e)}")

if __name__ == "__main__":
    # Run the test
    asyncio.run(test_yahoo_finance_extractor_network()) 