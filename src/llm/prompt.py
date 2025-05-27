from typing import Literal
from pydantic import BaseModel, Field

import sys
from pathlib import Path
project_root = Path.cwd() # Get the current directory
sys.path.append(str(project_root))

from src.logger import get_logger

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
    market_reference: str = "market"
) -> str:
    """Create a prompt for news analysis.
    
    Args:
        content (str): The news content to analyze
        content_name (str): The type of content (e.g., "headline", "article")
        market_reference (str): The market context for relevance scoring
        
    Returns:
        str: The formatted prompt
    """
    # Get the event types from the model's Literal type
    event_types = NewsAnalysis.model_fields['event_type'].annotation.__args__
    
    return (
        f"You are a financial‐news analysis assistant. Given only the {content_name} of the news, "
        f"you must output a valid JSON object with exactly these four fields (no extra keys, no prose):\n"
        f"- sentiment_score: float between -1 (very negative) and 1 (very positive)  \n"
        f"- relevance_score: float between 0 (irrelevant) and 1 (highly relevant to the {market_reference})  \n"
        "- event_importance: float between 0 (no market impact) and 1 (major market-moving event)  \n"
        f"- event_type: one of {event_types}\n\n"
        f"**{content_name.capitalize()}:** \"{content}\"\n\n"
        "**Output only JSON.**"
    )

async def analyze_news(
    content: str,
    content_name: str = "headline",
    market_reference: str = "market",
    model: str = "gemini-2.0-flash"
) -> NewsAnalysis:
    """Analyze news content using Gemini API.
    
    Args:
        content (str): The news content to analyze
        content_name (str): The type of content (e.g., "headline", "article")
        market_reference (str): The market context for relevance scoring
        model (str): The Gemini model to use
        
    Returns:
        NewsAnalysis: The analysis results
    """
    from .gemini_client import generate
    from google.genai import types
    
    prompt = create_news_analysis_prompt(content, content_name, market_reference)
    
    config = types.GenerateContentConfig(
        response_mime_type="application/json",
        response_schema=NewsAnalysis
    )
    
    response = await generate(
        contents=prompt,
        model=model,
        generate_content_config=config
    )
    
    return response.parsed