from typing import Literal
from pydantic import BaseModel, Field
from src.utils.logger import get_logger

logger = get_logger(__name__)

class NewsAnalysis(BaseModel):
    """Model for news analysis output."""
    sentiment_score: float = Field(
        description="Score between -1 (very negative) and 1 (very positive)",
        ge=-1.0,
        le=1.0
    )
    relevance_score: float = Field(
        description="Score between 0 (irrelevant) and 1 (highly relevant)",
        ge=0.0,
        le=1.0
    )
    event_importance: float = Field(
        description="Score between 0 (no market impact) and 1 (major market-moving event)",
        ge=0.0,
        le=1.0
    )
    event_type: Literal[
        "earnings",
        "merger",
        "dividend",
        "guidance",
        "regulatory",
        "macroeconomic",
        "monetary",
        "CEO change",
        "product launch",
        "supply-chain",
        "credit",
        "scandal",
        "analyst",
        "sector-wide",
        "geopolitical",
        "other"
    ]

def create_news_analysis_prompt(
    content: str,
    content_name: str = "headline",
    stock_name: str = "market"
) -> str:
    """Create a prompt for news analysis.
    
    Args:
        content (str): The news content to analyze
        content_name (str): The type of content (e.g., "headline", "article")
        stock_name (str): The stock context for relevance scoring
        
    Returns:
        str: The formatted prompt
    """
    # Get the event types from the model's Literal type
    event_types = NewsAnalysis.model_fields['event_type'].annotation.__args__
    
    return (
        f"You are a financial‐news analysis assistant. Given only the {content_name} of the news, "
        f"you must output a valid JSON object with exactly these four fields (no extra keys, no prose):\n"
        f"- sentiment_score: float between -1 (very negative) and 1 (very positive)  \n"
        f"- relevance_score: float between 0 (irrelevant) and 1 (highly relevant to the {stock_name})  \n"
        "- event_importance: float between 0 (no market impact) and 1 (major market-moving event)  \n"
        f"- event_type: one of {event_types}\n\n"
        f"**{content_name.capitalize()}:** \"{content}\"\n\n"
        "**Output only JSON.**"
    )

async def analyze_news(
    content: str,
    content_name: str = "headline",
    stock_name: str = "market",
    model: str = "gemini-2.0-flash"
) -> NewsAnalysis:
    """Analyze news content using Gemini API.
    
    Args:
        content (str): The news content to analyze
        content_name (str): The type of content (e.g., "headline", "article")
        stock_name (str): The stock context for relevance scoring
        model (str): The Gemini model to use
        
    Returns:
        NewsAnalysis: The analysis results
        
    Raises:
        ValueError: If the API call fails or returns invalid data
    """
    from .gemini_client import generate
    from google.genai import types
    
    prompt = create_news_analysis_prompt(content, content_name, stock_name)
    
    config = types.GenerateContentConfig(
        response_mime_type="application/json",
        response_schema=NewsAnalysis
    )
    
    try:
        response = await generate(
            contents=prompt,
            model=model,
            generate_content_config=config
        )
        
        if not response or not response.parsed:
            raise ValueError("Empty response from LLM")
            
        return response.parsed
    except Exception as e:
        logger.error(f"Failed to analyze news: {str(e)}")
        raise ValueError(f"News analysis failed: {str(e)}") 