from abc import ABC, abstractmethod
from typing import List, Tuple
from src.pipeline.models import Channel, NewsItem

class RSSParser(ABC):
    """Abstract base class for RSS feed parsers."""
    
    @abstractmethod
    async def parse_feed(self, url: str) -> Tuple[Channel, List[NewsItem]]:
        """Parse RSS feed and return channel info and news items.
        
        Args:
            url (str): The URL of the RSS feed to parse
            
        Returns:
            Tuple[Channel, List[NewsItem]]: A tuple containing the channel information
            and a list of news items
        """
        pass 