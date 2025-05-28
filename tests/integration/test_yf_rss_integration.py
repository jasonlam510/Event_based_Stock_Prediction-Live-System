import pytest
import asyncio
import os
from datetime import datetime, timedelta
from src.data.yf_rss import YahooFinanceRSS
from src.utils.logger import get_logger

logger = get_logger(__name__)

@pytest.fixture(autouse=True)
def setup_test_env(mock_env_vars):
    """Ensure test environment is set up for all tests."""
    # Debug: Print environment variables
    logger.info("Environment: %s", os.getenv('ENVIRONMENT'))
    logger.info("API Key exists: %s", bool(os.getenv('GEMINI_API_KEY')))

@pytest.mark.asyncio
async def test_fetch_and_process():
    """Test the integration of fetch and process functions"""
    try:
        # Calculate a timestamp from 1 day ago for testing
        since_time = '2025-05-28 12:30:00-04:00'
        
        # Use async context manager to ensure proper resource cleanup
        async with YahooFinanceRSS() as rss:
            # Test fetch
            logger.info("Testing fetch function...")
            df = await rss.fetch(since_time=since_time)
            
            # Verify fetch results
            assert df is not None, "Fetch returned None"
            assert not df.empty, "Fetched DataFrame is empty"
            assert 'guid' in df.columns, "DataFrame missing 'guid' column"
            assert 'title' in df.columns, "DataFrame missing 'title' column"
            assert 'link' in df.columns, "DataFrame missing 'link' column"
            
            logger.info(f"Successfully fetched {len(df)} news items")
            
            # Test process with a specific stock
            logger.info("Testing process function...")
            processed_df = await rss.process(stock_name="S&P500")
            
            # Verify process results
            assert processed_df is not None, "Process returned None"
            assert not processed_df.empty, "Processed DataFrame is empty"
            
            # Check for analysis columns
            analysis_columns = [
                'sentiment_score',
                'relevance_score',
                'event_importance',
                'event_type',
                'description'
            ]
            
            for col in analysis_columns:
                assert col in processed_df.columns, f"Processed DataFrame missing '{col}' column"
            
            # Verify data integrity
            assert len(processed_df) == len(df), "Process changed the number of rows"
            
            # Check that analysis values are within expected ranges
            assert processed_df['sentiment_score'].between(-1, 1).all(), "Invalid sentiment scores found"
            assert processed_df['relevance_score'].between(0, 1).all(), "Invalid relevance scores found"
            assert processed_df['event_importance'].between(0, 1).all(), "Invalid event importance scores found"
            
            # Check that event types are valid
            valid_event_types = {
                "earnings", "merger", "dividend", "guidance", "regulatory",
                "macroeconomic", "monetary", "CEO change", "product launch",
                "supply-chain", "credit", "scandal", "analyst", "sector-wide",
                "geopolitical", "other"
            }
            assert processed_df['event_type'].isin(valid_event_types).all(), "Invalid event types found"
            
            logger.info("Successfully processed news items")
            
            # Print some sample results
            logger.info("\nSample Analysis Results:")
            sample = processed_df.head(3)
            for _, row in sample.iterrows():
                logger.info(f"\nTitle: {row['title']}")
                logger.info(f"Sentiment: {row['sentiment_score']:.2f}")
                logger.info(f"Relevance: {row['relevance_score']:.2f}")
                logger.info(f"Importance: {row['event_importance']:.2f}")
                logger.info(f"Event Type: {row['event_type']}")
                logger.info(f"Description: {row['description'][:100]}...")  # Show first 100 chars of description
            
    except Exception as e:
        logger.error(f"Test failed with error: {e}")
        raise 