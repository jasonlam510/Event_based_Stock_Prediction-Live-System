import sys
from pathlib import Path
if __name__ == "__main__":
    project_root = Path.cwd()  # Get the current directory
    sys.path.append(str(project_root))
from src.utils.logger import get_logger
from src.data.base_data import Data
import aiohttp
import asyncio
import pandas as pd
from datetime import datetime, timezone
from typing import Optional
import time
import random
from src.parsers.yf_rss_parsers import YahooFinanceParser
from src.data.models import Channel, NewsItem

class YahooFinanceRSS(Data):
    def __init__(self, url: str = "https://finance.yahoo.com/rss/"):
        super().__init__()
        self.url = url
        self.logger = get_logger(__name__)
        self.channel = None
        self.df = pd.DataFrame()
        self.session = None
        self.parser = YahooFinanceParser()

    async def __aenter__(self):
        """Async context manager entry"""
        self.session = aiohttp.ClientSession(headers=self.parser.headers)
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit"""
        if self.session:
            await self.session.close()

    def _ensure_timezone_aware(self, dt: datetime) -> datetime:
        """Ensure datetime is timezone aware"""
        if dt.tzinfo is None:
            return dt.replace(tzinfo=timezone.utc)
        return dt

    async def _fetch_with_retry(self, max_retries: int = 3, initial_delay: float = 1.0):
        """Fetch data with exponential backoff retry logic"""
        retry_count = 0
        delay = initial_delay

        while retry_count < max_retries:
            try:
                if not self.session:
                    self.session = aiohttp.ClientSession(headers=self.parser.headers)
                
                async with self.session.get(self.url) as response:
                    if response.status == 429:
                        retry_count += 1
                        if retry_count < max_retries:
                            # Add jitter to avoid thundering herd problem
                            jitter = random.uniform(0, 0.1 * delay)
                            await asyncio.sleep(delay + jitter)
                            delay *= 2  # Exponential backoff
                            continue
                        else:
                            self.logger.error("Max retries reached for rate limiting")
                            return None
                    
                    response.raise_for_status()
                    return await response.text()

            except aiohttp.ClientError as e:
                self.logger.error(f"Error fetching RSS feed: {e}")
                if "429" in str(e):
                    retry_count += 1
                    if retry_count < max_retries:
                        await asyncio.sleep(delay)
                        delay *= 2
                        continue
                return None
            except Exception as e:
                self.logger.error(f"Unexpected error: {e}")
                return None

    async def fetch(self, since_time: Optional[str] = None) -> Optional[pd.DataFrame]:
        """Fetch news data from Yahoo Finance RSS feed asynchronously
        
        Args:
            since_time (Optional[str]): ISO 8601 timestamp. Only return items published after this time.
                                      If None, return all items.
        """
        try:
            self.logger.info(f"Fetching Yahoo Finance RSS feed from {self.url}")
            
            # Parse the since_time if provided
            since_datetime = None
            if since_time:
                try:
                    # Parse the timestamp and ensure it's timezone aware
                    since_datetime = datetime.fromisoformat(since_time.replace('Z', '+00:00'))
                    since_datetime = self._ensure_timezone_aware(since_datetime)
                    self.logger.info(f"Filtering items published after {since_datetime}")
                except ValueError as e:
                    self.logger.error(f"Invalid ISO 8601 timestamp format: {e}")
                    return None
            
            # Fetch with retry logic
            content = await self._fetch_with_retry()
            if not content:
                return None
            
            # Use the parser to parse the feed
            self.channel, items = await self.parser.parse_feed(self.url)
            if not self.channel or not items:
                return None
            
            # Log total number of items fetched before filtering
            self.logger.info(f"Successfully fetched {len(items)} news items")
            
            # Filter items by date if since_time is provided
            if since_datetime:
                items = [
                    item for item in items 
                    if self._ensure_timezone_aware(item.pub_date) > since_datetime
                ]
                self.logger.info(f"Filtered to {len(items)} items published after {since_datetime}")
            
            # Convert to DataFrame
            self.df = pd.DataFrame([item.model_dump() for item in items])
            
            return self.df
            
        except Exception as e:
            self.logger.error(f"Unexpected error: {e}")
            return None

    async def process(self, stock_name: str = "S&P500"):
        """Process the fetched Yahoo Finance data by analyzing each news item using Gemini
        
        Args:
            stock_name (str): The stock context for relevance scoring. Defaults to "S&P500".
        """
        if self.df.empty:
            self.logger.warning("No data to process. Please fetch data first.")
            return None

        try:
            # Import required modules
            from src.llm.gemini_news_analyzer import analyze_news
            from src.extractors.yf_news_extractors import YahooFinanceExtractor

            # Create extractor instance
            extractor = YahooFinanceExtractor()
            analysis_results = []
            
            # Process each news item
            for _, row in self.df.iterrows():
                try:
                    # Get the news guid and URL
                    guid = row['guid']
                    url = str(row['link'])  # Convert HttpUrl to string
                    
                    # Extract description using the extractor
                    description = await extractor.extract_content(url)
                    
                    if not description:
                        self.logger.warning(f"Could not extract description for {url}")
                        continue
                    
                    # Analyze the news using Gemini with the extracted description
                    analysis = await analyze_news(
                        content=description,
                        content_name="description",
                        stock_name=stock_name
                    )
                    
                    # Add analysis results to the list
                    analysis_results.append({
                        'guid': guid,
                        'description': description,
                        **analysis.model_dump()  # Include all analysis fields dynamically
                    })
                    
                    self.logger.info(f"Analyzed news with guid: {guid}")
                    
                except Exception as e:
                    self.logger.error(f"Error analyzing news item: {e}")
                    continue
            
            # Convert results to DataFrame and merge with original data
            if analysis_results:
                analysis_df = pd.DataFrame(analysis_results)
                self.df = pd.merge(
                    self.df,
                    analysis_df,
                    left_on='guid',
                    right_on='guid',
                    how='left'
                )
                self.logger.info(f"Successfully analyzed {len(analysis_results)} news items")
                return self.df
            else:
                self.logger.warning("No analysis results were generated")
                return None

        except Exception as e:
            self.logger.error(f"Error in process: {e}")
            return None

if __name__ == "__main__":
    async def main():
        async with YahooFinanceRSS() as yahoo_finance:
            since_time = '2025-05-28 11:27:00-04:00'
            df = await yahoo_finance.fetch(since_time=since_time) 
            
            if df is not None and not df.empty:
                # Print Channel Information
                print("\n=== Channel Information ===")
                if yahoo_finance.channel:
                    channel_info = yahoo_finance.channel.model_dump()
                    print(f"Title: {channel_info['title']}")
                    print(f"Description: {channel_info['description']}")
                    print(f"Language: {channel_info['language']}")
                    print(f"Last Updated: {channel_info['pub_date']}")
                    print(f"Copyright: {channel_info['copyright']}")
                    print(f"Image: {channel_info['image_title']} ({channel_info['image_url']})")
                
                # Print News Summary
                print("\n=== News Summary ===")
                print(f"Total Articles: {len(df)}")

            else:
                print("Failed to fetch data. Please try again later.")
            
            


    # Run the async main function
    asyncio.run(main()) 