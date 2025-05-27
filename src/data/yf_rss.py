import sys
from pathlib import Path
project_root = Path.cwd()  # Get the current directory
sys.path.append(str(project_root))
from src.utils.logger import get_logger
from base_data import Data
import aiohttp
import asyncio
import xml.etree.ElementTree as ET
import pandas as pd
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from pydantic import BaseModel, HttpUrl, Field
from typing import Optional, List
import time
import random

class NewsItem(BaseModel):
    title: str
    link: HttpUrl
    pub_date: datetime
    guid: str
    source_name: Optional[str] = None
    source_url: Optional[HttpUrl] = None
    media_url: Optional[HttpUrl] = None
    media_height: Optional[int] = None
    media_width: Optional[int] = None

class Channel(BaseModel):
    title: str
    link: HttpUrl
    description: str
    language: str
    copyright: str
    pub_date: datetime
    ttl: int
    image_title: str
    image_link: HttpUrl
    image_url: HttpUrl

class YahooFinanceRSS(Data):
    def __init__(self, url: str = "https://finance.yahoo.com/rss/"):
        super().__init__()
        self.url = url
        self.logger = get_logger(__name__)
        self.channel = None
        self.df = pd.DataFrame()
        self.session = None
        # Set a proper user agent that's allowed by Yahoo Finance
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Accept': 'application/rss+xml, application/xml, text/xml, */*',
            'Accept-Language': 'en-US,en;q=0.9',
            'Cache-Control': 'no-cache',
            'Pragma': 'no-cache'
        }

    async def __aenter__(self):
        """Async context manager entry"""
        self.session = aiohttp.ClientSession(headers=self.headers)
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit"""
        if self.session:
            await self.session.close()

    def _validate_yahoo_finance_feed(self, root: ET.Element) -> bool:
        """Validate if the RSS feed is from Yahoo Finance"""
        try:
            channel = root.find('channel')
            if channel is None:
                return False
            
            title = channel.find('title')
            if title is None or 'Yahoo Finance' not in title.text:
                return False
            
            return True
        except Exception as e:
            self.logger.error(f"Error validating Yahoo Finance feed: {e}")
            return False

    def _parse_date(self, date_str: str) -> datetime:
        """Parse date string in either RFC 822 or ISO 8601 format"""
        try:
            # Try ISO 8601 format first
            return datetime.fromisoformat(date_str.replace('Z', '+00:00'))
        except ValueError:
            try:
                # Try RFC 822 format
                return parsedate_to_datetime(date_str)
            except Exception as e:
                self.logger.error(f"Failed to parse date '{date_str}': {e}")
                raise

    def _parse_item(self, item: ET.Element) -> Optional[NewsItem]:
        """Parse a single RSS item into a NewsItem model"""
        try:
            # Parse source
            source_elem = item.find('source')
            source_name = source_elem.text if source_elem is not None else None
            source_url = source_elem.get('url') if source_elem is not None else None

            # Parse media content
            media_content_elem = item.find('.//{http://search.yahoo.com/mrss/}content')
            media_url = media_content_elem.get('url') if media_content_elem is not None else None
            media_height = media_content_elem.get('height') if media_content_elem is not None else None
            media_width = media_content_elem.get('width') if media_content_elem is not None else None

            # Parse pubDate
            pub_date = self._parse_date(item.find('pubDate').text)

            # Create NewsItem
            return NewsItem(
                title=item.find('title').text,
                link=item.find('link').text,
                pub_date=pub_date,
                guid=item.find('guid').text,
                source_name=source_name,
                source_url=source_url,
                media_url=media_url,
                media_height=media_height,
                media_width=media_width
            )
        except Exception as e:
            self.logger.error(f"Error parsing RSS item: {e}")
            return None

    def _parse_channel(self, channel: ET.Element) -> Channel:
        """Parse channel information into a Channel model"""
        image_elem = channel.find('image')
        
        # Parse pubDate
        pub_date = self._parse_date(channel.find('pubDate').text)

        return Channel(
            title=channel.find('title').text,
            link=channel.find('link').text,
            description=channel.find('description').text,
            language=channel.find('language').text,
            copyright=channel.find('copyright').text,
            pub_date=pub_date,
            ttl=int(channel.find('ttl').text),
            image_title=image_elem.find('title').text,
            image_link=image_elem.find('link').text,
            image_url=image_elem.find('url').text
        )

    async def _fetch_with_retry(self, max_retries: int = 3, initial_delay: float = 1.0):
        """Fetch data with exponential backoff retry logic"""
        retry_count = 0
        delay = initial_delay

        while retry_count < max_retries:
            try:
                if not self.session:
                    self.session = aiohttp.ClientSession(headers=self.headers)
                
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

    def _ensure_timezone_aware(self, dt: datetime) -> datetime:
        """Ensure datetime is timezone aware"""
        if dt.tzinfo is None:
            return dt.replace(tzinfo=timezone.utc)
        return dt

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
            
            # Parse the XML content
            root = ET.fromstring(content)
            
            # Validate if it's a Yahoo Finance feed
            if not self._validate_yahoo_finance_feed(root):
                self.logger.error("Invalid Yahoo Finance RSS feed")
                return None
            
            # Parse channel information
            channel = root.find('channel')
            self.channel = self._parse_channel(channel)
            
            # Parse all items
            items = []
            for item in root.findall('.//item'):
                news_item = self._parse_item(item)
                if news_item:
                    # Ensure both datetimes are timezone aware before comparison
                    item_date = self._ensure_timezone_aware(news_item.pub_date)
                    if since_datetime and item_date <= since_datetime:
                        continue
                    items.append(news_item)
            
            # Convert to DataFrame
            self.df = pd.DataFrame([item.model_dump() for item in items])
            
            self.logger.info(f"Successfully fetched {len(self.df)} news items")
            if since_datetime:
                self.logger.info(f"Filtered to {len(self.df)} items published after {since_datetime}")
            return self.df
            
        except ET.ParseError as e:
            self.logger.error(f"Error parsing XML: {e}")
            return None
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