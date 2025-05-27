from abc import ABC, abstractmethod
from typing import Optional

class ContentExtractor(ABC):
    """Abstract base class for content extractors."""
    
    @abstractmethod
    async def extract_content(self, url: str) -> Optional[str]:
        """Extract content from a URL.
        
        Args:
            url (str): The URL to extract content from
            
        Returns:
            Optional[str]: The extracted content, or None if extraction failed
        """
        pass 