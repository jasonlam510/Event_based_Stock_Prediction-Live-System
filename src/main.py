import asyncio
from .config import Config
from .llm.gemini_client import generate, GEMINI_MODELS

async def main():
    try:
        # Initialize configuration
        config = Config()
        
        # Print environment info
        print(f"Running in {config.env} environment")
        
        # Print available models
        print("\nAvailable models:")
        for model, description in GEMINI_MODELS.items():
            print(f"- {model}: {description}")
        
        # Example usage
        print("\nGenerating response...")
        response = await generate(
            contents="Hello, how are you?",
            model="gemini-2.0-flash-lite"
        )
        print("\nResponse:", response)
        
    except ValueError as e:
        print(f"Configuration Error: {e}")
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    asyncio.run(main())
