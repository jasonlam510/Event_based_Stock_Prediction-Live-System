import os
from google import genai
from google.genai import types
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type, before_sleep_log
from google.api_core import exceptions
import logging

import sys
from pathlib import Path
project_root = Path.cwd() # Get the current directory
sys.path.append(str(project_root))

from src.config import Config
from src.utils.logger import get_logger

logger = get_logger(__name__)

# List of available Gemini models
GEMINI_MODELS = {
    "gemini-2.0-flash": "Fast and efficient model for quick responses",
    "gemini-2.0-flash-lite": "Lightweight version of flash model for basic tasks"
}

# Initialize configuration
config = Config()

def get_client():
    """Get or create a Gemini client instance."""
    api_key = config.get_key('GEMINI_API_KEY')
    return genai.Client(api_key=api_key)

@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=4, max=10),
    retry=retry_if_exception_type(exceptions.ServiceUnavailable),
    reraise=True,
    before_sleep=before_sleep_log(logger, logging.INFO)
)
async def generate(
    contents: str, 
    model: str = "gemini-2.0-flash-lite", 
    generate_content_config: types.GenerateContentConfig = None
):
    """Generate content using the specified Gemini model.
    
    Args:
        contents (str): The input content to generate from
        model (str): The model to use. Must be one of the available models
        generate_content_config (types.GenerateContentConfig): Configuration for generation
        
    Returns:
        The generated response
        
    Raises:
        ValueError: If an invalid model is specified or if content is empty
        exceptions.ServiceUnavailable: If the service is temporarily unavailable (will retry)
    """
    if not contents or contents == "":
        error_msg = "Content cannot be empty"
        logger.error(error_msg)
        raise ValueError(error_msg)
        
    if model not in GEMINI_MODELS:
        error_msg = f"Invalid model: {model}. Available models are: {', '.join(GEMINI_MODELS.keys())}"
        logger.error(error_msg)
        raise ValueError(error_msg)
    
    try:
        client = get_client()
        response = await client.aio.models.generate_content(
            model=model,
            contents=contents,
            config=generate_content_config,
        )
        logger.debug("Content generated successfully")
        return response
    except Exception as e:
        logger.error("Error generating content: %s", str(e))
        raise