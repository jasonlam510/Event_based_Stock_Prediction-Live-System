import os

from pathlib import Path
from dotenv import load_dotenv
from src.utils.logger import get_logger

logger = get_logger(__name__)

class Config:
    """Configuration manager for different environments."""
    
    _instance = None
    
    def __new__(cls, env: str = None):
        """Singleton pattern implementation"""
        if cls._instance is None:
            cls._instance = super(Config, cls).__new__(cls)
            cls._instance._initialized = False
        return cls._instance
    
    def __init__(self, env: str = None):
        """Initialize configuration.
        
        Args:
            env (str, optional): Environment to load ('test' or 'prod'). 
                               If None, uses ENVIRONMENT variable or defaults to 'prod'
        """
        # Skip initialization if already done
        if self._initialized:
            return
            
        self.env = env or os.getenv('ENVIRONMENT', 'test')
        logger.info("Initializing Config with environment: %s", self.env)
        self._load_env()
        self._initialized = True
        
    def _load_env(self):
        """Load environment variables based on the current environment."""
        # Get the project root directory
        project_root = Path.cwd()
        
        # Load the appropriate .env file
        if self.env == 'test':
            env_file = project_root / '.env.test'
        else:
            env_file = project_root / '.env'
            
        # Load the environment variables
        if env_file.exists():
            # Set override=False to preserve existing environment variables
            load_dotenv(env_file, override=True)
            logger.info("Environment file loaded successfully (existing variables preserved)")
        else:
            error_msg = f"Environment file not found: {env_file}"
            logger.error(error_msg)
            logger.error("Current working directory: %s", os.getcwd())
            raise FileNotFoundError(error_msg)
    
    def get_key(self, key_name: str) -> str:
        """Get the API key for the current environment.
        
        Args:
            key_name (str): Name of the environment variable containing the API key.
                           Defaults to 'GEMINI_API_KEY'.
        
        Returns:
            str: The API key value
            
        Raises:
            ValueError: If the specified key is not found in the environment
        """
        key = os.getenv(key_name)
        if not key:
            error_msg = f"{key_name} not found in {self.env} environment"
            logger.error(error_msg)
            raise ValueError(error_msg)
        
        # Log first 4 characters of key for debugging (safe to show partial key)
        logger.debug("Retrieved %s: %s...", key_name, key[:4] if key else "None")
        return key
    
    @property
    def is_test(self) -> bool:
        """Check if we're in the test environment."""
        return self.env == 'test'
    
    @property
    def is_prod(self) -> bool:
        """Check if we're in the production environment."""
        return self.env == 'prod'
