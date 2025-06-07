import asyncio
import signal
import sys
from pathlib import Path
project_root = Path.cwd() # Get the current directory
sys.path.append(str(project_root))
from src.config import Config
from src.pipeline.orchestrator import PipelineOrchestrator
from src.utils.logger import get_logger
from src.database import init_db, close_db

logger = get_logger(__name__)

async def main():
    # Initialize configuration
    config = Config()
    logger.info(f"Environment: {config.get_key('ENVIRONMENT')}")

    # Initialize database
    try:
        await init_db()
        logger.info("Database initialized successfully")
    except Exception as e:
        logger.error(f"Failed to initialize database: {e}")
        return

    # Get database connection string
    db_dsn = config.get_key('DATABASE_URL')

    # Define which workers to enable/disable
    enabled_workers = {
        "rss_fetcher": True,        # Enable RSS fetcher
        "llm_analyzer": True,       # Enable LLM analyzer
        "content_backfill": True,   # Enable content backfill
        "price_fetcher": True,      # Enable price fetcher
        "ti_calculator": True,      # Enable technical indicator calculator
        "ti_backfill": True         # Enable technical indicator backfill
    }

    # Create and start the orchestrator with enabled workers
    orchestrator = PipelineOrchestrator(
        db_dsn=db_dsn,
        fetch_interval=3600,  # 1 hour fetch interval for price data
        enabled_workers=enabled_workers
    )
    
    # Set up signal handlers for graceful shutdown
    loop = asyncio.get_running_loop()
    for sig in (signal.SIGTERM, signal.SIGINT):
        loop.add_signal_handler(sig, lambda: asyncio.create_task(shutdown(orchestrator)))

    try:
        await orchestrator.start()
        # Keep the main task running
        while True:
            await asyncio.sleep(1)
    except Exception as e:
        logger.error(f"Error in main loop: {e}")
    finally:
        await shutdown(orchestrator)

async def shutdown(orchestrator: PipelineOrchestrator):
    """Gracefully shutdown the application"""
    logger.info("Shutting down...")
    
    try:
        # First stop the orchestrator
        await orchestrator.stop()
        
        # Then close database
        await close_db()
        
        # Get all tasks except the current one
        pending = asyncio.all_tasks() - {asyncio.current_task()}
        
        # Cancel all pending tasks
        for task in pending:
            task.cancel()
        
        # Wait for all tasks to complete with a timeout
        if pending:
            try:
                await asyncio.wait(pending, timeout=5.0)
            except asyncio.TimeoutError:
                logger.warning("Some tasks did not complete within timeout")
            except Exception as e:
                logger.error(f"Error waiting for tasks: {e}")
        
    except Exception as e:
        logger.error(f"Error during shutdown: {e}")
    finally:
        logger.info("Shutdown complete")

if __name__ == "__main__":
    asyncio.run(main())
