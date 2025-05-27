import sys
from pathlib import Path
project_root = Path.cwd()  # Get the current directory
sys.path.append(str(project_root))
from src.utils.logger import get_logger
from base_data import Data
import aiohttp
import asyncio
import pandas as pd
from datetime import datetime, timezone
from typing import Optional
import time
import random
from src.parsers.yahoo_finance import YahooFinanceParser
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

    async def fetch(self, since_time: Optional[str] = None):
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
            
            # Filter items by date if since_time is provided
            if since_datetime:
                items = [
                    item for item in items 
                    if self._ensure_timezone_aware(item.pub_date) > since_datetime
                ]
            
            # Convert to DataFrame
            self.df = pd.DataFrame([item.model_dump() for item in items])
            
            self.logger.info(f"Successfully fetched {len(self.df)} news items")
            if since_datetime:
                self.logger.info(f"Filtered to {len(self.df)} items published after {since_datetime}")
            return self.df
            
        except Exception as e:
            self.logger.error(f"Unexpected error: {e}")
            return None

    def process(self):
        """Process the fetched Yahoo Finance data"""
        # Implement Yahoo Finance processing logic here
        pass

if __name__ == "__main__":
    async def main():
        async with YahooFinanceRSS() as yahoo_finance:
            df = await yahoo_finance.fetch() 
            
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